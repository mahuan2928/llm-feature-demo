# llm-feature-demo

A minimal FastAPI service that adds **one** LLM feature — summarization — to an
existing app, without touching your core codebase.

Your backend calls this little sidecar over HTTP. The sidecar talks to OpenAI.
API keys, prompts, and provider quirks stay in one small place instead of being
sprinkled through your main application.

> **This is the free demo.** It has exactly two endpoints and is meant to show
> the pattern. The production version is here:
>
> ### 👉 [LLM Feature Service — Full Version ($49)](https://mahuan220.gumroad.com/l/gwwrrn)

---

## What it does

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health` | none | Liveness check. Returns `{"status": "ok", ...}` |
| `POST /features/summarize` | `X-API-Key` | `{text, max_sentences?}` → `{summary, model, usage}` |

- Auth is a single shared key (`SERVICE_API_KEY`) your backend sends as an
  `X-API-Key` header. Missing/wrong key → `401`.
- If `OPENAI_API_KEY` is not set, `/features/summarize` returns a clean
  `503` JSON error explaining what's missing — it never crashes.
- Config is via `.env` (see `.env.example`). No database, no extra services.

## Quickstart

```bash
git clone https://github.com/mahuan2928/llm-feature-demo
cd llm-feature-demo

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set SERVICE_API_KEY to any long random string,
#            and OPENAI_API_KEY to your OpenAI key.

uvicorn app:app --port 8000
```

Check it's alive:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"llm-feature-demo","openai_configured":true}
```

Summarize something:

```bash
curl -X POST http://localhost:8000/features/summarize \
  -H 'X-API-Key: YOUR_SERVICE_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Paste a long article, ticket, or document here...", "max_sentences": 2}'
```

```json
{
  "summary": "The article explains ... in two concise sentences.",
  "model": "gpt-4o-mini",
  "usage": {"input_tokens": 812, "output_tokens": 41, "total_tokens": 853}
}
```

Python 3.10+ required.

## Run the smoke tests

```bash
python test_demo.py
```

Verifies: `/health` → 200, summarize without a key → 401, summarize with a
valid service key but no `OPENAI_API_KEY` → clean 503. See `TESTING.md`.

## Free demo vs Full version

| | Free demo (this repo) | [Full version ($49)](https://mahuan220.gumroad.com/l/gwwrrn) |
|---|---|---|
| Summarize endpoint | ✅ | ✅ |
| `/health` | ✅ | ✅ |
| API-key auth | ✅ single key | ✅ per-client identity (`X-Client-Id`) |
| Chat endpoint | ❌ | ✅ `/features/chat` |
| Streaming (SSE) | ❌ | ✅ token-by-token chat streaming |
| Classify endpoint | ❌ | ✅ `/features/classify` with your labels |
| Token budgets | ❌ | ✅ per-client daily caps — HTTP `402` **before** you overspend |
| Rate limiting | ❌ | ✅ per-client requests/minute |
| Retries / timeouts | ❌ | ✅ exponential backoff on 429/5xx |
| Call logging | ❌ | ✅ one JSON line per call (endpoint, client, tokens, latency) |
| Providers | OpenAI only | Provider abstraction (OpenAI default, Claude/Gemini adapters) |
| Missing-key behaviour | clean `503` | service refuses to start unauthenticated |

The demo proves the pattern in ~150 lines. The full version is what you
deploy when real users — and a real OpenAI bill — are involved:

**→ [Get the LLM Feature Service — $49](https://mahuan220.gumroad.com/l/gwwrrn)**

## How you'd use it in a real app

1. Run this service next to your app (same host, container network, or a
   small VM). Server-to-server only — never expose `SERVICE_API_KEY` to a
   browser or mobile app.
2. From your backend, `POST /features/summarize` whenever you need a summary:
   support tickets, articles, meeting notes, long form submissions.
3. That's it. When you outgrow the demo, the full version keeps the same
   request/response shape and adds budgets, streaming chat, and logging.

## License

MIT — see `LICENSE`. Use the demo freely, including commercially.

---

Built by **Marty Ma** — Senior AI & Data Engineer (Tokyo)
11+ years building production systems (Rakuten, NN Life, ByteDance Japan).
Full version: https://mahuan220.gumroad.com/l/gwwrrn
