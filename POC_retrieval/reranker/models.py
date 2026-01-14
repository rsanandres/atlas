"""Pydantic models for reranker service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RerankRequest(BaseModel):
    query: str = Field(min_length=1)
    k_retrieve: int = Field(default=50, ge=1)
    k_return: int = Field(default=10, ge=1)
    filter_metadata: Optional[Dict[str, Any]] = None


class BatchRerankItem(BaseModel):
    query: str = Field(min_length=1)
    k_retrieve: int = Field(default=50, ge=1)
    k_return: int = Field(default=10, ge=1)
    filter_metadata: Optional[Dict[str, Any]] = None


class BatchRerankRequest(BaseModel):
    items: List[BatchRerankItem]


class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]


class RerankResponse(BaseModel):
    query: str
    results: List[DocumentResponse]


class BatchRerankResponse(BaseModel):
    items: List[RerankResponse]


class StatsResponse(BaseModel):
    model_name: str
    device: str
    cache_hits: int
    cache_misses: int
    cache_size: int
