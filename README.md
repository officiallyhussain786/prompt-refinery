---
title: Prompt Refinery
emoji: 🧪
colorFrom: blue
colorTo: green
sdk: docker
sdk_version: "3.12"
app_file: backend/app/api/main.py
pinned: false
---

# Prompt Refinery

An AI-powered prompt refinement tool that transforms vague prompts into optimized prompts for better LLM outputs.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Svelte UI     │────▶│   FastAPI       │────▶│   Groq API      │
│   (Frontend)    │     │   (Port 7860)   │     │   (LLM)         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                │
                                                ▼
                                        ┌─────────────────┐
                                        │   HuggingFace   │
                                        │   Embeddings    │
                                        └─────────────────┘
```

## Tech Stack

- **Frontend**: SvelteKit + TypeScript
- **Backend API**: FastAPI (Python)
- **LLM**: Groq (Llama 3.3 70B)
- **Embeddings**: HuggingFace Inference API

## Features

- 4 refinement modes: Detailed, Concise, Structured, Multi-Step
- Prompt quality scoring (1-10)
- Improvement suggestions

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/refine` | Refine a prompt |
| GET | `/health` | Health check |
| GET | `/` | API info |

## Environment Variables

- `GROQ_API_KEY` - Groq API key
- `HF_TOKEN` - HuggingFace token