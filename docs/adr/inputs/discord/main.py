"""
llm_mcp/main.py

Layer 2 LLM Gateway — FastAPI Microservice.
Empfang von Discord /chat → System-Prompt → OpenRouter → Antwort.

Alternative: Celery Task (siehe ADR-114 Review, Option B).
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import httpx
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─── Settings ─────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_MCP_", env_file=".env")

    api_key: str = Field(..., description="Interner API-Key für Service-zu-Service Auth")
    openrouter_api_key: str = Field(..., description="OpenRouter API Key")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-4o"
    max_tokens: int = 2048
    request_timeout: float = 55.0
    log_level: str = "INFO"


settings = Settings()  # type: ignore[call-arg]


# ─── Logging ──────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
log = structlog.get_logger()


# ─── HTTP Client (shared, mit Connection Pooling) ─────────────────────────────

_http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": "https://iil.gmbh",
            "X-Title": "iil-platform-llm-gateway",
        },
        timeout=settings.request_timeout,
    )
    log.info("startup", model=settings.default_model)
    yield
    await _http_client.aclose()
    log.info("shutdown")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="llm_mcp — LLM Gateway",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,   # Kein Swagger in Produktion
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://orchestrator_mcp:8000"],  # Nur intern
    allow_methods=["POST"],
    allow_headers=["Authorization", "X-Correlation-ID"],
)


# ─── Auth Dependency ──────────────────────────────────────────────────────────

async def verify_api_key(request: Request) -> None:
    """Service-zu-Service API-Key Validierung."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = auth.split(" ", 1)[1]
    if token != settings.api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    system_prompt: str = Field(default="Du bist ein hilfreicher Assistent.")
    model: Optional[str] = None
    user_id: str = Field(..., description="Discord User ID für Logging")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])


class ChatResponse(BaseModel):
    answer: str
    model: str
    tokens_used: int
    correlation_id: str
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    model: str
    uptime_s: float


# ─── Routes ───────────────────────────────────────────────────────────────────

_start_time = time.monotonic()


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health-Check ohne Auth (für interne Monitoring-Tools)."""
    return HealthResponse(
        status="ok",
        model=settings.default_model,
        uptime_s=round(time.monotonic() - _start_time, 1),
    )


@app.post(
    "/v1/chat",
    response_model=ChatResponse,
    dependencies=[Depends(verify_api_key)],
    summary="LLM Chat mit Platform-Kontext",
)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Hauptendpoint: Empfängt Frage + System-Prompt, gibt LLM-Antwort zurück.

    Retry-Logik: Bei OpenRouter-Fehler (5xx) 1x automatisch wiederholen.
    Idempotenz: correlation_id wird durchgereicht für Request-Deduplication.
    """
    assert _http_client is not None, "HTTP Client nicht initialisiert"

    model = req.model or settings.default_model
    t0 = time.monotonic()

    bound_log = log.bind(
        correlation_id=req.correlation_id,
        user_id=req.user_id,
        model=model,
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": req.system_prompt},
            {"role": "user",   "content": req.message},
        ],
        "max_tokens": settings.max_tokens,
    }

    # Mit 1x Retry bei 5xx
    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            resp = await _http_client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            break
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code < 500 or attempt == 1:
                raise
            bound_log.warning("openrouter_retry", status=e.response.status_code)
        except httpx.RequestError as e:
            last_error = e
            if attempt == 1:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"LLM-Service nicht erreichbar: {e}",
                )
            bound_log.warning("openrouter_retry_network", error=str(e))

    if last_error and "data" not in dir():
        raise HTTPException(status_code=502, detail="OpenRouter nicht erreichbar")

    answer = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", 0)
    latency_ms = int((time.monotonic() - t0) * 1000)

    bound_log.info(
        "chat_completed",
        tokens=tokens,
        latency_ms=latency_ms,
    )

    return ChatResponse(
        answer=answer,
        model=data.get("model", model),
        tokens_used=tokens,
        correlation_id=req.correlation_id,
        latency_ms=latency_ms,
    )


# ─── Error Handler ────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Interner Fehler. Bitte Logs prüfen."},
    )
