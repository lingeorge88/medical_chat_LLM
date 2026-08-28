from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from typing import List
from langchain.schema import Document
from src.helper import embed_texts
import hashlib
import os

COLLECTION = "medical_chunks"


def get_firestore_client():
    return firestore.Client(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        database="(default)",
    )


def ingest_documents(chunks: List[Document]) -> int:
    db = get_firestore_client()
    collection = db.collection(COLLECTION)
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


def similarity_search(query_embedding: List[float], k: int = 20) -> List[Document]:
    db = get_firestore_client()
    collection = db.collection(COLLECTION)

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
                metadata={"source": data.get("source"), "page": data.get("page")},
            )
        )
    return docs


def load_all_documents() -> List[Document]:
    db = get_firestore_client()
    collection = db.collection(COLLECTION)
    docs = []
    for doc in collection.stream():
        data = doc.to_dict()
        docs.append(
            Document(
                page_content=data["text"],
                metadata={"source": data.get("source"), "page": data.get("page")},
            )
        )
    return docs


def clear_collection():
    db = get_firestore_client()
    collection = db.collection(COLLECTION)
    deleted = 0
    for doc in collection.stream():
        doc.reference.delete()
        deleted += 1
    return deleted
