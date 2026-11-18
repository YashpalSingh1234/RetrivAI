import numpy as np

from backend.app.ingestion.embeddings import EmbeddingService

service = EmbeddingService()

sentences = [
    "Python is a programming language.",
    "Python is used for software develoment.",
    "The weather is very hot today."
]


vectors = service.embed_texts(sentences)

# Normalized embeddings: dot product = cosine similarity

similarity = np.dot(vectors, vectors.T)

print(np.round(similarity, 3))