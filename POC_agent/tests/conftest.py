"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv
import pytest_asyncio


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
