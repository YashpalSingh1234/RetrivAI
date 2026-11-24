# RetrivAI

RetrivAI is a private, document-grounded question-answering workspace. Upload PDF, DOCX, or UTF-8 TXT files, ask a question, and inspect the passages used to answer it.

## What it does

- Creates an account and isolates documents and conversations by account.
- Validates uploads and extracts page-aware text where the format supports it.
- Cleans and splits text into overlapping chunks, then stores text and embeddings in PostgreSQL with pgvector.
- Searches the signed-in user's documents and optionally reranks candidates with a cross-encoder.
- Answers from retrieved context, displays source passages, and declines when retrieval is too weak.
- Uses an OpenAI-compatible chat completions API when configured. With no API key, it returns a clearly labeled extractive answer so the local app still works.
- Stores users, document status, and chat history in the same PostgreSQL database.
- Includes retrieval metrics, generation quality heuristics, and a small manually checked sample dataset.

## Architecture

```text
Upload → validate → extract → clean → chunk → embed → PostgreSQL + pgvector
Question → embed → account-scoped search → cross-encoder rerank
         → cited context → LLM or extractive fallback → answer + sources
```

FastAPI coordinates the backend workflows. PostgreSQL stores account records, chat history, and source passages. pgvector ranks passages by cosine distance after scoping them to the signed-in account. The Next.js frontend talks to FastAPI using an HTTP-only session cookie.

See [RetrivAI_Doc.md](docs/RetrivAI_Doc.md) for the product specification and [RetrivAI_CODE_MAP.md](docs/RetrivAI_CODE_MAP.md) for module responsibilities.

## Run locally

### 1. Configure the backend

Use Python 3.10 or newer. From the repository root:

```powershell
py -3.10 -m venv RetrivAI_Venv
.\RetrivAI_Venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux, create/activate the virtual environment with `python3 -m venv .venv` and `source .venv/bin/activate`, then copy `.env.example` to `.env`.

Use an empty PostgreSQL database on a server with [pgvector installed](https://github.com/pgvector/pgvector#installation). Set `DATABASE_URL` in the root `.env` to the real connection string. An administrator can run `CREATE EXTENSION IF NOT EXISTS vector;` in that database if the app role cannot create extensions.

For a Docker-managed database with the backend running on your host, run `docker compose up -d db` and use port `5433` in `DATABASE_URL`. For existing SQLite and Chroma data, run the import below before opening the app against the new database.

Start the API from the repository root:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The API health check is at `http://localhost:8000/health`; interactive API documentation is at `http://localhost:8000/docs` while `APP_ENV` is not `production`.

### 2. Start the frontend

Use Node.js 20.9 or newer. In another terminal:

```bash
cd frontend
npm ci
```

Copy `frontend/.env.example` to `frontend/.env.local`, then run:

```bash
npm run dev
```

Open `http://localhost:3000`, create an account, and upload a document. The embedding and reranker model weights are downloaded the first time they are needed, so the first indexing or question may take longer.

### 3. Configure answer generation with Qwen 3.5

Start [Ollama](https://ollama.com/download), then download the local 4B model:

```powershell
ollama pull qwen3.5:4b
```

Set these values in the root `.env` and restart the backend:

```dotenv
LLM_API_KEY=ollama
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL=qwen3.5:4b
LLM_REASONING_EFFORT=none
LLM_TIMEOUT_SECONDS=180
```

`ollama` is a placeholder key accepted by the local runtime. The API sends the question, selected passages, and bounded chat history to that local endpoint. For a portable Windows setup, start the project copy from the repository root using:

```powershell
$env:OLLAMA_MODELS = Join-Path (Get-Location).Path 'data\ollama\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_NO_CLOUD = '1'
& '.\data\ollama\runtime\ollama.exe' serve
```

The app uses source excerpts when the model is unavailable or returns an answer without valid citations.

For another OpenAI-compatible provider, set its endpoint, model and key in the root `.env`, and leave `LLM_REASONING_EFFORT` empty unless that provider supports it:

```dotenv
LLM_API_KEY=your-provider-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

`LLM_BASE_URL` must expose an OpenAI-compatible `/chat/completions` endpoint. The key stays on the backend. For Docker, use an endpoint reachable from the backend container.

## Configuration

The root `.env.example` documents the settings. Common options:

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Set in `.env` | PostgreSQL connection string for the host backend |
| `POSTGRES_PASSWORD` | `retrivai` for local Compose | Password for the Compose database |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Shared query/document embedding model |
| `EMBEDDING_DIMENSION` | `768` | Vector size for the configured model and database schema |
| `RERANKER_ENABLED` | `true` | Enable cross-encoder reranking |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` | Chunk configuration in characters |
| `DEFAULT_TOP_K` / `MAX_TOP_K` | `5` / `20` | Retrieval response limits |
| `MIN_RELEVANCE_SCORE` | `0.22` | Low-evidence cutoff for an insufficient-context response |
| `MAX_UPLOAD_MB` | `20` | Upload size limit |
| `FRONTEND_URLS` | local Next.js origins | Exact CORS origins allowed to send session cookies |
| `COOKIE_SECURE` | `false` | Set `true` when serving over HTTPS |

The first account is created from the frontend. Passwords are stored as PBKDF2 hashes. The browser receives an HTTP-only signed session cookie. Back up the PostgreSQL database, including the `document_chunks` table.

## Import an existing SQLite and Chroma workspace

Stop the old backend so the files represent one consistent snapshot. Set `DATABASE_URL` to the empty PostgreSQL target and keep the embedding model and dimensions used by the original workspace. From the project root with the Python environment active:

```bash
python -m pip install -r backend/requirements-migration.txt
python -m backend.app.core.migrate_legacy
```

The default sources are `data/retrivai.sqlite3` and `data/chroma_df`. Pass `--sqlite PATH` and `--chroma PATH` for other locations. The import preserves accounts, password hashes, the session signing secret, document IDs, chat history, and indexed passages with their existing embeddings. It validates ready-document passage counts, commits the import together, and leaves the source files in place. Unowned sample passages are skipped. An upload that was interrupted before cutover can be retried.

After the import succeeds, start the new backend and check the document list, an existing chat, and a cited answer.

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend liveness and model configuration |
| `POST` | `/auth/register` | Create an account and session |
| `POST` | `/auth/login` | Start a session |
| `POST` | `/auth/logout` | End the browser session |
| `GET` | `/auth/me` | Get the current account |
| `POST` | `/documents/upload` | Validate and index a document |
| `GET` | `/documents` | List the current account's documents |
| `DELETE` | `/documents/{document_id}` | Delete a document and its vectors |
| `POST` | `/query` | Ask one question |
| `POST` | `/chat` | Ask and save a conversation turn |
| `GET` | `/chat/conversations` | List saved conversations |
| `GET` | `/chat/conversations/{id}` | Load a conversation |
| `DELETE` | `/chat/conversations/{id}` | Delete a conversation |
| `POST` | `/evaluation/retrieval` | Compute Precision@K, Recall@K, and reciprocal rank |
| `POST` | `/evaluation/generation` | Compute transparent lexical quality signals |

Protected routes require the session cookie. The frontend handles this automatically. OpenAPI documentation includes example request/response schemas.

## Evaluation

The small dataset in `backend/app/evaluation/dataset.jsonl` is grounded in the bundled one-page Big Data notes PDF. Run the retrieval evaluation from the repository root:

```bash
python -m backend.app.evaluation.run_dataset --top-k 5
```

The script indexes the sample PDF in a PostgreSQL test transaction and reports Precision@K, Recall@K, and MRR. The sample rows are rolled back after evaluation. Add `--with-reranker` to compare vector-only results with cross-encoder reranking. Add questions and verified relevant page/text labels to compare chunk and top-K configurations.

The generation endpoint reports lexical proxies for faithfulness, context relevance, answer relevance, and citation correctness. Token overlap cannot establish entailment, so these values are indicators for manual review, not proof that an answer is faithful.

## Local container deployment

Copy `.env.example` to `.env`, set `COOKIE_SECURE=false` for local HTTP, then run:

```bash
docker compose up --build
```

This starts PostgreSQL with pgvector, the API on port 8000, and the web app on port 3000. PostgreSQL uses the `postgres-data` volume and is reachable from the host at `127.0.0.1:5433`. Model cache files live under `data/`. For a public HTTPS deployment, configure the PostgreSQL credentials and allowed frontend origins, and set `COOKIE_SECURE=true`. If the frontend and API are on different sites, set `COOKIE_SAMESITE=none`.

## Project structure

```text
backend/app/api/          FastAPI routes
backend/app/core/         Configuration, PostgreSQL schema, auth, dependencies
backend/app/ingestion/    Loaders, cleaning, chunking, embeddings, pgvector
backend/app/retrieval/    Retrieval, reranking, context and citations
backend/app/generation/   Grounded prompts and LLM integration
backend/app/evaluation/   Retrieval/generation metrics and sample dataset
frontend/app/             Next.js pages
frontend/components/      Workspace, upload, chat, sources, architecture
frontend/lib/             API client and TypeScript types
docs/                     Product specification and code map
```
