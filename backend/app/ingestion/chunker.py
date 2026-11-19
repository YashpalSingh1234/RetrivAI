from langchain_text_splitters import RecursiveCharacterTextSplitter

import hashlib
class DocumentChunker:

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        if chunk_size <= 0:
              raise ValueError("chunk_size must be positive")
        
        if not 0 <= chunk_overlap < chunk_size:
              raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
              
        self.splitter = RecursiveCharacterTextSplitter(
              chunk_size=chunk_size,
              chunk_overlap=chunk_overlap,
              separators=["\n\n", "\n", " ", ""],
              length_function=len,
        )

    


    def chunk_document(self, document: dict) -> list[dict]:

        chunks = []

        document_id = document.get("document_id")

        if not document_id:
            raise ValueError("document_id is required")

        for page in document["pages"]:

            page_number = page["page_number"]
            text = page["text"]

            if not text.strip():
                continue

            page_chunks = self.splitter.split_text(text)

            for chunk_index, chunk_text in enumerate(page_chunks):

                chunk_hash = hashlib.sha256(
                    chunk_text.encode("utf-8")
                ).hexdigest()[:16]

                chunk_id = (
                    f"{document_id}_p{page_number}"
                    f"_c{chunk_index}_{chunk_hash}"
                )

                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "document_id": document_id,
                        "source": document["filename"],
                        "page_number": page_number,
                        "chunk_index": chunk_index
                    }
                })

        return chunks


