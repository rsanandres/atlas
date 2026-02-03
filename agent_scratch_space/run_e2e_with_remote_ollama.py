"""
Run the Agent API with a remote Ollama endpoint, then execute E2E tests — all in one go.

- Sets OLLAMA_BASE_URL so the API uses the remote Ollama (default: Tailscale 100.91.76.71:11434).
- Optionally verifies the remote Ollama (GET /api/tags) before starting.
- Starts the unified API (uvicorn) in a subprocess with that env.
- Waits for /health, then runs the E2E tests from test_e2e_agent.py against localhost:8000.
- Shuts down the API when tests finish.

Usage:
  # Use default remote Ollama (100.91.76.71:11434)
  python agent_scratch_space/run_e2e_with_remote_ollama.py

  # Override remote Ollama URL
  OLLAMA_BASE_URL=http://100.91.76.71:11434 python agent_scratch_space/run_e2e_with_remote_ollama.py

  # Skip pre-check of Ollama (start API anyway)
  SKIP_OLLAMA_CHECK=1 python agent_scratch_space/run_e2e_with_remote_ollama.py
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

# Project root (repo root) so "api.main:app" resolves; scratch space so test_e2e_agent resolves
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRATCH_SPACE = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRATCH_SPACE) not in sys.path:
    sys.path.insert(0, str(SCRATCH_SPACE))

# Default: Tailscale IPv4 with default Ollama port
DEFAULT_OLLAMA_BASE_URL = "http://100.91.76.71:11434"
API_BASE = "http://localhost:8000"
API_PORT = "8000"
HEALTH_TIMEOUT_SEC = 60
HEALTH_POLL_INTERVAL_SEC = 1.0


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def verify_remote_ollama(base_url: str) -> bool:
    """Verify the remote Ollama is reachable and return True on success."""
    try:
        r = httpx.get(f"{base_url}/api/tags", timeout=10)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        names = [m.get("name") for m in models if m.get("name")]
        print(f"  Ollama at {base_url}: OK — models: {names[:5]}{'...' if len(names) > 5 else ''}")
        return True
    except Exception as e:
        print(f"  Ollama at {base_url}: FAIL — {e}")
        return False


def wait_for_api(timeout_sec: float = HEALTH_TIMEOUT_SEC) -> bool:
    """Poll /health until 200 or timeout. Return True if healthy."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{API_BASE}/health", timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(HEALTH_POLL_INTERVAL_SEC)
    return False


def main() -> int:
    ollama_base = get_ollama_base_url()
    print("=" * 70)
    print("E2E with remote Ollama: start API + run tests")
    print("=" * 70)
    print(f"  OLLAMA_BASE_URL = {ollama_base}")
    print(f"  API will listen on {API_BASE}")
    print()

    if not os.getenv("SKIP_OLLAMA_CHECK"):
        print("Verifying remote Ollama...")
        if not verify_remote_ollama(ollama_base):
            print("  Optional: set SKIP_OLLAMA_CHECK=1 to start the API anyway.")
            return 1
        print()

    env = os.environ.copy()
    env["OLLAMA_BASE_URL"] = ollama_base
    env["API_PORT"] = API_PORT

    proc = None
    try:
        print("Starting Agent API (uvicorn)...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", API_PORT],
            env=env,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(f"  PID {proc.pid}")

        print("Waiting for API health...")
        if not wait_for_api():
            print("  API did not become healthy in time.")
            return 1
        print("  API is healthy.\n")

        # Run E2E tests (same process): import and run async main from test_e2e_agent
        import test_e2e_agent as e2e
        e2e.API_BASE = API_BASE
        asyncio.run(e2e.main())

        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if proc is not None:
            print("\nShutting down API...")
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            print("  API stopped.")


if __name__ == "__main__":
    sys.exit(main())
