import numpy as np
import torch

from sentence_transformers import SentenceTransformer

class EmbeddingService:

     def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        batch_size: int = 32,
        device: str | None = None
    ):
        if batch_size <= 0:
              raise ValueError("batch_size must be positive")
        
        self.model_name = model_name
        self.batch_size = batch_size

        self.device = device or (
              "cuda" if torch.cuda.is_available() else "cpu"
        )

        # Load once when the service is initialized
        self.model = SentenceTransformer(
              model_name,
              device=self.device
        )

        self.embedding_dimension = (
              self.model.get_sentence_embedding_dimension()
        )



     
     def embed_texts(self, texts: list[str]) -> np.ndarray:
         
          """
          Generate normalized embeddings for a list of tests.
          """

          if not texts:
              return np.empty(
                   (0, self.embedding_dimension),
                   dtype=np.float32
              )

          if any(
               not isinstance(text, str) or not text.strip()
               for text in texts
          ):
               raise ValueError("All texts must be non-empty strings")

          embeddings = self.model.encode(
               texts,
               batch_size=self.batch_size,
               convert_to_numpy = True,
               normalize_embeddings = True,
               show_progress_bar = False
          )

          return np.asarray(embeddings, dtype=np.float32)

     def embed_query(self, query: str) -> np.ndarray:
          """
          Generate embedding for a user query.
          """
          if not isinstance(query, str) or not query.strip():
               raise ValueError("Query must be a non-empty string")

          return self.embed_texts([query])[0]

     def embed_chunks(self, chunks: list[dict]) -> list[dict]:

          """
          Generate embeddings while preserving chunk metadata.
          """

          if not chunks:
               return []

          texts = [chunk["text"] for chunk in chunks]

          embeddings = self.embed_texts(texts)

          results = []

          for chunk, vector in zip(chunks, embeddings):
               results.append({
                    **chunk, 
                    "embedding" : vector.tolist()
               })

          return results

     