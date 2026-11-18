from backend.app.ingestion.loaders import load_pdf
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.chunker import DocumentChunker
from backend.app.ingestion.embeddings import EmbeddingService


# Step 1: Load PDF
document = load_pdf(r"testdata\Big_Data_Basics_Complete_Study_Notes.pdf")

# Step 2: Clean
cleaned_document = clean_document(document)

# Step 3: Chunk

chunker = DocumentChunker(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = chunker.chunk_document(cleaned_document)

print("Total Chunks:", len(chunks))

# Step 4: Initialize embedding model

embedding_service = EmbeddingService(
    batch_size = 32
)

print("Device:", embedding_service.device)
print("Embedding Dimentsion:", embedding_service.embedding_dimension)


# Step 5: Generate embeddings

embedded_chunks = embedding_service.embed_chunks(chunks)

# Step 6: Verify output
if embedded_chunks:
    first_chunk = embedded_chunks[0]

    print("Chunk ID:", first_chunk["chunk_id"])
    print("Text:", first_chunk["text"][:150])
    print("Metadata:", first_chunk["metadata"])

    print(
        "Embedding length:",
        len(first_chunk["embedding"])
    )

    print(
        "First 10 values:",
        first_chunk["embedding"][:10]
    )

# Step 7: Test query embedding
query = "What is machine learning?"

query_vector = embedding_service.embed_query(query)

print("Query Vector Shape:", query_vector.shape)