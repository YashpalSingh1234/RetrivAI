from pathlib import Path

import chromadb
import numpy as np

class VectorStore:

    def __init__(self, persist_directory: str = "data/chroma_df", collection_name: str = "rag_documents"):
        Path(persist_directory).mkdir(
            parents=True,
            exist_ok=True
        )

        self.client = chromadb.PersistentClient(
            path=persist_directory
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space":"cosine"}
            )
        )

    def add_chunks(
            self,
            chunks: list[dict],
            batch_size: int = 100
    ) -> int:
        """
        Store embedded chunks in ChromaDB
        """

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        if not chunks:
            return 0

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]

            ids = [chunk["chunk_id"] for chunk in batch]

            documents = [
                chunk["text"] for chunk in batch
            ]


            embeddings = [
                chunk["embedding"] for chunk in batch
            ]


            metadatas = [chunk["metadata"] for chunk in batch]

            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )

        return len(chunks)


    def search(
            self,
            query_embedding: np.ndarray,
            top_k: int = 5,
            where: dict | None = None
    ) -> list[dict]:
        """
        Search similar chunks using query embedding.

        """

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        if self.collection.count() == 0:
            return []

        query_vector = np.asarray(
            query_embedding,
            dtype=np.float32
        )

        if query_vector.ndim != 1:
            raise ValueError("Query embedding must be a 1D vector")
        
        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        matches = []

        for chunk_id, text, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            matches.append({
                "chunk_id" : chunk_id,
                "text":text,
                "metadata" : metadata,

            })
        return matches

    def delete_document(self, document_id: str) -> None:
        """
        Delete all chunks belonging to a document
        """

        self.collection.delete(
            where={"document_id":document_id}
        )

    def count(self) -> int:
        return self.collection.count()