from backend.app.ingestion.loaders import load_pdf
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.chunker import DocumentChunker

# Step 1: Load PDF
document = load_pdf(r"testdata\Big_Data_Basics_Complete_Study_Notes.pdf")

# Step 2: Clean text
cleaned_document = clean_document(document)

# Step 3: Create chunks
chunker = DocumentChunker(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = chunker.chunk_document(cleaned_document)

# Step 4: Display results

print("Total Chunks:", len(chunks))

for chunk in chunks[:5]:
    print("\n -------------------------")
    print("Chunk ID:", chunk["chunk_id"])
    print("Metadata:", chunk["metadata"])
    print("Length:", len(chunk["text"]))
    print("Text", chunk["text"][:200])
