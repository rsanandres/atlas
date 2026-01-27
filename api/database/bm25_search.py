"""BM25 full-text search using PostgreSQL tsvector.

This module provides keyword-based search using PostgreSQL's built-in
full-text search capabilities, complementing semantic vector search.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from langchain_core.documents import Document


# Schema and table configuration
SCHEMA_NAME = os.getenv("DB_SCHEMA", "hc_ai_schema")
TABLE_NAME = os.getenv("DB_TABLE", "hc_ai_table")


async def bm25_search(
    query: str,
    k: int = 50,
    filter_metadata: Optional[Dict[str, Any]] = None,
    engine=None,
) -> List[Document]:
    """
    Perform BM25 full-text search using PostgreSQL ts_rank.
    
    Args:
        query: Search query (will be converted to tsquery)
        k: Number of results to return
        filter_metadata: Optional metadata filters (e.g., {"patientId": "..."})
        engine: SQLAlchemy async engine (if not provided, uses global)
        
    Returns:
        List of Document objects sorted by BM25 relevance score
    """
    # Import here to avoid circular imports
    from api.database.postgres import _engine, initialize_vector_store
    
    if engine is None:
        if _engine is None:
            await initialize_vector_store()
        from api.database.postgres import _engine
        engine = _engine
    
    if not engine:
        return []
    
    # Build the base query with ts_rank for BM25-style scoring
    # plainto_tsquery handles natural language queries
    base_sql = f"""
        SELECT 
            langchain_id,
            content,
            langchain_metadata,
            ts_rank(ts_content, plainto_tsquery('english', :query)) as rank
        FROM "{SCHEMA_NAME}"."{TABLE_NAME}"
        WHERE ts_content @@ plainto_tsquery('english', :query)
    """
    
    params: Dict[str, Any] = {"query": query, "k": k}
    
    # Add metadata filters if provided
    where_clauses = []
    if filter_metadata:
        for key, value in filter_metadata.items():
            # Normalize patient_id to patientId (DB uses camelCase)
            db_key = "patientId" if key == "patient_id" else key
            param_name = f"meta_{db_key}"
            where_clauses.append(
                f"langchain_metadata->>'{db_key}' = :{param_name}"
            )
            params[param_name] = value
    
    if where_clauses:
        base_sql += " AND " + " AND ".join(where_clauses)
    
    # Order by rank and limit
    base_sql += """
        ORDER BY rank DESC
        LIMIT :k
    """
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(base_sql), params)
            rows = result.fetchall()
            
            documents = []
            for row in rows:
                # Handle both tuple and mapping access
                if hasattr(row, '_mapping'):
                    langchain_id = row._mapping['langchain_id']
                    content = row._mapping['content']
                    metadata = row._mapping['langchain_metadata'] or {}
                    rank = row._mapping['rank']
                else:
                    langchain_id, content, metadata, rank = row
                    
                # Add BM25 score to metadata for debugging
                if isinstance(metadata, dict):
                    metadata = {**metadata, "_bm25_score": float(rank)}
                    
                doc = Document(
                    id=str(langchain_id),
                    page_content=content or "",
                    metadata=metadata,
                )
                documents.append(doc)
                
            return documents
            
    except Exception as e:
        print(f"BM25 search error: {e}")
        return []


async def bm25_search_with_phrase(
    query: str,
    k: int = 50,
    filter_metadata: Optional[Dict[str, Any]] = None,
    engine=None,
) -> List[Document]:
    """
    Perform BM25 search with phrase matching support.
    
    Uses phraseto_tsquery for queries that should match as phrases.
    Better for exact code matching (e.g., "E11.9", "LOINC 2339-0").
    """
    from api.database.postgres import _engine, initialize_vector_store
    
    if engine is None:
        if _engine is None:
            await initialize_vector_store()
        from api.database.postgres import _engine
        engine = _engine
    
    if not engine:
        return []
    
    # For short queries or codes, use websearch_to_tsquery which handles special chars
    base_sql = f"""
        SELECT 
            langchain_id,
            content,
            langchain_metadata,
            ts_rank(ts_content, websearch_to_tsquery('english', :query)) as rank
        FROM "{SCHEMA_NAME}"."{TABLE_NAME}"
        WHERE ts_content @@ websearch_to_tsquery('english', :query)
    """
    
    params: Dict[str, Any] = {"query": query, "k": k}
    
    # Add metadata filters
    where_clauses = []
    if filter_metadata:
        for key, value in filter_metadata.items():
            db_key = "patientId" if key == "patient_id" else key
            param_name = f"meta_{db_key}"
            where_clauses.append(
                f"langchain_metadata->>'{db_key}' = :{param_name}"
            )
            params[param_name] = value
    
    if where_clauses:
        base_sql += " AND " + " AND ".join(where_clauses)
    
    base_sql += """
        ORDER BY rank DESC
        LIMIT :k
    """
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(base_sql), params)
            rows = result.fetchall()
            
            documents = []
            for row in rows:
                if hasattr(row, '_mapping'):
                    langchain_id = row._mapping['langchain_id']
                    content = row._mapping['content']
                    metadata = row._mapping['langchain_metadata'] or {}
                    rank = row._mapping['rank']
                else:
                    langchain_id, content, metadata, rank = row
                    
                if isinstance(metadata, dict):
                    metadata = {**metadata, "_bm25_score": float(rank)}
                    
                doc = Document(
                    id=str(langchain_id),
                    page_content=content or "",
                    metadata=metadata,
                )
                documents.append(doc)
                
            return documents
            
    except Exception as e:
        print(f"BM25 phrase search error: {e}")
        return []
