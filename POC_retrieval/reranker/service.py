"""FastAPI service for retrieval + cross-encoder reranking."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document

from .cache import InMemoryCache, build_cache_key
from .cross_encoder import Reranker
from .models import (
    BatchRerankRequest,
    BatchRerankResponse,
    DocumentResponse,
    RerankRequest,
    RerankResponse,
    RerankWithContextRequest,
    RerankWithContextResponse,
    FullDocumentResponse,
    SessionSummaryUpdate,
    SessionTurnRequest,
    SessionTurnResponse,
    StatsResponse,
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionMetadata,
    SessionListResponse,
    SessionCountResponse,
    ErrorResponse,
)

# Setup path before importing from session module
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
import sys
sys.path.insert(0, ROOT_DIR)
from utils.env_loader import load_env_recursive
load_env_recursive(ROOT_DIR)

# Now import session after path is set
from POC_retrieval.session.store_dynamodb import SessionStore

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "auto")
DEFAULT_K_RETRIEVE = int(os.getenv("RERANKER_K_RETRIEVE", "50"))
DEFAULT_K_RETURN = int(os.getenv("RERANKER_K_RETURN", "10"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "10000"))
SESSION_RECENT_LIMIT = int(os.getenv("SESSION_RECENT_LIMIT", "10"))

DDB_REGION = os.getenv("AWS_REGION", "us-east-1")
DDB_TURNS_TABLE = os.getenv("DDB_TURNS_TABLE", "hcai_session_turns").strip()
DDB_SUMMARY_TABLE = os.getenv("DDB_SUMMARY_TABLE", "hcai_session_summary").strip()
DDB_ENDPOINT = os.getenv("DDB_ENDPOINT", "http://localhost:8001")  # Default to local DynamoDB
DDB_TTL_DAYS = os.getenv("DDB_TTL_DAYS")
DDB_AUTO_CREATE = os.getenv("DDB_AUTO_CREATE", "true").lower() in {"1", "true", "yes"}  # Default true for local dev

# Validate table names
if not DDB_TURNS_TABLE or len(DDB_TURNS_TABLE) < 3:
    raise ValueError(f"Invalid DDB_TURNS_TABLE: '{DDB_TURNS_TABLE}'. Must be at least 3 characters.")
if not DDB_SUMMARY_TABLE or len(DDB_SUMMARY_TABLE) < 3:
    raise ValueError(f"Invalid DDB_SUMMARY_TABLE: '{DDB_SUMMARY_TABLE}'. Must be at least 3 characters.")


app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_reranker: Optional[Reranker] = None
_cache: Optional[InMemoryCache] = None
_session_store: Optional[SessionStore] = None


def _get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker(model_name=RERANKER_MODEL, device=RERANKER_DEVICE)
    return _reranker


def _get_cache() -> InMemoryCache:
    global _cache
    if _cache is None:
        _cache = InMemoryCache(ttl_seconds=CACHE_TTL, max_size=CACHE_MAX_SIZE)
    return _cache


def _get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        ttl_days_int: Optional[int] = None
        if DDB_TTL_DAYS and DDB_TTL_DAYS.isdigit():
            ttl_days_int = int(DDB_TTL_DAYS)
        _session_store = SessionStore(
            region_name=DDB_REGION,
            turns_table=DDB_TURNS_TABLE,
            summary_table=DDB_SUMMARY_TABLE,
            endpoint_url=DDB_ENDPOINT,
            ttl_days=ttl_days_int,
            max_recent=SESSION_RECENT_LIMIT,
            auto_create=DDB_AUTO_CREATE,
        )
    return _session_store


def _load_postgres_module():
    postgres_dir = os.path.join(ROOT_DIR, "postgres")
    postgres_file = os.path.join(postgres_dir, "langchain-postgres.py")
    if not os.path.exists(postgres_file):
        return None
    spec = importlib.util.spec_from_file_location("langchain_postgres", postgres_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_ingest_module():
    postgres_dir = os.path.join(ROOT_DIR, "postgres")
    ingest_file = os.path.join(postgres_dir, "ingest_fhir_json.py")
    if not os.path.exists(ingest_file):
        return None
    spec = importlib.util.spec_from_file_location("ingest_fhir_json", ingest_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document_id(doc: Document, fallback_index: int) -> str:
    doc_id = getattr(doc, "id", None)
    if doc_id:
        return str(doc_id)
    meta = doc.metadata or {}
    for key in ("chunk_id", "resource_id", "id"):
        if key in meta:
            return str(meta[key])
    content_hash = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
    return f"content:{fallback_index}:{content_hash}"


def _to_response(doc: Document, doc_id: str) -> DocumentResponse:
    return DocumentResponse(
        id=doc_id,
        content=doc.page_content,
        metadata=doc.metadata or {},
    )


async def _rerank_single(request: RerankRequest) -> RerankResponse:
    module = _load_postgres_module()
    if not module:
        raise HTTPException(status_code=500, detail="postgres/langchain-postgres.py not found")

    query = request.query
    k_retrieve = request.k_retrieve or DEFAULT_K_RETRIEVE
    k_return = request.k_return or DEFAULT_K_RETURN

    candidates: List[Document] = await module.search_similar_chunks(
        query=query,
        k=k_retrieve,
        filter_metadata=request.filter_metadata,
    )

    if not candidates:
        return RerankResponse(query=query, results=[])

    candidate_pairs = [(doc, _document_id(doc, idx)) for idx, doc in enumerate(candidates)]
    doc_ids = [doc_id for _doc, doc_id in candidate_pairs]
    cache_key = build_cache_key(query, doc_ids)
    cache = _get_cache()
    cached = cache.get(cache_key)

    if cached:
        cached_map = {doc_id: score for doc_id, score in cached}
        if all(doc_id in cached_map for doc_id in doc_ids):
            scored = [(idx, doc, doc_id) for idx, (doc, doc_id) in enumerate(candidate_pairs)]
            scored.sort(key=lambda item: (-cached_map[item[2]], item[0]))
            top_docs = scored[:k_return]
            results = [_to_response(doc, doc_id) for _idx, doc, doc_id in top_docs]
            return RerankResponse(query=query, results=results)

    reranker = _get_reranker()
    scored_docs = reranker.rerank_with_scores(query, candidates)
    doc_id_map = {id(doc): doc_id for doc, doc_id in candidate_pairs}
    scored_pairs: List[Tuple[str, float]] = []
    for doc, score in scored_docs:
        doc_id = doc_id_map.get(id(doc), "")
        if doc_id:
            scored_pairs.append((doc_id, score))
    cache.set(cache_key, scored_pairs)

    top_docs = scored_docs[:k_return]
    results = [_to_response(doc, doc_id_map.get(id(doc), _document_id(doc, idx))) for idx, (doc, _score) in enumerate(top_docs)]
    return RerankResponse(query=query, results=results)


async def _fetch_full_documents(patient_ids: List[str]) -> List[FullDocumentResponse]:
    if not patient_ids:
        return []
    module = _load_ingest_module()
    if not module:
        return []
    get_files = getattr(module, "get_latest_raw_files_by_patient_ids", None)
    if get_files is None:
        return []
    raw_files = await get_files(patient_ids)
    documents: List[FullDocumentResponse] = []
    for item in raw_files:
        documents.append(
            FullDocumentResponse(
                patient_id=item.get("patient_id", ""),
                source_filename=item.get("source_filename", ""),
                bundle_json=item.get("bundle_json", {}),
            )
        )
    return documents


@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest) -> RerankResponse:
    return await _rerank_single(request)


@app.post("/rerank/with-context", response_model=RerankWithContextResponse)
async def rerank_with_context(request: RerankWithContextRequest) -> RerankWithContextResponse:
    reranked = await _rerank_single(request)
    patient_ids = []
    for item in reranked.results:
        metadata = item.metadata or {}
        patient_id = metadata.get("patient_id")
        if patient_id:
            patient_ids.append(str(patient_id))
    full_documents = []
    if request.include_full_json:
        full_documents = await _fetch_full_documents(sorted(set(patient_ids)))
    return RerankWithContextResponse(query=reranked.query, chunks=reranked.results, full_documents=full_documents)


@app.post("/rerank/batch", response_model=BatchRerankResponse)
async def rerank_batch(request: BatchRerankRequest) -> BatchRerankResponse:
    tasks = [_rerank_single(item) for item in request.items]
    results = await asyncio.gather(*tasks)
    return BatchRerankResponse(items=results)


@app.get("/rerank/health")
async def rerank_health() -> Dict[str, str]:
    reranker = _get_reranker()
    return {"status": "healthy", "model": reranker.model_name, "device": reranker.device}


@app.get("/rerank/stats", response_model=StatsResponse)
async def rerank_stats() -> StatsResponse:
    reranker = _get_reranker()
    cache = _get_cache()
    stats = cache.stats()
    return StatsResponse(
        model_name=reranker.model_name,
        device=reranker.device,
        cache_hits=stats["hits"],
        cache_misses=stats["misses"],
        cache_size=stats["size"],
    )


# ---------------- Session memory endpoints (DynamoDB) ---------------- #


@app.post("/session/turn", response_model=SessionTurnResponse)
def append_session_turn(payload: SessionTurnRequest) -> SessionTurnResponse:
    store = _get_session_store()
    store.append_turn(
        session_id=payload.session_id,
        role=payload.role,
        text=payload.text,
        meta=payload.meta,
        patient_id=payload.patient_id,
    )
    recent = store.get_recent(payload.session_id, limit=payload.return_limit or SESSION_RECENT_LIMIT)
    summary = store.get_summary(payload.session_id)
    return SessionTurnResponse(session_id=payload.session_id, recent_turns=recent, summary=summary)


@app.get("/session/{session_id}", response_model=SessionTurnResponse)
def get_session_state(session_id: str, limit: int = SESSION_RECENT_LIMIT) -> SessionTurnResponse:
    store = _get_session_store()
    recent = store.get_recent(session_id, limit=limit)
    summary = store.get_summary(session_id)
    return SessionTurnResponse(session_id=session_id, recent_turns=recent, summary=summary)


@app.post("/session/summary")
def update_session_summary(payload: SessionSummaryUpdate) -> Dict[str, Any]:
    store = _get_session_store()
    store.update_summary(session_id=payload.session_id, summary=payload.summary, patient_id=payload.patient_id)
    summary = store.get_summary(payload.session_id)
    return {"session_id": payload.session_id, "summary": summary}


@app.delete("/session/{session_id}")
def clear_session(session_id: str) -> Dict[str, str]:
    store = _get_session_store()
    store.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


# ---------------- Multi-session management endpoints ---------------- #

import uuid
from datetime import datetime


@app.get("/sessions", response_model=SessionListResponse)
def list_sessions(user_id: str) -> SessionListResponse:
    """List all sessions for a user."""
    store = _get_session_store()
    sessions_data = store.list_sessions_by_user(user_id)
    
    sessions: List[SessionMetadata] = []
    for item in sessions_data:
        session_id = item.get("session_id", "")
        first_preview = store.get_first_message_preview(session_id)
        
        # Count messages
        recent = store.get_recent(session_id, limit=1000)  # Get all to count
        message_count = len([t for t in recent if t.get("role") == "user"])
        
        sessions.append(
            SessionMetadata(
                session_id=session_id,
                user_id=item.get("user_id", user_id),
                name=item.get("name"),
                description=item.get("description"),
                tags=item.get("tags", []),
                created_at=item.get("created_at", item.get("updated_at", datetime.utcnow().isoformat() + "Z")),
                last_activity=item.get("last_activity", item.get("updated_at", datetime.utcnow().isoformat() + "Z")),
                message_count=message_count,
                first_message_preview=first_preview,
            )
        )
    
    return SessionListResponse(sessions=sessions, count=len(sessions))


@app.get("/sessions/count", response_model=SessionCountResponse)
def get_session_count(user_id: str) -> SessionCountResponse:
    """Get session count for a user."""
    store = _get_session_store()
    count = store.get_session_count(user_id)
    return SessionCountResponse(user_id=user_id, count=count, max_allowed=5)


@app.post("/sessions", response_model=SessionMetadata)
def create_session(payload: SessionCreateRequest) -> SessionMetadata:
    """Create a new session."""
    store = _get_session_store()
    
    # Check session limit
    count = store.get_session_count(payload.user_id)
    if count >= 5:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Session limit reached",
                "code": "SESSION_LIMIT_EXCEEDED",
                "max_sessions": 5,
            }
        )
    
    # Generate new session_id
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    
    # Create summary with metadata
    summary: Dict[str, Any] = {
        "name": payload.name,
        "description": payload.description,
        "tags": payload.tags or [],
        "created_at": now,
        "last_activity": now,
    }
    
    store.update_summary(
        session_id=session_id,
        summary=summary,
        user_id=payload.user_id,
    )
    
    return SessionMetadata(
        session_id=session_id,
        user_id=payload.user_id,
        name=payload.name,
        description=payload.description,
        tags=payload.tags or [],
        created_at=now,
        last_activity=now,
        message_count=0,
        first_message_preview=None,
    )


@app.get("/sessions/{session_id}", response_model=SessionMetadata)
def get_session_metadata(session_id: str) -> SessionMetadata:
    """Get session metadata."""
    store = _get_session_store()
    summary = store.get_summary(session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    
    first_preview = store.get_first_message_preview(session_id)
    recent = store.get_recent(session_id, limit=1000)
    message_count = len([t for t in recent if t.get("role") == "user"])
    
    return SessionMetadata(
        session_id=session_id,
        user_id=summary.get("user_id", ""),
        name=summary.get("name"),
        description=summary.get("description"),
        tags=summary.get("tags", []),
        created_at=summary.get("created_at", summary.get("updated_at", datetime.utcnow().isoformat() + "Z")),
        last_activity=summary.get("last_activity", summary.get("updated_at", datetime.utcnow().isoformat() + "Z")),
        message_count=message_count,
        first_message_preview=first_preview,
    )


@app.put("/sessions/{session_id}", response_model=SessionMetadata)
def update_session_metadata(session_id: str, payload: SessionUpdateRequest) -> SessionMetadata:
    """Update session metadata."""
    store = _get_session_store()
    summary = store.get_summary(session_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update only provided fields
    updated_summary = summary.copy()
    if payload.name is not None:
        updated_summary["name"] = payload.name
    if payload.description is not None:
        updated_summary["description"] = payload.description
    if payload.tags is not None:
        updated_summary["tags"] = payload.tags
    
    updated_summary["last_activity"] = datetime.utcnow().isoformat() + "Z"
    
    store.update_summary(
        session_id=session_id,
        summary=updated_summary,
        user_id=summary.get("user_id"),
        patient_id=summary.get("patient_id"),
    )
    
    # Return updated metadata
    return get_session_metadata(session_id)


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a session."""
    store = _get_session_store()
    store.clear_session(session_id)
    return {"status": "deleted", "session_id": session_id}
