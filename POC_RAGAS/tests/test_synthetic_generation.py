"""Test synthetic testset generation — deferred for RAGAS v0.4 migration."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_generate_synthetic_testset():
    pytest.skip(
        "Synthetic testset generation not yet migrated to RAGAS v0.4. "
        "Use scripts/generate_patient_tests.py instead."
    )
