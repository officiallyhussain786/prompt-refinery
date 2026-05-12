# Prompt Refinery

An AI-powered prompt refinement tool that transforms vague prompts into optimized prompts for better LLM outputs.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Svelte UI     │────▶│   FastAPI       │────▶│   gRPC Service  │
│   (Frontend)    │     │   (Port 8000)   │     │   (Port 50051)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │   Groq API      │
                                                │   (LLM)         │
                                                └─────────────────┘
```

## Tech Stack

- **Frontend**: SvelteKit + TypeScript
- **Backend API**: FastAPI (Python)
- **Internal Service**: gRPC
- **LLM**: Groq (Llama 3.3 70B)
- **RAG**: FAISS + Sentence Transformers

## Features

- 4 refinement modes: Detailed, Concise, Structured, Multi-Step
- Prompt quality scoring (1-10)
- Improvement suggestions
- Rate limiting & security headers
- CORS protected

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Set API key
export GROQ_API_KEY=your_key_here

# Run gRPC server (port 50051)
python -m app.services.grpc_server

# Run FastAPI (port 8000) - in another terminal
uvicorn app.api.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment

### Frontend (Vercel)
1. Push to GitHub
2. Connect to Vercel
3. Set `VITE_API_URL` to your backend URL

### Backend (Railway/Render)
1. Deploy the `backend` folder
2. Set `GROQ_API_KEY` environment variable
3. Railway auto-detects FastAPI

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/refine` | Refine a prompt |
| GET | `/health` | Health check |
| GET | `/` | API info |

## Security

- Rate limiting: 20 requests/minute per IP
- CORS: Configured origins only
- Input validation: Max 5000 characters
- Security headers: CSP, X-Frame-Options, etc.