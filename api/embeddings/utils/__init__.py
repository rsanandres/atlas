"""Embeddings utilities."""

# Export main functions for backward compatibility
from api.embeddings.utils.helper import (
    get_chunk_embedding,
    process_and_store,
    semantic_chunking,
    recursive_json_chunking,
    parent_child_chunking,
    extract_resource_metadata,
)

__all__ = [
    "get_chunk_embedding",
    "process_and_store",
    "semantic_chunking",
    "recursive_json_chunking",
    "parent_child_chunking",
    "extract_resource_metadata",
]
