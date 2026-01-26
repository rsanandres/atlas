"""Cross-encoder reranker implementation."""

from __future__ import annotations

from typing import List

import torch
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


def _resolve_device(device: str) -> str:
    if device and device.lower() != "auto":
        return device
    return "cuda" if torch.cuda.is_available() else "cpu"


class Reranker:
    """Cross-encoder reranker that scores query-document pairs."""

    def __init__(self, model_name: str, device: str = "auto") -> None:
        resolved_device = _resolve_device(device)
        self._device = resolved_device
        self._model_name = model_name
        self._model = CrossEncoder(model_name, device=resolved_device)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return self._device

    def score(self, query: str, docs: List[str]) -> List[float]:
        pairs = [(query, doc) for doc in docs]
        scores = self._model.predict(pairs)
        return [float(score) for score in scores]

    def rerank(self, query: str, docs: List[Document], top_k: int) -> List[Document]:
        if not docs:
            return []
        contents = [doc.page_content for doc in docs]
        scores = self.score(query, contents)
        scored_docs = [(idx, doc, score) for idx, (doc, score) in enumerate(zip(docs, scores))]
        scored_docs.sort(key=lambda item: (-item[2], item[0]))
        return [doc for _idx, doc, _score in scored_docs[:top_k]]

    def rerank_with_scores(self, query: str, docs: List[Document]) -> List[tuple[Document, float]]:
        if not docs:
            return []
        contents = [doc.page_content for doc in docs]
        scores = self.score(query, contents)
        scored_docs = [(idx, doc, score) for idx, (doc, score) in enumerate(zip(docs, scores))]
        scored_docs.sort(key=lambda item: (-item[2], item[0]))
        return [(doc, score) for _idx, doc, score in scored_docs]

    def rerank_batch(
        self,
        queries: List[str],
        docs_list: List[List[Document]],
        top_k: int,
    ) -> List[List[Document]]:
        if len(queries) != len(docs_list):
            raise ValueError("queries and docs_list length mismatch")
        results: List[List[Document]] = []
        for query, docs in zip(queries, docs_list):
            results.append(self.rerank(query, docs, top_k))
        return results
