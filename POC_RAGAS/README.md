# POC_RAGAS Evaluation Suite

RAGAS-based evaluation tooling for the Atlas medical RAG agent. Runs against the **production API** using OpenAI gpt-4o-mini as the judge LLM.

**RAGAS version:** v0.4.3+

## What it evaluates

- **Faithfulness** — Are responses grounded in the retrieved contexts?
- **Response relevancy** — Does the response actually answer the question?
- **Noise sensitivity** — How much does injecting irrelevant context degrade faithfulness?

## Prerequisites

- Atlas production API running (ALB endpoint or custom domain via `AGENT_API_URL`)
- `OPENAI_API_KEY` in the repo root `.env` file
- Python 3.11+

## Setup

```bash
pip install -r POC_RAGAS/requirements.txt
```

Create a `.env` file in the repo root (already in `.gitignore`):

```
OPENAI_API_KEY=sk-...
```

## Health check

```bash
python POC_RAGAS/scripts/check_services.py
```

## Run smoke test (5 questions)

```bash
python POC_RAGAS/scripts/run_evaluation.py \
    --testset POC_RAGAS/data/testsets/smoke_test.json \
    --cooldown 7 \
    --output-id smoke_v04
```

Results saved to:
- `POC_RAGAS/data/results/results_smoke_v04.json`
- `POC_RAGAS/data/results/report_smoke_v04.md`

## Run full evaluation

```bash
python POC_RAGAS/scripts/run_evaluation.py \
    --testset POC_RAGAS/data/testsets/patient_tests.json \
    --cooldown 7 \
    --output-id full
```

## Generate testsets

Template-based generation (no RAGAS dependency):

```bash
python POC_RAGAS/scripts/generate_patient_tests.py
```

## Rate limiting

The production API has a **10 req/min rate limit**. The default cooldown is 7 seconds between requests (`RAGAS_API_COOLDOWN` env var or `--cooldown` flag). 429 responses are automatically retried with backoff.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key for judge LLM |
| `RAGAS_MODEL` | `gpt-4o-mini` | OpenAI model for RAGAS scoring |
| `AGENT_API_URL` | `https://api.hcai.rsanandres.com/agent/query` | Atlas API endpoint |
| `RAGAS_API_COOLDOWN` | `7` | Seconds between API requests |
| `RAGAS_NOISE_RATIO` | `0.25` | Fraction of noise contexts to inject |
| `RAGAS_CHECKPOINT_INTERVAL` | `10` | Save checkpoint every N samples |

## API cost estimates

| Run | OpenAI cost |
|-----|-------------|
| Smoke test (5 questions) | ~$0.01-0.05 |
| Full eval (200 questions) | ~$1-5 |

Uses gpt-4o-mini for judging and text-embedding-3-small for relevancy embeddings.
