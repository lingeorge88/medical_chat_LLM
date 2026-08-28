# Medical Lab Assistant

An agentic RAG chatbot for medical laboratory environments, powered by Google's Agent Development Kit (ADK) and Gemini 2.5 Flash. The agent intelligently routes queries between a local IFU knowledge base, web search, and clarification — providing accurate, sourced answers for laboratory technicians and medical professionals.

## Architecture

```
+---------------+         +--------------------------------------------+
|  React UI     |-------->|  FastAPI on Cloud Run                      |
|  (static)     |  SSE    |                                            |
+---------------+         |  +----------------------------------------+|
                          |  |  ADK LlmAgent (Gemini 2.5 Flash)       ||
                          |  |                                         ||
                          |  |  Tool 1: RAG Search                     ||
                          |  |    - Firestore vector search (2048d)    ||
                          |  |    - BM25 hybrid retrieval              ||
                          |  |    - BGE cross-encoder reranking        ||
                          |  |                                         ||
                          |  |  Tool 2: Web Search                     ||
                          |  |    - Tavily Search API                  ||
                          |  |                                         ||
                          |  |  Tool 3: Clarification                  ||
                          |  |    - Ask user for more info             ||
                          |  +----------------------------------------+|
                          |                                            |
                          |  Firestore: vectors + chat sessions        |
                          +--------------------------------------------+
```

### How It Works

1. **User sends a query** via the React frontend
2. **ADK agent decides** which tool to use based on the query
3. **RAG Search**: Embeds the query (Gemini Embedding 2048d), performs hybrid retrieval (dense + BM25), reranks with BGE cross-encoder, returns top 5 passages with source citations
4. **Web Search**: If the KB doesn't have the answer, the agent searches the web via Tavily
5. **Clarification**: If the query is too vague, the agent asks for more details
6. **Agent generates response** using retrieved context, citing sources

### RAG Pipeline

```
Query -> Gemini Embedding (2048d) -> Firestore vector search (top 20)
                                   + BM25 keyword search (top 20)
                                   -> Merge & deduplicate
                                   -> BGE Reranker v2-m3 (top 5)
                                   -> Agent generates response
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.5 Flash (Vertex AI) |
| Embedding | Gemini Embedding 001 (2048d) |
| Vector Store | Firestore (native vector search) |
| Reranker | BAAI/bge-reranker-v2-m3 |
| Agent Framework | Google ADK 2.8.0 |
| Web Search | Tavily Search API |
| Backend | FastAPI + Uvicorn |
| Frontend | React 19 + Material UI |
| Deployment | Google Cloud Run |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Google Cloud account with Vertex AI enabled
- Tavily API key (free tier: 1,000 searches/month)

### Setup

```bash
# Clone the repo
git clone git@github.com:lingeorge88/medical_chat_LLM.git
cd medical_chat_LLM

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up GCP authentication
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable aiplatform.googleapis.com firestore.googleapis.com
```

### Environment Variables

Create a `.env` file:

```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-west1
GOOGLE_GENAI_USE_VERTEXAI=True
TAVILY_API_KEY=your-tavily-api-key
```

### Document Ingestion

Place PDF files in the `data/` directory, then run:

```bash
# Create Firestore vector index (one-time)
gcloud firestore indexes composite create \
  --collection-group=medical_chunks \
  --field-config=vector-config='{"dimension":"2048","flat":{}}',field-path=embedding

# Ingest documents
python store_index.py
```

### Local Development

```bash
# Test with ADK Web UI (shows tool routing, reasoning traces)
adk web .
# Open http://localhost:8000

# Or run the FastAPI backend
uvicorn app:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
REACT_APP_API_URL=http://localhost:8080 npm start
```

### Deployment (Cloud Run)

```bash
# Build and deploy
gcloud run deploy medical-chatbot \
  --source . \
  --region us-west1 \
  --allow-unauthenticated \
  --set-secrets=TAVILY_API_KEY=TAVILY_API_KEY:latest \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-west1,GOOGLE_GENAI_USE_VERTEXAI=True \
  --memory=2Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3
```

## Project Structure

```
medical_chat_LLM/
├── agent.py              # ADK agent definition (3 tools, routing logic)
├── app.py                # FastAPI backend (endpoints, session management)
├── store_index.py        # Document ingestion pipeline
├── src/
│   ├── helper.py         # Embeddings, BM25, reranker utilities
│   └── vector_store.py   # Firestore vector search operations
├── data/                 # PDF documents (IFU manuals)
├── frontend/             # React frontend (Material UI)
├── Dockerfile            # Container build
├── Procfile              # Cloud Run process definition
└── requirements.txt      # Python dependencies
```

## Estimated Cost

| Service | Monthly Cost |
|---|---|
| Cloud Run | $0 (free tier) |
| Firestore | $0 (free tier) |
| Gemini 2.5 Flash | ~$1-5 |
| Vertex AI Embeddings | ~$0.01 |
| Tavily | $0 (free tier) |
| **Total** | **~$1-5/month** |

## Use Cases

- **Equipment Troubleshooting**: Quick answers to analyzer errors and maintenance procedures
- **Protocol Guidance**: Step-by-step instructions for complex laboratory procedures
- **Quality Control**: Information about QC profiles, calibration, and validation
- **Training Support**: On-demand reference for laboratory technicians
- **Research**: Web search fallback for FDA guidelines, best practices, and industry standards

## License

Apache License 2.0
