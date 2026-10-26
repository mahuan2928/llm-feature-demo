"""llm-feature-demo — a minimal LLM feature service (free demo).

A tiny FastAPI sidecar that adds ONE LLM feature to an existing app:
summarization. Your backend calls this service over HTTP; this service
talks to OpenAI. That keeps API keys and prompt logic out of your core
codebase.

Run:
    uvicorn app:app --port 8000

Endpoints:
    GET  /health              — no auth, liveness check
    POST /features/summarize  — requires X-API-Key header

This is the free demo of the LLM Feature Service. The full version adds
chat (SSE streaming), classification, per-client token budgets, rate
limits, retries with backoff, JSON call logging, and a provider
abstraction for OpenAI / Claude / Gemini.
https://mahuan220.gumroad.com/l/gwwrrn
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Minimal .env loader (avoids an extra dependency for the demo)
# ---------------------------------------------------------------------------
def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LLM Feature Demo",
    version="0.1.0",
    description="Free demo: one LLM feature (summarize) as a clean HTTP sidecar.",
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Check X-API-Key against SERVICE_API_KEY from the environment."""
    expected = os.getenv("SERVICE_API_KEY")
    if not expected:
        # Server misconfigured — fail closed, explain plainly.
        raise HTTPException(
            status_code=503,
            detail="SERVICE_API_KEY is not set on the server. "
                   "Copy .env.example to .env and set a key.",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, description="Text to summarize")
    max_sentences: int = Field(default=3, ge=1, le=10)


class SummarizeResponse(BaseModel):
    summary: str
    model: str
    usage: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "llm-feature-demo",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/features/summarize", dependencies=[Depends(require_api_key)])
def summarize(req: SummarizeRequest):
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        # Clean, actionable error — never crash on a missing key.
        return JSONResponse(
            status_code=503,
            content={
                "detail": "OPENAI_API_KEY is not set. Copy .env.example to .env "
                          "and add your OpenAI API key, then restart the service."
            },
        )

    # Imported here so the service (and /health) still starts without
    # the key path being exercised.
    from openai import OpenAI

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=openai_key)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Summarize the user's text in at most "
                        f"{req.max_sentences} sentence(s). "
                        f"Keep key facts, names, and numbers. Be concise."
                    ),
                },
                {"role": "user", "content": req.text},
            ],
            temperature=0.3,
        )
    except Exception as exc:  # provider / network failure
        raise HTTPException(status_code=502, detail=f"LLM provider error: {exc}") from exc

    choice = completion.choices[0].message.content or ""
    usage = {}
    if completion.usage:
        usage = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
            "total_tokens": completion.usage.total_tokens,
        }

    return SummarizeResponse(summary=choice.strip(), model=model, usage=usage)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
