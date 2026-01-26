"""CORS and other middleware configuration."""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js default ports
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
