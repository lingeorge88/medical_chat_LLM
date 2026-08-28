from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import CrossEncoder
from google import genai
from google.genai.types import EmbedContentConfig
from typing import List
from langchain.schema import Document
import os

EMBEDDING_DIMENSION = 2048

_reranker = None
_genai_client = None


def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-west1"),
        )
    return _genai_client


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
    return _reranker


def load_pdf_file(data):
    loader = DirectoryLoader(data, glob="*.pdf", loader_cls=PyPDFLoader)
    return loader.load()


def filter_to_minimal_docs(docs: List[Document]) -> List[Document]:
    return [
        Document(
            page_content=doc.page_content,
            metadata={
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
            },
        )
        for doc in docs
    ]


def text_split(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return text_splitter.split_documents(extracted_data)


def embed_texts(texts: List[str]) -> List[List[float]]:
    client = get_genai_client()
    all_embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
            config=EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSION),
        )
        all_embeddings.extend([e.values for e in response.embeddings])
    return all_embeddings


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]


def load_all_chunks_for_bm25() -> List[Document]:
    from src.vector_store import load_all_documents
    return load_all_documents()


def create_bm25_retriever(docs: List[Document], k: int = 20) -> BM25Retriever:
    return BM25Retriever.from_documents(docs, k=k)
