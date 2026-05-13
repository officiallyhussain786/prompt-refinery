import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from pathlib import Path

# Load .env from backend root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prompt Refinery API",
    version="1.0.0",
    description="AI-powered prompt refinement service"
)

# ============== SECURITY CONFIG ==============

rate_limit_store: dict = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 60

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

MAX_PROMPT_LENGTH = 5000
VALID_MODES = ["detailed", "concise", "structured", "multi_step"]


# ============== MIDDLEWARE ==============

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host

    now = time.time()
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip]
        if now - ts < RATE_WINDOW
    ]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait before trying again."}
        )

    rate_limit_store[client_ip].append(now)

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT - len(rate_limit_store[client_ip]))
    return response


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


# ============== SERVICE CLIENTS ==============

_refiner = None
_retriever = None


def get_services():
    """Lazy load services to handle initialization errors gracefully."""
    global _refiner, _retriever

    if _retriever is None:
        from app.rag.retriever import get_retriever
        _retriever = get_retriever()

    if _refiner is None:
        from app.services.refiner import get_refiner
        _refiner = get_refiner()

    return _refiner, _retriever


# ============== ENDPOINTS ==============

@app.post("/refine", response_model=RefineResponse, tags=["refine"])
async def refine_prompt(request: RefineRequest):
    """Refine a user prompt to improve LLM output quality."""
    try:
        refiner, retriever = get_services()

        patterns = retriever.search(request.prompt, request.mode)

        result = refiner.refine(
            request.prompt, request.mode, patterns
        )

        return RefineResponse(
            refined_prompt=result["refined_prompt"],
            intent=result["intent"],
            original_score=result["original_score"],
            refined_score=result["refined_score"],
            improvements=result["improvements"]
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=503, detail="Service not configured. Check environment variables.")
    except Exception as e:
        logger.error(f"Error during refinement: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during refinement")


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