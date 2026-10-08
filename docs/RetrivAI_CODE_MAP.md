# RetrivAI — Complete Code Map & File Responsibility Guide

**Purpose:** This is the implementation blueprint for RetrivAI. It explains what every file does, what kind of code belongs inside it, what it imports/references, and how the complete system connects.

> This document intentionally does NOT provide the finished implementation. You will write the code yourself, file by file, to understand the system deeply.

## 1. Final Project Structure

```text
RetrivAI/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── documents.py
│   │   │   ├── query.py
│   │   │   └── health.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── ingestion/
│   │   │   ├── loaders.py
│   │   │   ├── cleaner.py
│   │   │   ├── chunker.py
│   │   │   └── embeddings.py
│   │   ├── retrieval/
│   │   │   ├── retriever.py
│   │   │   ├── reranker.py
│   │   │   └── context.py
│   │   ├── generation/
│   │   │   ├── prompts.py
│   │   │   └── llm.py
│   │   ├── evaluation/
│   │   │   ├── retrieval.py
│   │   │   └── generation.py
│   │   └── models/
│   │       └── schemas.py
│   ├── tests/
│   │   ├── test_chunker.py
│   │   ├── test_retriever.py
│   │   ├── test_generation.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── chat/
│   │   ├── documents/
│   │   └── architecture/
│   ├── components/
│   │   ├── Chat/
│   │   ├── DocumentUpload/
│   │   ├── DocumentList/
│   │   ├── SourceCitation/
│   │   └── Architecture/
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   └── public/
├── docs/
│   ├── RetrivAI_Doc.md
│   └── CODE_MAP.md
├── .env
├── .env.example
├── .gitignore
└── README.md
```

## 2. Dependency Direction

```text
Frontend
   │ HTTP
   ▼
FastAPI API Layer
   │
   ├───────────────┐
   ▼               ▼
Ingestion       Query/RAG
   │               │
   ▼               ▼
Chunking        Retrieval
   │               │
   ▼               ▼
Embeddings      Reranking
   │               │
   ▼               ▼
Vector DB       Context
                   │
                   ▼
                  LLM
                   │
                   ▼
             Answer + Sources
```

Rule:

- API modules coordinate.
- Business modules perform the actual work.
- Schemas define data shapes.
- Core contains shared configuration/security.

# 3. Root Files

## `.gitignore`

**Purpose:** Prevent secrets, caches, generated files, dependencies, local databases/vector stores, and build output from being committed.

Typical categories:

```text
.env
__pycache__/
*.pyc
.venv/
venv/
node_modules/
.next/
dist/
build/
logs/
local vector-store directory
```

No application code belongs here.

## `.env`

Stores local secrets/configuration:

```text
LLM_API_KEY
LLM_MODEL
EMBEDDING_MODEL
DATABASE_URL
VECTOR_DB_PATH
FRONTEND_URL
BACKEND_URL
```

Connection:

```text
.env → config.py → application modules
```

Never commit this file.

## `.env.example`

Contains the same variable names with empty/safe placeholder values. It documents what another developer must configure.

## `README.md`

Public GitHub entry point. Include:

- What RetrivAI is
- Problem and solution
- Features
- Architecture
- Tech stack
- Setup
- Environment variables
- API overview
- RAG pipeline
- Evaluation
- Screenshots/demo
- Live URL
- Future improvements

It can link to `docs/RetrivAI_Doc.md` and `docs/CODE_MAP.md`.

# 4. Backend

## `backend/requirements.txt`

Lists Python dependencies only.

Categories:

- FastAPI
- Uvicorn
- Pydantic
- PDF/DOCX loaders
- Sentence Transformers
- Chroma/vector DB
- Reranker model
- LLM SDK
- Testing tools

Connection:

```text
requirements.txt → Python environment → backend/app
```

## `backend/app/main.py`

FastAPI entry point.

Responsibilities:

- Create FastAPI app
- Register routers
- Configure CORS
- Register startup/shutdown behavior if needed

References:

```text
api/health.py
api/documents.py
api/query.py
core/config.py
```

Do NOT put chunking, retrieval, or LLM logic here.

# 5. API Layer

## `api/health.py`

Provides:

```text
GET /health
```

Only checks whether the backend is running.

## `api/documents.py`

Handles:

```text
POST /documents/upload
GET  /documents
DELETE /documents/{document_id}
```

It orchestrates:

```text
Upload
→ validation
→ loader
→ cleaner
→ chunker
→ embeddings
→ vector storage
→ response
```

References:

```text
core/security.py
models/schemas.py
ingestion/loaders.py
ingestion/cleaner.py
ingestion/chunker.py
ingestion/embeddings.py
```

The route should coordinate these modules, not contain their implementation.

## `api/query.py`

Handles:

```text
POST /query
POST /chat
```

Flow:

```text
Question
→ validation
→ retriever
→ reranker
→ context builder
→ prompt
→ LLM
→ answer + citations
```

References:

```text
models/schemas.py
retrieval/retriever.py
retrieval/reranker.py
retrieval/context.py
generation/prompts.py
generation/llm.py
```

# 6. Core Layer

## `core/config.py`

Central configuration layer.

Reads environment variables and exposes:

```text
LLM settings
Embedding model
Vector DB path
Database URL
Allowed origins
Chunk size
Chunk overlap
Top-K
```

Connection:

```text
.env → config.py → modules that need configuration
```

Avoid reading environment variables separately throughout every module.

## `core/security.py`

Security helpers.

Initial responsibilities:

- File type validation
- MIME/type checks
- File-size checks
- Input validation

Later:

- Authentication
- Authorization
- User/document isolation
- Rate limiting

Used by API/security-sensitive modules.

# 7. Ingestion Layer

Overall:

```text
Loader
 ↓
Cleaner
 ↓
Chunker
 ↓
Embeddings
 ↓
Vector Storage
```

## `ingestion/loaders.py`

Reads PDF/DOCX/TXT and extracts text plus useful metadata such as filename/page.

Input:

```text
uploaded file
```

Output conceptually:

```text
text + source + page metadata
```

Do not generate embeddings or call the LLM here.

## `ingestion/cleaner.py`

Cleans extracted text:

- Normalize whitespace
- Normalize line breaks
- Remove extraction artifacts
- Preserve useful structure

Connection:

```text
loaders.py → cleaner.py → chunker.py
```

## `ingestion/chunker.py`

Splits cleaned text into retrieval-friendly chunks.

Responsibilities:

- Chunk size
- Overlap
- Chunk indexes
- Metadata preservation

Conceptual output:

```text
chunk_id
document_id
chunk_index
content
page_number
source_file
```

Connection:

```text
cleaner.py → chunker.py → embeddings.py
```

## `ingestion/embeddings.py`

Generates embeddings for:

1. Document chunks
2. User queries

Initial candidate:

```text
sentence-transformers/all-mpnet-base-v2
```

Connection:

```text
chunks → embeddings → vector store
query → embeddings → retriever
```

Both document and query embeddings must use a compatible embedding space/model.

# 8. Retrieval Layer

## `retrieval/retriever.py`

Finds relevant chunks.

Responsibilities:

- Accept query
- Generate query embedding
- Search vector DB
- Return Top-K results
- Return scores/metadata

Output:

```text
chunks + scores + metadata
```

Does not generate the final answer.

## `retrieval/reranker.py`

Second-stage relevance ranking.

```text
Vector Search
→ Top-K candidates
→ Reranker
→ Top-N
```

A cross-encoder is a candidate implementation.

References results from `retriever.py`.

## `retrieval/context.py`

Builds the final LLM context.

Responsibilities:

- Select final chunks
- Format context
- Preserve source metadata
- Prepare citation information
- Keep context size under control

Connection:

```text
reranker.py → context.py → prompts.py
```

# 9. Generation Layer

## `generation/prompts.py`

Stores prompt templates.

The grounded prompt should instruct the LLM to:

- Use supplied context
- Avoid unsupported facts
- Say when context is insufficient
- Answer directly
- Support source/citation handling

Input:

```text
question + retrieved context
```

Output:

```text
LLM-ready messages/prompt
```

## `generation/llm.py`

LLM integration.

Responsibilities:

- Configure model client
- Send prompt/messages
- Receive response
- Normalize response
- Handle API/model errors

Does not perform retrieval.

# 10. Models

## `models/schemas.py`

Pydantic request/response definitions.

Likely schemas:

```text
DocumentResponse
DocumentListResponse
QueryRequest
QueryResponse
SourceCitation
ChatRequest
ChatResponse
```

Conceptually:

```text
QueryRequest
 ├── question
 └── top_k

QueryResponse
 ├── answer
 └── sources[]
```

Schemas contain data definitions, not business logic.

# 11. Evaluation

## `evaluation/retrieval.py`

Measures:

- Precision@K
- Recall@K
- MRR

Input:

```text
evaluation dataset + retrieved results
```

Output:

```text
metrics/report
```

Not called for every user query.

## `evaluation/generation.py`

Measures:

- Faithfulness
- Answer relevance
- Context relevance
- Citation correctness

Input:

```text
question
expected answer
retrieved context
generated answer
sources
```

Output:

```text
evaluation scores/report
```

# 12. Tests

## `tests/test_chunker.py`

Test:

- Chunk creation
- Chunk size
- Overlap
- Metadata
- Empty input

## `tests/test_retriever.py`

Test:

- Retrieval
- Top-K
- Metadata
- No-result behavior

## `tests/test_generation.py`

Test:

- Prompt construction
- Grounding instructions
- LLM response handling
- Error handling

Mock external LLM calls where appropriate.

## `tests/test_api.py`

Test:

```text
/health
/documents/upload
/documents
/query
```

Include success and failure cases.

# 13. Frontend

The frontend handles UI/UX only. It does not implement the RAG algorithm.

```text
Frontend
 ↓ HTTP
FastAPI
 ↓
RAG pipeline
```

## `frontend/app/page.tsx`

Main application/landing page.

May compose:

```text
RetrivAI branding
Document upload
Recent documents
Ask-question entry
Product explanation
```

References reusable components.

## `frontend/app/chat/`

Chat/workspace route.

Contains:

- Question input
- Conversation history
- Answer
- Sources
- Loading/error states

References:

```text
components/Chat
components/SourceCitation
lib/api.ts
lib/types.ts
```

## `frontend/app/documents/`

Document management route.

Features:

- Upload
- List
- Processing status
- Delete

References:

```text
DocumentUpload
DocumentList
api.ts
types.ts
```

## `frontend/app/architecture/`

Technical architecture visualization.

Should represent the actual implemented system:

```text
Document ingestion
→ Chunking
→ Embeddings
→ Vector DB
→ Retrieval
→ Reranking
→ Context
→ LLM
→ Answer
→ Citations
```

# 14. Components

## `components/Chat/`

Reusable chat UI:

```text
ChatWindow
MessageBubble
QuestionInput
LoadingIndicator
```

UI only; API calls go through `lib/api.ts`.

## `components/DocumentUpload/`

Handles:

- File selection
- Client-side validation feedback
- Upload request
- Progress/processing state
- Errors

Uses `lib/api.ts`.

## `components/DocumentList/`

Displays:

- Filename
- Type
- Status
- Date
- Delete action

Uses API helper functions.

## `components/SourceCitation/`

Displays evidence behind an answer:

```text
Sources
────────────
document.pdf — Page 12
policy.pdf   — Page 4
```

## `components/Architecture/`

Visualization components such as:

```text
ArchitectureDiagram
ArchitectureNode
ArchitectureConnection
FlowParticle
ArchitectureTooltip
```

# 15. Frontend Library

## `frontend/lib/api.ts`

Single place for frontend/backend communication.

Possible functions:

```text
uploadDocument()
getDocuments()
deleteDocument()
askQuestion()
sendChatMessage()
getHealth()
```

Connection:

```text
React components → api.ts → FastAPI
```

Avoid scattering raw `fetch()` calls throughout components.

## `frontend/lib/types.ts`

TypeScript definitions matching backend API data:

```text
Document
SourceCitation
QueryRequest
QueryResponse
ChatMessage
```

Connection:

```text
Backend response shape ↔ types.ts → React components
```

# 16. Complete Upload Flow

```text
DocumentUpload UI
      ↓
api.uploadDocument()
      ↓
POST /documents/upload
      ↓
documents.py
      ↓
security validation
      ↓
loaders.py
      ↓
cleaner.py
      ↓
chunker.py
      ↓
embeddings.py
      ↓
Vector Database
      ↓
Response
      ↓
DocumentList UI
```

# 17. Complete Query Flow

```text
QuestionInput
      ↓
api.askQuestion()
      ↓
POST /query
      ↓
query.py
      ↓
retriever.py
      ↓
Vector Database
      ↓
Top-K chunks
      ↓
reranker.py
      ↓
context.py
      ↓
prompts.py
      ↓
llm.py
      ↓
Answer + Sources
      ↓
api.ts
      ↓
Chat UI
```

# 18. Complete RAG Mental Model

```text
INDEXING TIME
Documents
 ↓
Loader
 ↓
Cleaner
 ↓
Chunker
 ↓
Embeddings
 ↓
Vector Store

QUERY TIME
User Query
 ↓
Query Embedding
 ↓
Vector Search
 ↓
Top-K
 ↓
Reranker
 ↓
Top-N Context
 ↓
Prompt
 ↓
LLM
 ↓
Answer + Citations
```

# 19. Coding Order

Do not write everything randomly.

### Phase 1 — Environment

```text
.gitignore
.env
.env.example
requirements.txt
```

### Phase 2 — FastAPI foundation

```text
core/config.py
main.py
api/health.py
```

First milestone:

```text
GET /health
```

works.

### Phase 3 — Schemas

```text
models/schemas.py
```

### Phase 4 — Ingestion

```text
loaders.py
cleaner.py
chunker.py
```

### Phase 5 — Embeddings

```text
embeddings.py
```

### Phase 6 — Retrieval

```text
retriever.py
```

### Phase 7 — Reranking

```text
reranker.py
```

### Phase 8 — Context

```text
context.py
```

### Phase 9 — Generation

```text
prompts.py
llm.py
```

### Phase 10 — API orchestration

```text
documents.py
query.py
```

### Phase 11 — Frontend

```text
lib/api.ts
lib/types.ts
components/
app/
```

### Phase 12 — Evaluation

```text
evaluation/retrieval.py
evaluation/generation.py
```

### Phase 13 — Tests

```text
tests/
```

### Phase 14 — Deployment and polish

```text
README.md
architecture
demo
deployment
```

# 20. Do Not Build One Giant RAG File

Avoid:

```text
rag.py
```

containing loading + chunking + embeddings + retrieval + reranking + LLM + API.

Prefer:

```text
API route
   ↓
specialized module
   ↓
specialized component
```

Each file should have one clear responsibility.

# 21. Four Questions Before Writing Every File

Before coding a file, answer:

1. **What is this file responsible for?**
2. **What does it receive?**
3. **What does it return?**
4. **Which module does it call?**

If those four answers are clear, write the code.

# 22. Milestones

```text
1. FastAPI /health works
        ↓
2. Document extraction works
        ↓
3. Chunking works
        ↓
4. Embeddings work
        ↓
5. Vector retrieval works
        ↓
6. Reranking works
        ↓
7. LLM answers from retrieved context
        ↓
8. Citations work
        ↓
9. Frontend connects
        ↓
10. RetrivAI works end-to-end
```

## Final Rule

Do not copy a complete RAG implementation.

Build RetrivAI yourself from this map, test every milestone, and use the specification as the architecture contract.

The objective is not merely to have a working demo. The objective is to understand every layer well enough to explain and modify it in an AI/ML interview or client project.
