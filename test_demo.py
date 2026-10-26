"""Smoke tests for llm-feature-demo.

Run:
    python test_demo.py

Covers the three behaviours that must never regress:
  1. GET /health returns 200 (no auth)
  2. POST /features/summarize without X-API-Key returns 401
  3. POST /features/summarize with a valid X-API-Key but no
     OPENAI_API_KEY returns a clean 503 JSON error (never a crash)

No real OpenAI call is made — test 3 stops at the missing-key check.
"""
from __future__ import annotations

import os
import sys

# Set a known service key BEFORE importing the app, and make sure no
# OpenAI key leaks in from the developer's shell / .env.
os.environ["SERVICE_API_KEY"] = "test-service-key"
os.environ.pop("OPENAI_API_KEY", None)

# Prevent app.py's .env loader from re-adding an OPENAI_API_KEY from a
# local .env file during the test: run from this directory only if you
# have not copied a real key into .env. To be safe, we also clear it
# after import if it came from .env (the loader uses setdefault, and
# we popped it above, so a .env value WOULD be loaded — handle that).
from fastapi.testclient import TestClient  # noqa: E402

import app as app_module  # noqa: E402

# If a local .env provided OPENAI_API_KEY, remove it for test 3's sake.
_removed = os.environ.pop("OPENAI_API_KEY", None)
if _removed:
    print("note: ignored OPENAI_API_KEY from .env for the missing-key test")

client = TestClient(app_module.app, raise_server_exceptions=False)

FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def main() -> int:
    # 1. /health returns 200, no auth needed
    r = client.get("/health")
    check("GET /health returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:120]}")
    if r.status_code == 200:
        check("GET /health body has status ok", r.json().get("status") == "ok", str(r.json()))

    # 2. /features/summarize without X-API-Key returns 401
    r = client.post("/features/summarize", json={"text": "Hello world, this is a test."})
    check("POST /features/summarize without X-API-Key returns 401",
          r.status_code == 401, f"got {r.status_code}: {r.text[:120]}")

    # 2b. Wrong key also returns 401
    r = client.post(
        "/features/summarize",
        headers={"X-API-Key": "wrong-key"},
        json={"text": "Hello world, this is a test."},
    )
    check("POST /features/summarize with wrong X-API-Key returns 401",
          r.status_code == 401, f"got {r.status_code}: {r.text[:120]}")

    # 3. Valid service key, but no OPENAI_API_KEY -> clean 503 JSON error
    r = client.post(
        "/features/summarize",
        headers={"X-API-Key": "test-service-key"},
        json={"text": "A long article that needs summarizing.", "max_sentences": 2},
    )
    check("POST /features/summarize with key but no OPENAI_API_KEY returns 503",
          r.status_code == 503, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 503:
        try:
            body = r.json()
            detail = str(body.get("detail", ""))
        except Exception:
            detail = ""
            body = {}
        check("503 body is JSON with a detail explaining OPENAI_API_KEY is missing",
              "OPENAI_API_KEY" in detail, f"body={body}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} test(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
