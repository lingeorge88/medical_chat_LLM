from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google import genai
from google.genai.types import EmbedContentConfig
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document
from sentence_transformers import CrossEncoder
from app.retrieval.interface import RetrievalProvider, SearchResult
from app import config
from typing import List
import hashlib

_genai_client = None
_reranker = None
_bm25_retriever = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_LOCATION,
        )
    return _genai_client


def _get_firestore_client():
    return firestore.Client(
        project=config.GOOGLE_CLOUD_PROJECT,
        database="(default)",
    )


def _get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
    return _reranker


def embed_texts(texts: List[str]) -> List[List[float]]:
    client = _get_genai_client()
    all_embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=batch,
            config=EmbedContentConfig(output_dimensionality=config.EMBEDDING_DIMENSION),
        )
        all_embeddings.extend([e.values for e in response.embeddings])
    return all_embeddings


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]


def similarity_search(query_embedding: List[float], k: int = 20) -> List[Document]:
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_CHUNKS_COLLECTION)

    results = collection.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=k,
    )

    docs = []
    for doc in results.stream():
        data = doc.to_dict()
        docs.append(
            Document(
                page_content=data["text"],
                metadata={
                    "source": data.get("source"),
                    "page": data.get("page"),
                },
            )
        )
    return docs


def load_all_documents() -> List[Document]:
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_CHUNKS_COLLECTION)
    docs = []
    for doc in collection.stream():
        data = doc.to_dict()
        docs.append(
            Document(
                page_content=data["text"],
                metadata={
                    "source": data.get("source"),
                    "page": data.get("page"),
                },
            )
        )
    return docs


def _get_bm25():
    global _bm25_retriever
    if _bm25_retriever is None:
        chunks = load_all_documents()
        _bm25_retriever = BM25Retriever.from_documents(chunks, k=20)
        print(f"BM25 index cached with {len(chunks)} chunks")
    return _bm25_retriever


def ingest_documents(chunks: List[Document]) -> int:
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_CHUNKS_COLLECTION)
    batch_size = 50
    ingested = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk.page_content for chunk in batch]
        vectors = embed_texts(texts)

        fb_batch = db.batch()
        for chunk, vector in zip(batch, vectors):
            content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
            doc_ref = collection.document(content_hash)
            fb_batch.set(doc_ref, {
                "text": chunk.page_content,
                "embedding": Vector(vector),
                "source": chunk.metadata.get("source"),
                "page": chunk.metadata.get("page"),
            })
        fb_batch.commit()

        ingested += len(batch)
        print(f"  [{ingested}/{len(chunks)}] chunks ingested")

    return ingested


def clear_collection():
    db = _get_firestore_client()
    collection = db.collection(config.FIRESTORE_CHUNKS_COLLECTION)
    deleted = 0
    for doc in collection.stream():
        doc.reference.delete()
        deleted += 1
    return deleted


class LegacyRetriever(RetrievalProvider):
    def search(self, query: str, analyzer: str | None = None, top_k: int = 5) -> List[SearchResult]:
        query_embedding = embed_query(query)
        dense_docs = similarity_search(query_embedding, k=20)

        try:
            bm25_docs = _get_bm25().invoke(query)
        except Exception:
            bm25_docs = []

        seen = set()
        merged = []
        for doc in dense_docs + bm25_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                merged.append(doc)

        if not merged:
            return []

        reranker = _get_reranker()
        pairs = [(query, doc.page_content) for doc in merged]
        scores = reranker.predict(pairs)
        scored = sorted(zip(scores, merged), key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored[:top_k]:
            results.append(SearchResult(
                text=doc.page_content,
                source=doc.metadata.get("source", ""),
                page=doc.metadata.get("page"),
                score=float(score),
            ))
        return results
