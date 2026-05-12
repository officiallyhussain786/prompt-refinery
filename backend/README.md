# Prompt Refinery API

A FastAPI + gRPC service that refines user prompts to get better results from LLMs.

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key in .env
echo "GROQ_API_KEY=your_key_here" > .env
```

### 2. Generate Protobuf Files

```bash
source venv/bin/activate
python -m grpc_tools.protoc -I./protos --python_out=./app/services --grpc_python_out=./app/services ./protos/refine.proto
```

### 3. Run the Services

**Terminal 1 - gRPC Server:**
```bash
source venv/bin/activate
cd /home/hussain/prompt-refinery/backend
export PYTHONPATH=/home/hussain/prompt-refinery/backend
export GROQ_API_KEY=your_key_here
python -m app.services.grpc_server
```

**Terminal 2 - FastAPI:**
```bash
source venv/bin/activate
cd /home/hussain/prompt-refinery/backend
export PYTHONPATH=/home/hussain/prompt-refinery/backend
export GROQ_API_KEY=your_key_here
python -m app.api.main
```

### 4. Test the API

```bash
curl -X POST http://localhost:8000/refine \
  -H "Content-Type: application/json" \
  -d '{"prompt": "write code", "mode": "detailed"}'
```

Or open http://localhost:8000/docs for Swagger UI.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── main.py          # FastAPI REST API (port 8000)
│   ├── rag/
│   │   └── retriever.py     # FAISS vector search for patterns
│   └── services/
│       ├── refiner.py       # Groq API integration
│       ├── grpc_server.py   # gRPC server (port 50051)
│       ├── refine_pb2.py    # Generated protobuf
│       └── refine_pb2_grpc.py
├── protos/
│   └── refine.proto         # gRPC service definition
├── .env                     # Environment variables
└── requirements.txt
```

## Architecture

```
User → FastAPI (port 8000) → gRPC (port 50051) → Groq API
                      ↓
                 FAISS Vector Search
                 (RAG patterns)
```

### How It Works

1. **HTTP Request** → POST `/refine` to FastAPI
2. **gRPC Call** → FastAPI communicates with gRPC server
3. **RAG Retrieval** → Query FAISS vector index for relevant patterns
4. **LLM Refinement** → Send prompt + patterns to Groq (Llama 3.3)
5. **Response** → Return refined prompt with scores

## API Reference

### POST /refine

**Request:**
```json
{
  "prompt": "your original prompt",
  "mode": "detailed"  // detailed, concise, structured, multi_step
}
```

**Response:**
```json
{
  "refined_prompt": "improved version of your prompt",
  "intent": "what you want to accomplish",
  "original_score": 5,
  "refined_score": 9,
  "improvements": ["added context", "specified format"]
}
```

### GET /health

Returns service health status.

## Modes

| Mode | Use Case |
|------|----------|
| `detailed` | Add context, specify format, examples |
| `concise` | Short, direct prompts |
| `structured` | Bullet points, step-by-step |
| `multi_step` | Complex tasks with phases |

## Key Files Explained

### proto/refine.proto
Defines the gRPC service contract - what methods are available and their data types.

### app/services/refiner.py
The Groq API client. Takes the original prompt and patterns, sends to Llama 3.3, parses the JSON response.

### app/rag/retriever.py
The FAISS-based RAG system. Embeds prompt engineering patterns, searches by semantic similarity.

### app/api/main.py
FastAPI endpoints. Validates requests, calls gRPC, returns formatted responses.

### app/services/grpc_server.py
The gRPC service implementation. Orchestrates RAG retrieval + LLM refinement.

## Troubleshooting

**"GROQ_API_KEY environment variable is not set"**
→ Set your Groq API key in `.env`

**Import errors**
→ Run `export PYTHONPATH=/home/hussain/prompt-refinery/backend`

**Protobuf errors**
→ Regenerate with: `python -m grpc_tools.protoc -I./protos --python_out=./app/services --grpc_python_out=./app/services ./protos/refine.proto`