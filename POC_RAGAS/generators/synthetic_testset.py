"""Synthetic testset generation — deferred for RAGAS v0.4 migration.

The RAGAS v0.4 TestsetGenerator API changed significantly from v0.1.
Use `scripts/generate_patient_tests.py` (template-based) for testset generation instead.
"""

from __future__ import annotations


def generate_synthetic_testset(*args, **kwargs):
    raise NotImplementedError(
        "Synthetic testset generation has not been migrated to RAGAS v0.4. "
        "Use scripts/generate_patient_tests.py for template-based testset generation."
    )
