import os
import sys
import time
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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
    "https://huggingface.co",
    "https://hussain4214-prompt-refinery.hf.space",
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
    """Root endpoint with UI."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Prompt Refinery</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; padding: 40px 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            h1 { text-align: center; margin-bottom: 30px; color: #58a6ff; }
            .terminal { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; }
            label { display: block; margin-bottom: 8px; color: #8b949e; font-size: 14px; }
            textarea { width: 100%; background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 16px; color: #c9d1d9; font-size: 14px; min-height: 100px; resize: vertical; margin-bottom: 16px; }
            textarea:focus { outline: none; border-color: #58a6ff; }
            .modes { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
            .mode-btn { background: transparent; border: 1px solid #30363d; color: #8b949e; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
            .mode-btn.active { background: #238636; color: white; border-color: #238636; }
            .refine-btn { width: 100%; background: #238636; border: none; color: white; padding: 14px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
            .refine-btn:disabled { opacity: 0.5; cursor: not-allowed; }
            .result { margin-top: 20px; padding: 16px; background: #0d1117; border-radius: 8px; display: none; }
            .result.show { display: block; }
            .result h3 { color: #58a6ff; font-size: 12px; margin-bottom: 12px; }
            .result pre { white-space: pre-wrap; font-size: 14px; line-height: 1.6; }
            .scores { display: flex; gap: 16px; margin-top: 16px; }
            .score { flex: 1; padding: 12px; background: #0d1117; border-radius: 8px; text-align: center; }
            .score-label { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
            .score-value { font-size: 20px; font-weight: bold; }
            .error { background: #f8514922; border: 1px solid #f85149; color: #f85149; padding: 12px; border-radius: 8px; margin-top: 16px; display: none; }
            .error.show { display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>[PROMPT REFINERY]</h1>
            <div class="terminal">
                <label>Enter your prompt</label>
                <textarea id="prompt" placeholder="write a python function to calculate fibonacci..."></textarea>
                <label>Refinement Mode</label>
                <div class="modes">
                    <button class="mode-btn active" data-mode="detailed">DETAILED</button>
                    <button class="mode-btn" data-mode="concise">CONCISE</button>
                    <button class="mode-btn" data-mode="structured">STRUCTURED</button>
                    <button class="mode-btn" data-mode="multi_step">MULTI_STEP</button>
                </div>
                <button class="refine-btn" onclick="refine()">REFINE PROMPT</button>
                <div class="error" id="error"></div>
                <div class="result" id="result">
                    <h3>REFINED PROMPT</h3>
                    <pre id="refined"></pre>
                    <div class="scores">
                        <div class="score"><div class="score-label">ORIGINAL</div><div class="score-value" id="origScore">-</div></div>
                        <div class="score"><div class="score-label">REFINED</div><div class="score-value" id="refScore">-</div></div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            let mode = 'detailed';
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.onclick = () => {
                    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    mode = btn.dataset.mode;
                };
            });
            async function refine() {
                const prompt = document.getElementById('prompt').value;
                if (!prompt) return;
                document.querySelector('.refine-btn').disabled = true;
                document.getElementById('error').classList.remove('show');
                document.getElementById('result').classList.remove('show');
                try {
                    const res = await fetch('/refine', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({prompt, mode})
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Error');
                    document.getElementById('refined').textContent = data.refined_prompt;
                    document.getElementById('origScore').textContent = data.original_score + '/10';
                    document.getElementById('refScore').textContent = data.refined_score + '/10';
                    document.getElementById('result').classList.add('show');
                } catch (e) {
                    document.getElementById('error').textContent = e.message;
                    document.getElementById('error').classList.add('show');
                }
                document.querySelector('.refine-btn').disabled = false;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


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