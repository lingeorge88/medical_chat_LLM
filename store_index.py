from dotenv import load_dotenv
from src.helper import load_pdf_file, filter_to_minimal_docs, text_split
from src.vector_store import ingest_documents, clear_collection

load_dotenv()

extracted_data = load_pdf_file(data="data/")
filtered_data = filter_to_minimal_docs(extracted_data)
text_chunks = text_split(filtered_data)

print(f"Loaded {len(extracted_data)} pages, split into {len(text_chunks)} chunks")

for chunk in text_chunks[:3]:
    print(f"  Chunk ({len(chunk.page_content)} chars): {chunk.page_content[:80]}...")
    print(f"  Metadata: {chunk.metadata}")

print("Clearing existing documents...")
deleted = clear_collection()
print(f"  Deleted {deleted} existing documents")

print(f"Ingesting {len(text_chunks)} chunks into Firestore...")
ingested = ingest_documents(text_chunks)
print(f"Done. {ingested} chunks ingested.")
