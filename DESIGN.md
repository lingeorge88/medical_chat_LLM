# Medical Chat LLM — Redesign & GCP Migration

## Context

The current medical chatbot suffers from slow retrieval times and inaccurate responses due to:
- Weak embedding model (`all-MiniLM-L6-v2`, 384d, max 256 tokens)
- Poor chunking (500 chars, 20 char overlap — too small, loses context)
- No reranking (top-3 cosine similarity only)
- No hybrid search (misses exact medical terms/part numbers)
- Synchronous Flask backend (blocks on every LLM call)
- No conversation memory (stateless)
- GPT-5-mini as the LLM (limited reasoning)

This redesign migrates to GCP, replaces the LangChain retrieval chain with a Google ADK agent (3 tools: RAG, web search, clarification), and improves the RAG pipeline — targeting ~$1-5/month total cost.

## Final Architecture

```
+---------------+         +--------------------------------------------+
|  React UI     |-------->|  FastAPI on Cloud Run                      |
|  (static)     |  SSE    |                                            |
+---------------+         |  +----------------------------------------+|
                          |  |  ADK LlmAgent (Gemini 2.5 Flash)       ||
                          |  |                                         ||
                          |  |  Tool 1: RAG Search                     ||
                          |  |    - Firestore vector search            ||
                          |  |    - BM25 hybrid                        ||
                          |  |    - BGE reranker                       ||
                          |  |                                         ||
                          |  |  Tool 2: Web Search                     ||
                          |  |    - Tavily MCP (remote)                ||
                          |  |                                         ||
                          |  |  Tool 3: Clarification                  ||
                          |  |    - Ask user for more info             ||
                          |  +----------------------------------------+|
                          |                                            |
                          |  Firestore: vectors + chat sessions        |
                          +--------------------------------------------+
```

## Tech Stack

| Layer | Current | New |
|---|---|---|
| LLM | GPT-5-mini (OpenAI) | Gemini 2.5 Flash (Vertex AI) |
| Embedding | all-MiniLM-L6-v2 (384d) | text-embedding-005 (768d) |
| Vector Store | Pinecone | Firestore vector search ($0/mo) |
| Backend | Flask (sync) | FastAPI 0.141 (async + streaming) |
| Agent Framework | LangChain retrieval chain | Google ADK 2.8.0 |
| Web Search | None | Tavily MCP (1,000 free/mo) |
| Deployment | Render | Cloud Run (scales to zero) |
| Chat Memory | None (stateless) | Firestore sessions |

## Estimated Monthly Cost

| Service | Cost |
|---|---|
| Cloud Run | $0 (free tier) |
| Firestore (vectors + sessions) | $0 (free tier) |
| Vertex AI (embeddings) | ~$0.01 |
| Gemini 2.5 Flash | ~$1-5 (depending on usage) |
| Tavily | $0 (free tier) |
| **Total** | **~$1-5/month** |

## Accounts & Keys Needed

| Item | Where | Cost |
|---|---|---|
| GCP free trial | cloud.google.com/free | $0 ($300 credit) |
| Gemini API key | aistudio.google.com/apikey | $0 (local dev) |
| Tavily API key | tavily.com | $0 (1,000 searches/mo) |
| gcloud CLI | `brew install google-cloud-sdk` | $0 |

---

## Phase 1: FastAPI Migration

**Goal:** Replace Flask with FastAPI for async support and SSE streaming. No changes to RAG pipeline or models yet — backend-only swap.

### Changes

**`app.py`** — Full rewrite:
- Replace Flask with FastAPI 0.141.1
- Replace `flask-cors` with `CORSMiddleware`
- Replace `send_from_directory` with `StaticFiles(directory="frontend/build", html=True)`
- Convert `/get` endpoint to `async def` with Pydantic request/response models
- Add SSE streaming endpoint (`/chat/stream`) using `StreamingResponse`
- Use `asynccontextmanager` lifespan for startup initialization

**`requirements.txt`** — Swap dependencies:
- Remove: `flask`, `flask-cors`, `gunicorn`
- Add: `fastapi==0.141.1`, `uvicorn[standard]`

**`Dockerfile`** — Update CMD:
- `CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]`

**`frontend/src/components/ChatContainer.js`** — Update API call:
- Change `Content-Type` from `x-www-form-urlencoded` to `application/json`
- Send `{ "msg": userMessage.text }` as JSON body

### Local Verification

```bash
# Install new deps
pip install fastapi uvicorn[standard]

# Start backend (still uses OpenAI + Pinecone)
uvicorn app:app --reload --port 8080

# Test API
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is the calibration procedure?"}'

# Test streaming
curl -N -X POST http://localhost:8080/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is the calibration procedure?"}'

# Test frontend
cd frontend && REACT_APP_API_URL=http://localhost:8080 npm start

# Verify Swagger docs at http://localhost:8080/docs
```

---

## Phase 2: RAG Pipeline Improvements

**Goal:** Fix chunking, upgrade embeddings, add hybrid search + reranking. Still using Pinecone and OpenAI — improving retrieval quality before swapping infrastructure.

### Changes

**`src/helper.py`** — Overhaul:
- `RecursiveCharacterTextSplitter`: `chunk_size=1500`, `chunk_overlap=200`, separators `["\n\n", "\n", ". ", " ", ""]`
- Replace HuggingFace embeddings with Vertex AI `text-embedding-005` (768d)
- Add `rerank_documents()` using `CrossEncoder("BAAI/bge-reranker-v2-m3")`
- Add BM25 retriever for sparse search
- Keep page number in metadata for citations

**`store_index.py`** — Update Pinecone index dimension 384 -> 768

**`app.py`** — Update retrieval:
- Retrieve top-20 candidates, rerank to top-5
- `EnsembleRetriever` with BM25 (0.4) + dense (0.6)

**`requirements.txt`** — Add: `google-genai`, `rank-bm25`

### Local Verification

```bash
# Delete old Pinecone index and re-ingest
python store_index.py

# Test retrieval quality
uvicorn app:app --reload --port 8080
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What are the reagent storage requirements for the 5812?"}'

# Test BM25 keyword matching
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is part number 123-456?"}'
```

---

## Phase 3: Firestore Vector Store (Replace Pinecone)

**Goal:** Move vectors to Firestore. Free tier covers ~1,600 vectors. Eliminates Pinecone cost.

### Changes

**`store_index.py`** — Rewrite for Firestore:
- Collection `medical_chunks`: `{ text, embedding (768d), metadata, content_hash }`
- Composite vector index for cosine similarity

**`src/helper.py`** — Firestore retrieval:
- `firestore_similarity_search()` using `collection.find_nearest()`
- Remove Pinecone code

**`requirements.txt`** — Remove `langchain-pinecone`, add `google-cloud-firestore`

### Local Verification

```bash
# Use Firestore emulator
gcloud emulators firestore start --host-port=localhost:8081
export FIRESTORE_EMULATOR_HOST=localhost:8081

# Ingest against emulator
python store_index.py

# Test queries
FIRESTORE_EMULATOR_HOST=localhost:8081 uvicorn app:app --reload --port 8080
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is the calibration procedure?"}'

# Verify Pinecone fully removed
grep -r "pinecone" --include="*.py" .
```

---

## Phase 4: ADK Agent with 3 Tools

**Goal:** Replace LangChain chain with ADK `LlmAgent`. Swap OpenAI -> Gemini 2.5 Flash. This is the biggest architectural change.

### Changes

**New `agent.py`**:
```python
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

agent = LlmAgent(
    model="gemini-2.5-flash",
    name="medical_assistant",
    instruction="...",
    tools=[search_knowledge_base, tavily_toolset, ask_clarification]
)
```

**`app.py`** — ADK Runner integration:
- `Runner(agent=agent, app_name="medical_chat", session_service=session_service)`
- Endpoints call `runner.run_async()` instead of `rag_chain.invoke()`

**`requirements.txt`** — Remove LangChain/OpenAI, add `google-adk==2.8.0`

### Local Verification — ADK CLI & Web UI

```bash
# Test in ADK CLI (interactive terminal chat)
adk run agent.py

# Test in ADK Web UI (browser dev UI with tool call visibility)
adk web agent.py
# Opens http://localhost:8000 — shows tool calls, reasoning traces

# Test FastAPI integration
uvicorn app:app --reload --port 8080
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What reagents does the AU680 need?"}'

# Test web search
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "Latest FDA guidelines for clinical chemistry analyzers?"}'

# Test clarification
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "analyzer"}'
```

---

## Phase 5: Conversation Memory + Streaming UI

**Goal:** Add chat history for follow-ups. Stream tokens to frontend for faster perceived response.

### Changes

**`app.py`** — Session management via ADK `SessionService` + Firestore backend

**`ChatContainer.js`** — Streaming:
- Generate `session_id` in `localStorage`
- Replace `fetch` with `ReadableStream` reader for SSE
- Render tokens as they arrive

### Local Verification

```bash
# Test memory (same session_id)
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is the calibration procedure?", "session_id": "test-123"}'

curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "How often should I do that?", "session_id": "test-123"}'

# Test streaming
curl -N -X POST http://localhost:8080/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"msg": "Explain the maintenance schedule", "session_id": "test-456"}'

# Test in ADK Web UI (shows session state)
adk web agent.py
```

---

## Phase 6: Cloud Run Deployment

**Goal:** Deploy to Cloud Run. Serverless, scales to zero, ~$0-5/month.

### Changes

**`Dockerfile`** — Production: `python:3.12-slim`, non-root user, uvicorn

**New `.dockerignore`**: Ignore `data/`, `research/`, `node_modules/`, `.env`, `.git`

### Deployment

```bash
gcloud run deploy medical-chatbot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=your-project-id \
  --memory=1Gi --cpu=1 \
  --min-instances=0 --max-instances=3
```

### Local Verification (Pre-Deploy)

```bash
docker build -t medical-chatbot .
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=your-key \
  -e TAVILY_API_KEY=your-key \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  medical-chatbot

curl http://localhost:8080/
curl -X POST http://localhost:8080/get \
  -H "Content-Type: application/json" \
  -d '{"msg": "What is the calibration procedure?"}'
```

---

## Files Modified Per Phase

| Phase | New Files | Modified Files |
|---|---|---|
| 1 | — | `app.py`, `requirements.txt`, `Dockerfile`, `ChatContainer.js` |
| 2 | — | `src/helper.py`, `store_index.py`, `app.py`, `requirements.txt` |
| 3 | — | `store_index.py`, `src/helper.py`, `app.py`, `requirements.txt`, `.env` |
| 4 | `agent.py` | `app.py`, `src/prompt.py`, `requirements.txt`, `.env` |
| 5 | — | `app.py`, `ChatContainer.js`, `ChatMessage.js` |
| 6 | `.dockerignore`, `cloudbuild.yaml` | `Dockerfile`, `Procfile` |
