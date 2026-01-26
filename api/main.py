"""Main FastAPI application with all routers."""

from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI

import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.env_loader import load_env_recursive
from api.shared.middleware import setup_cors

# Load environment variables
load_env_recursive(ROOT_DIR)

# Create FastAPI app
app = FastAPI(
    title="HC AI Unified API",
    description="Unified API for agent, embeddings, retrieval, session, and database services",
    version="1.0.0",
)

# Setup CORS
setup_cors(app)

# Import routers
from api.agent import router as agent_router
from api.embeddings import router as embeddings_router
from api.retrieval import router as retrieval_router
from api.session import router as session_router
from api.database import router as database_router

# Mount routers
app.include_router(agent_router, prefix="/agent", tags=["agent"])
app.include_router(embeddings_router, prefix="/embeddings", tags=["embeddings"])
app.include_router(retrieval_router, prefix="/retrieval", tags=["retrieval"])
app.include_router(session_router, prefix="/session", tags=["session"])
app.include_router(database_router, prefix="/db", tags=["database"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "HC AI Unified API",
        "version": "1.0.0",
        "endpoints": {
            "agent": "/agent/*",
            "embeddings": "/embeddings/*",
            "retrieval": "/retrieval/*",
            "session": "/session/*",
            "database": "/db/*",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
