import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
import grpc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services import refine_pb2
from app.services import refine_pb2_grpc

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prompt Refinery API",
    version="1.0.0",
    description="AI-powered prompt refinement service"
)

# ============== SECURITY CONFIG ==============

# Rate limiting: { IP: [(timestamp, count), ...] }
rate_limit_store: dict = defaultdict(list)
RATE_LIMIT = 20  # requests per window
RATE_WINDOW = 60  # seconds

# CORS allowed origins (configure for production)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

# Max prompt length to prevent abuse
MAX_PROMPT_LENGTH = 5000

# Valid refinement modes
VALID_MODES = ["detailed", "concise", "structured", "multi_step"]


# ============== MIDDLEWARE ==============

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    # Clean old entries
    now = time.time()
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip]
        if now - ts < RATE_WINDOW
    ]

    # Check rate limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait before trying again."}
        )

    # Add current request
    rate_limit_store[client_ip].append(now)

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT - len(rate_limit_store[client_ip]))
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host
    method = request.method
    path = request.url.path

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(f"{client_ip} - {method} {path} - {response.status_code} - {duration:.3f}s")

    return response


# ============== MODELS ==============

class RefineRequest(BaseModel):
    prompt: str
    mode: str = "detailed"

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        if len(v) > MAX_PROMPT_LENGTH:
            raise ValueError(f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters")
        return v.strip()

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in VALID_MODES:
            raise ValueError(f"Invalid mode. Must be one of: {VALID_MODES}")
        return v


class RefineResponse(BaseModel):
    refined_prompt: str
    intent: str
    original_score: int
    refined_score: int
    improvements: list


# ============== HELPERS ==============

GRPC_TARGET = os.getenv("GRPC_TARGET", "localhost:50051")


class GrpcClient:
    """Singleton gRPC client with a persistent channel and auto-reconnect."""

    _instance: Optional["GrpcClient"] = None
    _channel: Optional[grpc.Channel] = None
    _stub: Optional[refine_pb2_grpc.PromptRefinerStub] = None

    def __new__(cls) -> "GrpcClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self) -> None:
        """Create (or recreate) the channel and stub."""
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception:
                pass
        self._channel = grpc.insecure_channel(
            GRPC_TARGET,
            options=[
                ("grpc.keepalive_time_ms", 30_000),
                ("grpc.keepalive_timeout_ms", 10_000),
                ("grpc.keepalive_permit_without_calls", True),
                ("grpc.http2.max_pings_without_data", 0),
            ],
        )
        self._stub = refine_pb2_grpc.PromptRefinerStub(self._channel)
        logger.info(f"gRPC channel established → {GRPC_TARGET}")

    def get_stub(self) -> refine_pb2_grpc.PromptRefinerStub:
        """Return the cached stub."""
        return self._stub


_grpc_client: Optional[GrpcClient] = None


def get_grpc_stub() -> refine_pb2_grpc.PromptRefinerStub:
    """Return the shared gRPC stub (creates the singleton on first call)."""
    global _grpc_client
    if _grpc_client is None:
        _grpc_client = GrpcClient()
    return _grpc_client.get_stub()


# ============== ENDPOINTS ==============

@app.post("/refine", response_model=RefineResponse, tags=["refine"])
async def refine_prompt(request: RefineRequest):
    """Refine a user prompt to improve LLM output quality.

    - **prompt**: The original prompt to refine (max 5000 chars)
    - **mode**: Refinement style - detailed, concise, structured, or multi_step

    Returns the refined prompt with analysis and improvement suggestions.
    """
    try:
        stub = get_grpc_stub()

        grpc_request = refine_pb2.RefineRequest(
            original_prompt=request.prompt,
            refinement_mode=request.mode
        )

        response = stub.RefinePrompt(grpc_request)

        return RefineResponse(
            refined_prompt=response.refined_prompt,
            intent=response.intent_detected,
            original_score=response.original_score,
            refined_score=response.refined_score,
            improvements=list(response.improvements)
        )
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e.code()} - {e.details()}")
        raise HTTPException(status_code=503, detail="Refinement service temporarily unavailable")


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "prompt-refinery",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/", tags=["root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": "Prompt Refinery API",
        "version": "1.0.0",
        "docs": "/docs",
        "security": {
            "rate_limit": f"{RATE_LIMIT} requests per {RATE_WINDOW} seconds",
            "max_prompt_length": MAX_PROMPT_LENGTH
        },
        "endpoints": {
            "refine": "POST /refine",
            "health": "GET /health"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)