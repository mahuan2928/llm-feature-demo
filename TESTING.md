# Testing — llm-feature-demo

Smoke tests for the three behaviours that must never regress. No real
OpenAI call is made: the third test stops at the missing-key check,
which happens before any provider request.

## Environment

- Date: 2026-10-26
- Python: 3.12.3 (demo requires 3.10+)
- Installed from `requirements.txt` in a fresh venv:
  - fastapi==0.115.12
  - uvicorn==0.34.2
  - openai==1.82.0
  - pydantic==2.11.7
  - httpx==0.28.1 (required by FastAPI's TestClient)

## Commands

```bash
cd llm-feature-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python test_demo.py
```

## Test cases

`test_demo.py` uses FastAPI's `TestClient`, sets
`SERVICE_API_KEY=test-service-key`, and ensures `OPENAI_API_KEY` is
**not** set:

1. `GET /health` returns 200
2. `POST /features/summarize` without `X-API-Key` returns 401
   (plus a bonus check: a wrong key also returns 401)
3. `POST /features/summarize` with the valid `X-API-Key` but no
   `OPENAI_API_KEY` returns 503 with a clean JSON error naming the
   missing key

## Output (2026-10-26)

```
[PASS] GET /health returns 200 — got 200: {"status":"ok","service":"llm-feature-demo","openai_configured":false}
[PASS] GET /health body has status ok — {'status': 'ok', 'service': 'llm-feature-demo', 'openai_configured': False}
[PASS] POST /features/summarize without X-API-Key returns 401 — got 401: {"detail":"Invalid or missing X-API-Key."}
[PASS] POST /features/summarize with wrong X-API-Key returns 401 — got 401: {"detail":"Invalid or missing X-API-Key."}
[PASS] POST /features/summarize with key but no OPENAI_API_KEY returns 503 — got 503: {"detail":"OPENAI_API_KEY is not set. Copy .env.example to .env and add your OpenAI API key, then restart the service."}
[PASS] 503 body is JSON with a detail explaining OPENAI_API_KEY is missing — body={'detail': 'OPENAI_API_KEY is not set. Copy .env.example to .env and add your OpenAI API key, then restart the service.'}

All smoke tests passed.
```

Exit code: 0 — **all 3 required smoke tests pass** (6 checks total
including the bonus wrong-key and body checks).

## Not covered

- A live summarize call against the real OpenAI API (requires a paid
  key; the code path is a single `chat.completions.create` call and is
  exercised by the full version's template testing).
- Load / concurrency behaviour — out of scope for a demo.
