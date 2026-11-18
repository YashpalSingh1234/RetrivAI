import hashlib

from backend.app.ingestion.loaders import load_pdf
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.chunker import DocumentChunker
from backend.app.ingestion.embeddings import EmbeddingService
from backend.app.ingestion.vector_store import VectorStore

PDF_PATH = r"testdata\Big_Data_Basics_Complete_Study_Notes.pdf"

# 1. Load
document = load_pdf(PDF_PATH)

with open(PDF_PATH, "rb") as file:
    document["document_id"] = hashlib.file_digest(
        file, "sha256"
    ).hexdigest()

# 2. Clean
document = clean_document(document)

# 3. Chunk

chunker = DocumentChunker(
    chunk_size=1000,
    chunk_overlap=200
) 

chunks = chunker.chunk_document(document)

# 4. Embed
embedding_service = EmbeddingService()

embedded_chunks = embedding_service.embed_chunks(chunks)


# 5. Store
vector_store = VectorStore()

stored_count = vector_store.add_chunks(
    embedded_chunks
)

print("Processed Chunks:", stored_count)
print("Database Count:", vector_store.count())


# 6. Search
query = "What is machine learning?"

query_embedding = embedding_service.embed_query(query)

results = vector_store.search(
    query_embedding=query_embedding,
    top_k=5,
    where={"document_id": document["document_id"]}
)

for index, result in enumerate(results, start=1):
    print(f"\n--- Result {index} ---")
    print("Chunk ID:", result["chunk_id"])
    print("Distance:", result["distance"])
    print("Source:", result["metadata"]["page_number"])
    print("Page:", result["metadata"]["page_number"])
    print("Text:", result["text"][:300])