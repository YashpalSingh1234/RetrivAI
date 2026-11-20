# RetrivAI

RetrivAI is a private, document-grounded question-answering workspace. Upload PDF, DOCX, or UTF-8 TXT files, ask a question, and inspect the passages used to answer it.

## What it does

- Creates an account and isolates documents and conversations by account.
- Validates uploads and extracts page-aware text where the format supports it.
- Cleans and splits text into overlapping chunks, then embeds and stores them in Chroma.
- Searches the signed-in user's documents and optionally reranks candidates with a cross-encoder.
- Answers from retrieved context, displays source passages, and declines when retrieval is too weak.
- Uses an OpenAI-compatible chat completions API when configured. With no API key, it returns a clearly labeled extractive answer so the local app still works.
- Stores users, document status, and chat history in SQLite.
- Includes retrieval metrics, generation quality heuristics, and a small manually checked sample dataset.

## Architecture

```text
Upload → validate → extract → clean → chunk → embed → Chroma
Question → embed → account-scoped search → cross-encoder rerank
         → cited context → LLM or extractive fallback → answer + sources
```

FastAPI coordinates the backend workflows. Chroma stores vectors and passage metadata; SQLite stores account, document, and conversation records. The Next.js frontend talks to FastAPI using an HTTP-only session cookie.

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

### 3. Configure answer generation (optional)

The app works without a model API key using extractive answers. For generated answers, set these in the root `.env`:

```dotenv
LLM_API_KEY=your-provider-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

`LLM_BASE_URL` must expose an OpenAI-compatible `/chat/completions` endpoint. The key stays on the backend. When generation is enabled, retrieved excerpts and the current question are sent to that provider; uploaded files and full documents are not sent as a whole.

## Configuration

The root `.env.example` documents the settings. Common options:

| Setting | Default | Purpose |
| --- | --- | --- |
| `DATABASE_PATH` | `data/retrivai.sqlite3` | SQLite application metadata |
| `VECTOR_DB_PATH` | `data/chroma_df` | Persistent Chroma collection |
| `EMBEDDING_MODEL` | `sentence-transformers/all-mpnet-base-v2` | Shared query/document embedding model |
| `RERANKER_ENABLED` | `true` | Enable cross-encoder reranking |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `200` | Chunk configuration in characters |
| `DEFAULT_TOP_K` / `MAX_TOP_K` | `5` / `20` | Retrieval response limits |
| `MIN_RELEVANCE_SCORE` | `0.22` | Low-evidence cutoff for an insufficient-context response |
| `MAX_UPLOAD_MB` | `20` | Upload size limit |
| `FRONTEND_URLS` | local Next.js origins | Exact CORS origins allowed to send session cookies |
| `COOKIE_SECURE` | `false` | Set `true` when serving over HTTPS |

The first account is created from the frontend. Passwords are stored as PBKDF2 hashes; the browser receives an HTTP-only signed session cookie. SQLite and Chroma data are local files and should be backed up together.

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

The script indexes that sample PDF under a separate `evaluation` owner in the local Chroma collection, then reports Precision@K, Recall@K, and MRR. Add `--with-reranker` to compare vector-only results with cross-encoder reranking. Add questions and verified relevant page/text labels to compare chunk and top-K configurations.

The generation endpoint reports lexical proxies for faithfulness, context relevance, answer relevance, and citation correctness. Token overlap cannot establish entailment, so these values are indicators for manual review, not proof that an answer is faithful.

## Local container deployment

Copy `.env.example` to `.env`, set `COOKIE_SECURE=false` for local HTTP, then run:

```bash
docker compose up --build
```

This starts the API on port 8000 and the web app on port 3000. Persistent SQLite, Chroma, and model cache data live under `data/`. For a public HTTPS deployment, configure a strong origin list and set `COOKIE_SECURE=true`. If the frontend and API are on different sites, also set `COOKIE_SAMESITE=none`. Use persistent, private database/vector volumes and review the hosting provider's resource limits for the embedding and reranker models. Cloud deployment still requires your hosting account and service configuration.

## Project structure

```text
backend/app/api/          FastAPI routes
backend/app/core/         Configuration, SQLite, auth, dependencies
backend/app/ingestion/    Loaders, cleaning, chunking, embeddings, Chroma
backend/app/retrieval/    Retrieval, reranking, context and citations
backend/app/generation/   Grounded prompts and LLM integration
backend/app/evaluation/   Retrieval/generation metrics and sample dataset
frontend/app/             Next.js pages
frontend/components/      Workspace, upload, chat, sources, architecture
frontend/lib/             API client and TypeScript types
docs/                     Product specification and code map
```
