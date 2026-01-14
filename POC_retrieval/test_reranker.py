"""Simple CLI script to test reranker on a single query."""

from __future__ import annotations

import json
import sys
import urllib.request


DEFAULT_URL = "http://localhost:8001/rerank"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python POC_retrieval/test_reranker.py \"your query here\"")
        return 1

    query = sys.argv[1]
    payload = {
        "query": query,
        "k_retrieve": 50,
        "k_return": 10,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEFAULT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)
    except Exception as exc:
        print(f"Error calling reranker service: {exc}")
        print("Is the service running? Try:")
        print("  uvicorn POC_retrieval.reranker.service:app --reload --port 8001")
        return 1

    results = result.get("results", [])
    print(f"Query: {query}")
    print(f"Returned {len(results)} documents")
    for idx, doc in enumerate(results, start=1):
        content_preview = doc.get("content", "")[:200].replace("\n", " ")
        metadata = doc.get("metadata", {})
        print(f"\n[{idx}] {doc.get('id')}")
        print(f"Preview: {content_preview}")
        print(f"Metadata: {metadata}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
