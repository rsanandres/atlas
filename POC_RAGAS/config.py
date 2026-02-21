"""Configuration for RAGAS evaluation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class RagasConfig:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ragas_model: str = os.getenv("RAGAS_MODEL", "gpt-4o-mini")
    test_set_size: int = int(os.getenv("RAGAS_TEST_SET_SIZE", "120"))
    question_distribution_simple: float = float(os.getenv("RAGAS_Q_SIMPLE", "0.4"))
    question_distribution_multihop: float = float(os.getenv("RAGAS_Q_MULTI", "0.35"))
    question_distribution_conditional: float = float(os.getenv("RAGAS_Q_COND", "0.25"))
    noise_ratio: float = float(os.getenv("RAGAS_NOISE_RATIO", "0.25"))
    noise_seed: int = int(os.getenv("RAGAS_NOISE_SEED", "42"))

    data_dir: Path = Path(os.getenv("RAGAS_DATA_DIR", REPO_ROOT / "data" / "fhir"))
    testset_dir: Path = Path(os.getenv("RAGAS_TESTSET_DIR", Path(__file__).resolve().parent / "data" / "testsets"))
    results_dir: Path = Path(os.getenv("RAGAS_RESULTS_DIR", Path(__file__).resolve().parent / "data" / "results"))
    checkpoint_dir: Path = Path(os.getenv("RAGAS_CHECKPOINT_DIR", Path(__file__).resolve().parent / "data" / "checkpoints"))
    checkpoint_interval: int = int(os.getenv("RAGAS_CHECKPOINT_INTERVAL", "10"))

    agent_api_url: str = os.getenv("AGENT_API_URL", "https://api.hcai.rsanandres.com/agent/query")
    api_cooldown_seconds: int = int(os.getenv("RAGAS_API_COOLDOWN", "7"))

    include_full_json: bool = os.getenv("RAGAS_INCLUDE_FULL_JSON", "false").lower() in {"1", "true", "yes"}


CONFIG = RagasConfig()
