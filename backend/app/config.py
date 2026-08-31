import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-west1")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
RETRIEVAL_PROVIDER = os.environ.get("RETRIEVAL_PROVIDER", "legacy")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 2048

DAILY_REQUEST_LIMIT = int(os.environ.get("DAILY_REQUEST_LIMIT", "10"))
BURST_REQUEST_LIMIT = int(os.environ.get("BURST_REQUEST_LIMIT", "3"))

FIRESTORE_CHUNKS_COLLECTION = "medical_chunks"
FIRESTORE_SESSIONS_COLLECTION = "adk_sessions"
FIRESTORE_RATE_LIMITS_COLLECTION = "rate_limits"
