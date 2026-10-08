# RetrivAI — Project Specification

**Document Version:** 1.0
**Status:** Development Blueprint
**Project Type:** Portfolio / Production-style AI Application
**Primary Goal:** Demonstrate practical expertise in RAG, LLM applications, retrieval, reranking, evaluation, FastAPI, and deployment.

---

## 1. Project Overview

### Product Identity

**RetrivAI** represents the core idea of the system:

> **Retrieve relevant information → provide context to the AI → generate a grounded answer.**

The product is intentionally positioned as a technical AI proof-of-work rather than a generic chatbot.

### 1.1 Project Name

**RetrivAI**

### 1.2 One-line Description

RetrivAI is a document-grounded AI assistant that allows users to upload documents and ask questions using Retrieval-Augmented Generation (RAG), semantic search, reranking, grounded generation, and source citations.

### 1.3 Problem Statement

Traditional document search often requires users to manually scan large documents to find relevant information. Generic LLM chatbots can answer questions fluently but may hallucinate information when they do not have access to the user's documents.

This project combines document retrieval with LLM generation so that answers are based on relevant document content rather than relying only on the model's general knowledge.

### 1.4 Objective

Build an end-to-end RAG application that can:

- Accept user documents.
- Extract and process document text.
- Split documents into meaningful chunks.
- Generate vector embeddings.
- Store embeddings in a vector database.
- Retrieve semantically relevant information.
- Rerank retrieved candidates.
- Generate grounded answers with an LLM.
- Display supporting sources/citations.
- Evaluate retrieval and answer quality.

---

# 2. Product Scope

## 2.1 Core User Flow

```text
User
  ↓
Upload Documents
  ↓
Document Processing
  ↓
Text Extraction
  ↓
Cleaning
  ↓
Chunking
  ↓
Embedding Generation
  ↓
Vector Database
  ↓
User Asks Question
  ↓
Query Embedding
  ↓
Semantic Retrieval
  ↓
Top-K Candidates
  ↓
Reranking
  ↓
Relevant Context
  ↓
LLM
  ↓
Grounded Answer + Citations
```

## 2.2 Core Features

### Document Management

- PDF upload
- DOCX upload
- TXT upload
- File validation
- Document listing
- Document deletion
- Document metadata
- Processing status

### RAG

- Text extraction
- Text cleaning
- Chunking
- Embedding generation
- Vector storage
- Semantic similarity search
- Top-K retrieval
- Reranking
- Context construction
- Grounded generation

### Chat

- Question answering
- Conversation history
- Source citations
- Source preview
- "Insufficient information" response when context is inadequate

### Evaluation

- Retrieval evaluation
- Answer relevance
- Context relevance
- Faithfulness / groundedness
- Citation correctness

---

# 3. Advanced Features

These should be implemented after the core RAG pipeline is stable.

- Query rewriting
- Metadata filtering
- Configurable Top-K
- Configurable chunk size
- Retrieval score display
- Reranking score display
- Source highlighting
- Multi-document search
- Evaluation dashboard
- Response latency tracking
- Retrieval debugging view

The advanced features must not delay the first working version.

---

# 4. Target Users

The application should demonstrate a realistic business use case.

Potential users:

- Students
- Researchers
- Employees
- Teams working with internal documentation
- Companies with knowledge bases
- Customer-support teams
- Legal/financial/document-heavy workflows

The demo should remain domain-neutral so that the same architecture can be adapted to different client requirements.

---

# 5. High-Level Architecture

```text
                         ┌───────────────────┐
                         │       USER        │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │    Web Frontend   │
                         └─────────┬─────────┘
                                   │
                         ┌─────────┴─────────┐
                         │                   │
                         ▼                   ▼
                  Document Upload        User Query
                         │                   │
                         ▼                   ▼
                  File Validation      Query Processing
                         │                   │
                         ▼                   ▼
                  Document Loader      Query Embedding
                         │                   │
                         ▼                   │
                    Text Cleaning            │
                         │                   │
                         ▼                   │
                      Chunking               │
                         │                   │
                         ▼                   │
                    Embeddings               │
                         │                   │
                         ▼                   │
                  Vector Database ◄──────────┘
                         │
                         ▼
                  Semantic Retrieval
                         │
                         ▼
                       Top-K
                         │
                         ▼
                     Reranking
                         │
                         ▼
                  Relevant Context
                         │
                         ▼
                Prompt + Context
                         │
                         ▼
                         LLM
                         │
                         ▼
              Grounded Answer + Sources
                         │
                         ▼
                         USER
```

### Important Architecture Principle

The architecture above is a **conceptual application architecture**. Exact cloud services or infrastructure should only be documented after they are actually implemented.

---

# 6. Document Ingestion Pipeline

## 6.1 Pipeline

```text
File Upload
    ↓
Validation
    ↓
Document Loader
    ↓
Text Extraction
    ↓
Text Cleaning
    ↓
Chunking
    ↓
Metadata Creation
    ↓
Embedding Generation
    ↓
Vector Storage
```

## 6.2 File Validation

Validate:

- Supported extension
- MIME type
- File size
- Empty/corrupt files

The backend must reject unsupported or unsafe files before processing.

## 6.3 Text Extraction

The system extracts readable text from uploaded documents.

The implementation should preserve useful metadata such as:

- Filename
- Page number
- Document ID
- Chunk index

## 6.4 Text Cleaning

Potential operations:

- Remove unnecessary whitespace
- Normalize line breaks
- Remove extraction artifacts
- Preserve meaningful headings and structure where possible

Cleaning should not destroy information needed for retrieval.

---

# 7. Chunking Strategy

Chunking is one of the most important parts of the RAG pipeline.

## Initial Strategy

Start with a fixed-size or recursive text splitter with overlap.

Conceptually:

```text
Document
   ↓
Chunk 1
Chunk 2
Chunk 3
Chunk 4
...
```

Each chunk should contain enough context to answer questions while remaining small enough for effective retrieval.

## Chunk Metadata

Each chunk should retain:

```text
document_id
chunk_id
source_file
page_number
chunk_index
content
```

## Chunking Experiments

The project should allow later comparison of:

- Smaller chunks
- Larger chunks
- Different overlap sizes
- Structure-aware splitting

The final configuration should be chosen based on evaluation rather than guesswork.

---

# 8. Embeddings

## Purpose

Embeddings convert text into numerical vectors representing semantic meaning.

```text
Text
  ↓
Embedding Model
  ↓
Vector
```

Both document chunks and user queries must be embedded into the same vector space.

## Initial Embedding Approach

Use a sentence-transformers embedding model.

A candidate model is:

`sentence-transformers/all-mpnet-base-v2`

The exact model may be changed after evaluation.

---

# 9. Vector Database

## Initial Choice

**Chroma**

Purpose:

- Store chunk embeddings
- Store metadata
- Perform similarity search
- Retrieve candidate chunks

Conceptual structure:

```text
Vector Database
│
├── Document A
│   ├── Chunk 1
│   ├── Chunk 2
│   └── Chunk 3
│
├── Document B
│   ├── Chunk 1
│   └── Chunk 2
│
└── Metadata
```

The vector database choice should remain replaceable so the application can later support systems such as PostgreSQL/pgvector or managed vector databases.

---

# 10. Retrieval Pipeline

## 10.1 Basic Retrieval

```text
User Query
    ↓
Query Embedding
    ↓
Vector Similarity Search
    ↓
Top-K Chunks
```

## 10.2 Similarity

Cosine similarity can be used to compare query and document vectors.

Conceptually:

```text
similarity(query, chunk)
```

Higher semantic similarity means the chunk is more likely to be relevant.

## 10.3 Top-K

The retriever initially returns several candidates rather than immediately passing the entire document collection to the LLM.

Example:

```text
1000 chunks
    ↓
Retrieve Top 10
    ↓
Rerank
    ↓
Select Top 3–5
```

The exact K should be determined experimentally.

---

# 11. Reranking

Semantic retrieval provides candidate documents, but the first retrieved result is not always the best final context.

Reranking adds a second relevance stage.

```text
Vector Search
     ↓
Top-K Candidates
     ↓
Cross-Encoder / Reranker
     ↓
Ranked Candidates
     ↓
Top-N Context
```

## Why Reranking?

It can improve:

- Relevance
- Context quality
- Precision of retrieved information
- Final answer quality

A cross-encoder model can be evaluated as the initial reranking approach.

---

# 12. Context Construction

After reranking:

```text
Ranked Chunks
    ↓
Context Selection
    ↓
Context Formatting
    ↓
Prompt
```

The context should contain source metadata so that citations can be generated.

Example:

```text
[Source: employee_handbook.pdf, Page 12]

Relevant content...
```

---

# 13. Grounded Generation

The LLM should receive:

1. User question
2. Retrieved context
3. System instructions

Conceptual prompt:

```text
You are a document-based assistant.

Answer the user's question using only the provided context.

Rules:
- Do not invent facts.
- Do not use unsupported information.
- If the context does not contain enough information, say that the answer
  cannot be determined from the provided documents.
- Keep the answer relevant and concise.
- Cite the sources used for the answer.
```

The final prompt will be refined during implementation and evaluation.

---

# 14. Hallucination Reduction

The application should reduce hallucination through multiple layers:

```text
Relevant Retrieval
      ↓
Reranking
      ↓
Limited Context
      ↓
Grounded Prompt
      ↓
Source Citations
      ↓
Answer Evaluation
```

The system should not claim that hallucinations are completely eliminated.

---

# 15. Citation System

Every answer should attempt to show where the information came from.

Example:

```text
Answer:
The company provides 20 annual leave days.

Sources:
1. employee_handbook.pdf — Page 12
2. leave_policy.pdf — Page 4
```

Citation metadata should originate from the retrieved chunks, not be fabricated by the model.

---

# 16. Handling Insufficient Context

If retrieved context is not relevant enough, the system should avoid confidently generating an unsupported answer.

Expected behavior:

```text
Query
 ↓
Retrieval
 ↓
Relevance Check
 ↓
Insufficient Context
 ↓
"I couldn't find enough information in the uploaded documents
to answer this question."
```

This is an important part of trustworthy RAG behavior.

---

# 17. Chat Architecture

```text
User
 ↓
Chat UI
 ↓
POST /query
 ↓
Query Processing
 ↓
Retriever
 ↓
Reranker
 ↓
Context Builder
 ↓
LLM
 ↓
Answer + Citations
 ↓
Chat UI
```

Conversation history should be separated from document retrieval logic so the system remains maintainable.

---

# 18. API Specification

The backend will use FastAPI.

## Health

```http
GET /health
```

Purpose:

Verify that the backend is running.

## Upload Document

```http
POST /documents/upload
```

Purpose:

Upload and process a document.

## List Documents

```http
GET /documents
```

Purpose:

Return uploaded documents and their processing status.

## Delete Document

```http
DELETE /documents/{document_id}
```

Purpose:

Delete a document and its associated vector records.

## Query

```http
POST /query
```

Request concept:

```json
{
  "question": "What is the leave policy?",
  "top_k": 5
}
```

Response concept:

```json
{
  "answer": "...",
  "sources": [
    {
      "document": "employee_handbook.pdf",
      "page": 12
    }
  ]
}
```

## Chat

```http
POST /chat
```

Purpose:

Support conversational interaction with document context.

---

# 19. Backend Folder Structure

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── documents.py
│   │   ├── query.py
│   │   └── health.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── ingestion/
│   │   ├── loaders.py
│   │   ├── cleaner.py
│   │   ├── chunker.py
│   │   └── embeddings.py
│   │
│   ├── retrieval/
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   └── context.py
│   │
│   ├── generation/
│   │   ├── prompts.py
│   │   └── llm.py
│   │
│   ├── evaluation/
│   │   ├── retrieval.py
│   │   └── generation.py
│   │
│   └── models/
│       └── schemas.py
│
├── tests/
├── requirements.txt
└── .env.example
```

---

# 20. Frontend Structure

```text
frontend/
│
├── app/
│   ├── page.tsx
│   ├── chat/
│   ├── documents/
│   └── architecture/
│
├── components/
│   ├── Chat/
│   ├── DocumentUpload/
│   ├── DocumentList/
│   ├── SourceCitation/
│   └── Architecture/
│
├── lib/
│   ├── api.ts
│   └── types.ts
│
└── public/
```

---

# 21. Database / Storage Model

A relational database may be used for application metadata.

Conceptual entities:

```text
User
 │
 ├── Documents
 │      │
 │      └── Chunks
 │
 └── Conversations
        │
        └── Messages
```

Document:

```text
id
user_id
filename
file_type
status
created_at
```

Chunk:

```text
id
document_id
chunk_index
content
page_number
metadata
```

Conversation:

```text
id
user_id
created_at
```

Message:

```text
id
conversation_id
role
content
created_at
```

Vector storage remains separate from relational application metadata if Chroma is used.

---

# 22. Technology Stack

| Layer               | Initial Technology         |
| ------------------- | -------------------------- |
| Frontend            | Next.js                    |
| UI                  | Tailwind CSS               |
| Language            | TypeScript                 |
| Backend             | FastAPI                    |
| Backend Language    | Python                     |
| Embeddings          | Sentence Transformers      |
| Vector DB           | Chroma                     |
| Retrieval           | Semantic Similarity Search |
| Reranking           | Cross-Encoder              |
| LLM                 | API-based LLM              |
| Version Control     | GitHub                     |
| Frontend Deployment | Vercel                     |
| Backend Deployment  | Render / Railway           |

These are initial decisions and can be changed if testing demonstrates a better choice.

---

# 23. Security Requirements

The application must:

- Validate uploaded files.
- Restrict supported file types.
- Enforce file-size limits.
- Keep API keys server-side.
- Use environment variables for secrets.
- Validate API inputs.
- Prevent users from accessing other users' documents.
- Consider prompt-injection attacks from document content.
- Apply reasonable rate limits.
- Avoid logging sensitive document content unnecessarily.

---

# 24. Testing Strategy

## Unit Tests

Test:

- Text cleaning
- Chunking
- Metadata generation
- Retrieval
- Reranking
- Prompt construction
- API validation

## Integration Tests

Test:

```text
Upload
 ↓
Process
 ↓
Index
 ↓
Query
 ↓
Retrieve
 ↓
Generate
 ↓
Return citations
```

## Frontend Tests

Verify:

- Upload UI
- Processing state
- Chat
- Source display
- Error handling
- Responsive layout

---

# 25. RAG Evaluation

Evaluation is a core portfolio feature, not an optional afterthought.

## Retrieval Metrics

### Precision@K

Measures how many retrieved chunks are relevant.

### Recall@K

Measures how many relevant chunks were successfully retrieved.

### MRR

Measures how highly the first relevant result appears.

---

# 26. Generation Evaluation

Evaluate:

### Faithfulness

Does the answer stay supported by the retrieved context?

### Answer Relevance

Does the response actually answer the question?

### Context Relevance

Is the retrieved context relevant to the question?

### Citation Accuracy

Do citations actually support the claims made?

---

# 27. Evaluation Dataset

Create a small manually verified dataset.

Example:

```text
Question
Expected Answer
Relevant Document
Relevant Page
Relevant Chunk
```

Example:

```text
Question:
How many annual leave days are provided?

Expected:
20 days.

Relevant Source:
employee_handbook.pdf

Relevant Page:
12
```

This dataset will be used to compare retrieval configurations and prompt changes.

---

# 28. Experiments

The project should document meaningful experiments.

Possible experiments:

### Experiment 1 — Chunk Size

Compare:

```text
Small chunks
vs
Medium chunks
vs
Large chunks
```

### Experiment 2 — Top-K

Compare:

```text
Top-3
Top-5
Top-10
```

### Experiment 3 — Reranking

Compare:

```text
Vector Search Only
vs
Vector Search + Reranking
```

### Experiment 4 — Prompting

Compare:

```text
Basic Prompt
vs
Grounded Prompt + Citation Instructions
```

The final configuration should be selected based on observed evaluation results.

---

# 29. Performance Considerations

Track:

- Document processing time
- Embedding generation time
- Retrieval latency
- Reranking latency
- LLM latency
- Total response time

Conceptual:

```text
Total Latency =
Retrieval
+ Reranking
+ LLM Generation
```

The application should avoid unnecessarily sending large contexts to the LLM.

---

# 30. Error Handling

The application should handle:

- Unsupported files
- Corrupt files
- Empty documents
- Extraction failures
- Embedding failures
- Vector DB failures
- LLM/API failures
- Timeouts
- Invalid queries
- Missing context

The frontend should show useful human-readable errors.

---

# 31. Observability

At minimum, log:

- Request ID
- Processing status
- Retrieval latency
- Number of retrieved chunks
- Reranking latency
- LLM latency
- Error type

Do not log full sensitive document contents by default.

---

# 32. Deployment Architecture

Initial deployment concept:

```text
                 ┌──────────────┐
                 │    Vercel    │
                 │   Frontend   │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   FastAPI    │
                 │   Backend    │
                 └──────┬───────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
        Vector DB     LLM API   App DB
```

Exact hosting services should be finalized during deployment.

---

# 33. GitHub Repository

Repository should contain:

```text
README.md
LICENSE
.env.example
frontend/
backend/
docs/
tests/
```

README should include:

- Project overview
- Features
- Architecture
- Tech stack
- Setup
- Environment variables
- API
- RAG pipeline
- Evaluation
- Screenshots
- Demo
- Deployment
- Future improvements

---

# 34. Portfolio Presentation

The final portfolio project should demonstrate:

### Product

- Working document chatbot
- Clean UI
- Source citations

### Engineering

- FastAPI backend
- RAG pipeline
- Embeddings
- Vector DB
- Reranking
- LLM integration

### AI Quality

- Grounded responses
- Evaluation
- Retrieval metrics
- Citation validation

### Deployment

- Live demo
- Public GitHub repository
- Production deployment

---

# 35. Architecture Visualization

The portfolio should include an interactive architecture diagram.

Recommended flow:

```text
User
 ↓
Web Application
 ↓
Document / Query Router
 ├───────────────┐
 │               │
 ▼               ▼
Ingestion      Query
 │               │
 ▼               ▼
Chunking      Embedding
 │               │
 ▼               ▼
Embeddings → Vector DB
                 │
                 ▼
             Retrieval
                 │
                 ▼
              Reranking
                 │
                 ▼
               Context
                 │
                 ▼
                LLM
                 │
                 ▼
          Answer + Citations
```

The architecture visualization should be interactive and explain the actual implemented pipeline.

---

# 36. Demo Video

Create a short 30–60 second demo.

Suggested sequence:

```text
1. Open application
2. Upload document
3. Show processing
4. Ask question
5. Show answer
6. Show source citation
7. Show another question
8. Show architecture
9. Show GitHub / live deployment
```

Do not spend the entire video explaining theory.

---

# 37. Definition of Done

The project is considered complete only when:

- [ ] Documents can be uploaded.
- [ ] Supported files are processed.
- [ ] Text is extracted.
- [ ] Documents are chunked.
- [ ] Embeddings are generated.
- [ ] Embeddings are stored.
- [ ] User queries work.
- [ ] Semantic retrieval works.
- [ ] Reranking works.
- [ ] LLM generates grounded answers.
- [ ] Citations are displayed.
- [ ] Insufficient context is handled.
- [ ] Chat works.
- [ ] Evaluation dataset exists.
- [ ] Retrieval metrics are measured.
- [ ] Generation quality is evaluated.
- [ ] API is documented.
- [ ] Tests exist.
- [ ] Security basics are implemented.
- [ ] Frontend is responsive.
- [ ] Backend is deployed.
- [ ] Frontend is deployed.
- [ ] GitHub repository is clean.
- [ ] README is complete.
- [ ] Architecture diagram is complete.
- [ ] Demo video is complete.
- [ ] Portfolio case study is complete.

---

# 38. Interview Explanation

### 30-second version

> I built an end-to-end RAG-based knowledge assistant where users can upload documents and ask questions about them. The system extracts and chunks the documents, generates embeddings, stores them in a vector database, retrieves relevant chunks using semantic search, reranks the candidates, and passes the best context to an LLM. The response is grounded in the retrieved documents and includes source citations. I also evaluated retrieval and generation quality to compare different RAG configurations.

### Technical follow-up topics

Be prepared to explain:

- Why RAG instead of fine-tuning?
- How chunking affects retrieval
- Embeddings
- Cosine similarity
- Top-K
- Reranking
- Vector databases
- Hybrid search
- BM25
- Query rewriting
- Metadata filtering
- Hallucination reduction
- Context window
- Prompt injection
- RAG evaluation
- Precision@K
- Recall@K
- MRR
- Faithfulness
- Answer relevance
- FastAPI architecture
- Async processing
- Deployment

---

# 39. Future Improvements

After the core project is stable:

- Hybrid search (BM25 + semantic search)
- Better reranking
- Query expansion
- Query rewriting
- Parent-child retrieval
- Multi-vector retrieval
- Streaming responses
- Background document processing
- Authentication
- Team workspaces
- Managed vector database
- Advanced evaluation dashboard
- Agentic RAG
- Multi-modal document support
- OCR for scanned PDFs

These should remain future improvements unless they are explicitly implemented.

---

# 40. Development Order

Do not build everything at once.

Recommended sequence:

```text
Phase 1
Project Setup
    ↓
Phase 2
Document Upload + Extraction
    ↓
Phase 3
Chunking + Embeddings
    ↓
Phase 4
Vector Database
    ↓
Phase 5
Semantic Retrieval
    ↓
Phase 6
LLM Generation
    ↓
Phase 7
Citations
    ↓
Phase 8
Reranking
    ↓
Phase 9
FastAPI Integration
    ↓
Phase 10
Frontend Chat UI
    ↓
Phase 11
Evaluation
    ↓
Phase 12
Testing + Security
    ↓
Phase 13
Deployment
    ↓
Phase 14
Architecture + Demo Video
    ↓
Phase 15
README + Portfolio Case Study
```

---

# 41. Guiding Principle

The goal is not to build the largest RAG application.

The goal is to build a **small but technically credible AI system** that demonstrates:

```text
Understanding
     +
Implementation
     +
Evaluation
     +
Deployment
     +
Communication
```

A client should be able to look at the project and conclude:

> "This developer understands how a real RAG system works and can build one for my product."
