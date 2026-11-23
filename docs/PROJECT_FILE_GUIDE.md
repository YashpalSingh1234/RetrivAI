# RetrivAI Project File Guide

RetrivAI mein Next.js browser UI chalata hai, FastAPI login, upload aur chat requests handle karta hai, aur PostgreSQL application records ke saath passage text aur pgvector embeddings store karta hai. Neeche har source file, command-line script aur project config ka role diya hai. File naam par click karke seedha code khol sakte ho.

## App ke teen main flows

- **Sign in.** `AuthPanel.tsx` credentials `lib/api.ts` ke through bhejta hai. Backend ka `api/auth.py` account verify karta hai aur session cookie set karta hai. `Workspace.tsx` `/auth/me` se session check karke private workspace kholta hai.
- **Upload.** `DocumentUpload.tsx` multipart request bhejta hai. `api/documents.py` request ko document service tak le jata hai. Service file validate karti hai, text nikalti hai, passages banati hai aur embeddings ke saath PostgreSQL mein save karti hai.
- **Question.** `ChatWindow.tsx` question `/chat` ko bhejta hai. Query pipeline pgvector se apne account ke relevant passages nikalti hai, optional reranker se order improve karti hai aur citations ke saath answer banati hai. Chat ka turn PostgreSQL mein save hota hai.

## Root configuration aur deployment

| File | Kya kaam karti hai |
| --- | --- |
| [`docker-compose.yml`](../docker-compose.yml) | `db`, `backend` aur `frontend` services define karti hai. pgvector wala PostgreSQL named volume use karta hai. Compose host par database `5433`, FastAPI `8000` aur Next.js `3000` par milte hain. Health checks startup order set karte hain. |
| [`.env.example`](../.env.example) | Backend settings ka template. Ismein database URL, embedding model/dimension, chunk size, reranker, LLM settings, allowed frontend origins, upload limit aur session settings ke example values hain. |
| [`.gitignore`](../.gitignore) | Local secrets, venv, Python cache, Next.js build output aur database data ko Git ignore list mein rakhti hai. |
| [`.dockerignore`](../.dockerignore) | Root se banne wale backend Docker image ke build context se `.env`, runtime data, venv, frontend, docs aur test files hataati hai. |
| [`README.md`](../README.md) | App setup, run commands, environment settings, API routes, PostgreSQL migration, evaluation aur Docker deployment ka operational reference. |

Root ki local `.env` file active `DATABASE_URL`, LLM credentials aur doosri machine-specific settings rakhne ki jagah hai. Backend `core/config.py` se ise load karta hai, aur Docker Compose bhi ise configuration ke liye use karta hai.

## Backend entry point aur HTTP routes

| File | Kya kaam karti hai |
| --- | --- |
| [`backend/Dockerfile`](../backend/Dockerfile) | Python image mein `backend/requirements.txt` install karta hai aur Uvicorn se `backend.app.main:app` ko port `8000` par start karta hai. |
| [`backend/requirements.txt`](../backend/requirements.txt) | Backend ke runtime Python dependencies. FastAPI aur Uvicorn API ke liye, PyMuPDF aur python-docx readers ke liye, Sentence Transformers embeddings ke liye aur Psycopg PostgreSQL ke liye. |
| [`backend/requirements-migration.txt`](../backend/requirements-migration.txt) | Purane vectors read karne ke liye Chroma Python package specify karti hai. Ise legacy import ke waqt install karte hain. |
| [`backend/app/main.py`](../backend/app/main.py) | FastAPI entry point. Startup par database initialize karta hai aur routers jodta hai. Middleware CORS, cookie-based writes ke Origin checks, upload ki request-size check, request IDs aur timing logs handle karta hai. |
| [`backend/app/api/health.py`](../backend/app/api/health.py) | `GET /health` se service status, configured embedding model aur LLM key ki availability return karti hai. Frontend startup par ye endpoint call karta hai. |
| [`backend/app/api/auth.py`](../backend/app/api/auth.py) | Register, login, logout aur current-user endpoints. Auth helpers ko call karti hai, signed session cookie set ya clear karti hai aur duplicate email par `409` deti hai. |
| [`backend/app/api/documents.py`](../backend/app/api/documents.py) | Authenticated upload, list aur delete routes. Uploaded file ko bounded bytes mein read karti hai, document service call karti hai aur processing errors ko HTTP responses mein badalti hai. |
| [`backend/app/api/query.py`](../backend/app/api/query.py) | `POST /query` single answer deta hai. `POST /chat` question aur answer ko conversation mein save karta hai. `_query_pipeline()` user ke ready documents check karta hai, retrieval aur reranking chalata hai aur relevance threshold ke baad cited context banata hai. Isi file mein chat history list, open aur delete routes hain. |
| [`backend/app/api/evaluation.py`](../backend/app/api/evaluation.py) | Signed-in user ke liye retrieval aur generation metrics ke endpoints. Request body se inputs lekar evaluation helpers ka score return karti hai. |
| [`backend/app/models/schemas.py`](../backend/app/models/schemas.py) | Pydantic models mein request validation aur response ka shape define karti hai. Email, password aur question ki limits ke saath user, document, conversation, answer, citation, health aur evaluation types yahin hain. |

## Backend config, session aur database

| File | Kya kaam karti hai |
| --- | --- |
| [`backend/app/core/config.py`](../backend/app/core/config.py) | Root `.env` load karke `settings` banati hai. `DATABASE_URL`, `EMBEDDING_DIMENSION`, model names, search limits, CORS origins aur cookie behavior ki configuration yahin se aati hai. |
| [`backend/app/core/database.py`](../backend/app/core/database.py) | `database()` Psycopg connection ko transaction context mein kholta hai. `initialize_database()` pgvector extension aur `users`, `documents`, `document_chunks`, `conversations`, `messages` aur `app_meta` tables taiyar karta hai. Yahin vector dimension check aur session signing secret ka access hai. |
| [`backend/app/core/auth.py`](../backend/app/core/auth.py) | Passwords ko PBKDF2 se hash aur verify karti hai, PostgreSQL mein accounts create ya lookup karti hai aur expiry wale HMAC-signed session tokens issue ya verify karti hai. |
| [`backend/app/core/dependencies.py`](../backend/app/core/dependencies.py) | FastAPI routes ke liye shared auth aur rate-limit dependencies. Session cookie ya Bearer token se current user lookup karti hai aur invalid session par `401` deti hai. |
| [`backend/app/core/security.py`](../backend/app/core/security.py) | Filename normalize karti hai aur upload extension, MIME type, file size aur actual content check karti hai. Yahin per-process request rate limiter hai, jisme login/register ke liye tighter limit hai. |
| [`backend/app/core/services.py`](../backend/app/core/services.py) | `get_embedding_service()`, `get_vector_store()`, `get_retriever()` aur `get_reranker()` ke cached instances return karti hai. API aur document service in helpers se shared ML services leti hain. |
| [`backend/app/core/migrate_legacy.py`](../backend/app/core/migrate_legacy.py) | One-time CLI. SQLite ke users, document records, conversations, messages aur auth secret copy karti hai. Chroma ki scratch copy se passages aur existing vectors read karti hai, owner aur count verify karke PostgreSQL mein ek transaction mein import karti hai. Import marker repeat run ko skip karta hai. |

## Document processing aur search

| File | Kya kaam karti hai |
| --- | --- |
| [`backend/app/services/__init__.py`](../backend/app/services/__init__.py) | Chhoti Python package file. `services` directory ko application ke workflow modules ke package ke roop mein mark karti hai. |
| [`backend/app/services/documents.py`](../backend/app/services/documents.py) | `process_document()` validation se indexing tak ka poora workflow chalata hai. Content hash se duplicate upload pehchanta hai, document row lock karta hai aur passages plus `Ready` status transaction mein save karta hai. Failure par partial passages rollback hote hain. List, lookup aur delete queries owner ke hisaab se scoped hain. Delete par database related chunks bhi hataata hai. |
| [`backend/app/ingestion/loaders.py`](../backend/app/ingestion/loaders.py) | `load_pdf()` disk path se PDF ka page-wise text nikalta hai. `load_document_bytes()` upload bytes se PDF, DOCX ya UTF-8 TXT ko filename, full text aur page records mein convert karta hai. DOCX paragraphs aur tables page `1` ke under aate hain. |
| [`backend/app/ingestion/cleaner.py`](../backend/app/ingestion/cleaner.py) | `clean_text()` Unicode, whitespace aur line endings normalize karta hai. `clean_document()` ye cleanup har page par chala kar original filename, page numbers aur doosri metadata preserve karta hai. |
| [`backend/app/ingestion/chunker.py`](../backend/app/ingestion/chunker.py) | `DocumentChunker` text ko har page ke andar overlapping passages mein split karta hai. Har passage ko document ID, page number, chunk index aur text hash se stable ID deta hai. Input document mein `document_id` chahiye. |
| [`backend/app/ingestion/embeddings.py`](../backend/app/ingestion/embeddings.py) | `EmbeddingService` configured Sentence Transformer ko pehli zaroorat par load karta hai aur available GPU ya CPU use karta hai. `embed_chunks()` passages ke vectors banata hai. `embed_query()` question ko usi vector space mein convert karta hai. |
| [`backend/app/ingestion/vector_store.py`](../backend/app/ingestion/vector_store.py) | `VectorStore.add_chunks()` `document_chunks` table mein passages aur embeddings batch mein save karta hai. `search()` signed-in owner ke ready documents par pgvector cosine distance se top matches nikalta hai. Search selected document IDs tak bhi limit ho sakti hai. |
| [`backend/app/ingestion/check.py`](../backend/app/ingestion/check.py) | Purane experiments ke import path ka compatibility wrapper. `VectorStore` class ko `vector_store.py` se re-export karti hai. |
| [`backend/app/retrieval/retriever.py`](../backend/app/retrieval/retriever.py) | Question ki embedding banata hai, `VectorStore.search()` ko owner aur optional document IDs deta hai aur cosine distance ko relevance score mein convert karta hai. |
| [`backend/app/retrieval/reranker.py`](../backend/app/retrieval/reranker.py) | Optional cross-encoder question aur candidate passages ko pairs mein score karke final order banata hai. Model unavailable ho to original vector score ka order aur warning return karta hai. |
| [`backend/app/retrieval/context.py`](../backend/app/retrieval/context.py) | Final passages ko configured character limit ke andar pack karta hai. `[S1]` jaise labels banata hai aur har citation ke saath filename, page, excerpt, chunk index aur relevance score rakhta hai. |

## Answer generation aur evaluation

| File | Kya kaam karti hai |
| --- | --- |
| [`backend/app/generation/prompts.py`](../backend/app/generation/prompts.py) | `build_messages()` question, selected evidence aur bounded recent history se model messages banata hai. System instructions answer ko supplied passages aur unke citation labels tak ground karne ko kehti hain. |
| [`backend/app/generation/llm.py`](../backend/app/generation/llm.py) | Configured OpenAI-compatible `/chat/completions` endpoint ko call karti hai. Model/key unavailable ho to source sentences se extractive answer banati hai. Evidence unavailable ho to insufficient-context response deti hai. |
| [`backend/app/evaluation/retrieval.py`](../backend/app/evaluation/retrieval.py) | Precision@K, Recall@K aur reciprocal rank calculate karti hai. Input expected relevant passage IDs aur retrieval ka ordered result hota hai. |
| [`backend/app/evaluation/generation.py`](../backend/app/evaluation/generation.py) | Answer, context, question aur optional expected text ke word overlap se quality signals calculate karti hai. Citation IDs ko available IDs se compare karti hai. Ye scores approximate indicators hain. |
| [`backend/app/evaluation/run_dataset.py`](../backend/app/evaluation/run_dataset.py) | Sample PDF aur labeled questions se retrieval benchmark chalati hai. Temporary PostgreSQL transaction mein sample index karti hai, vector aur optional reranked results score karti hai, summary JSON print karti hai aur sample rows rollback karti hai. |
| [`backend/app/evaluation/dataset.jsonl`](../backend/app/evaluation/dataset.jsonl) | Har line ek benchmark case hai. Ismein question, expected answer, source filename, relevant page aur relevant passage mein expected phrase hoti hai. |

## Frontend pages aur styling

| File | Kya kaam karti hai |
| --- | --- |
| [`frontend/app/layout.tsx`](../frontend/app/layout.tsx) | Sab routes ka root page shell. HTML language, browser title, description aur `globals.css` import yahin set hote hain. |
| [`frontend/app/page.tsx`](../frontend/app/page.tsx) | `/` route. `Workspace` ko `overview` tab ke saath kholta hai. |
| [`frontend/app/chat/page.tsx`](../frontend/app/chat/page.tsx) | `/chat` route. `Workspace` ka chat tab kholta hai. |
| [`frontend/app/documents/page.tsx`](../frontend/app/documents/page.tsx) | `/documents` route. `Workspace` ka document library tab kholta hai. |
| [`frontend/app/architecture/page.tsx`](../frontend/app/architecture/page.tsx) | `/architecture` route. `Workspace` ka How it works tab kholta hai. |
| [`frontend/app/globals.css`](../frontend/app/globals.css) | Puri UI ke shared colors, font sizes, buttons, form styles, layout aur mobile breakpoints. Login, navigation, chat, uploads, citations aur architecture diagram ke styles yahin milte hain. |

## Frontend components aur API client

| File | Kya kaam karti hai |
| --- | --- |
| [`frontend/components/Workspace.tsx`](../frontend/components/Workspace.tsx) | Charon pages ka shared React component. Pehle backend health aur current session check karta hai, phir user ki document list load karta hai. Loading, connection error, sign-in aur signed-in workspace states choose karta hai. Sidebar, overview counts aur selected page ka content render karta hai. |
| [`frontend/components/AuthPanel.tsx`](../frontend/components/AuthPanel.tsx) | Sign-in aur account creation form. Email aur password input, password hint, pending state aur error messages handle karta hai. Success par user record `Workspace` ko deta hai. |
| [`frontend/components/ChatWindow.tsx`](../frontend/components/ChatWindow.tsx) | Question input, suggested questions, messages, loading feedback aur conversation history manage karta hai. Backend ko question bhejta hai, result aur citations render karta hai aur `localStorage` mein last open conversation ki ID yaad rakhta hai. Saved messages backend se load hote hain. |
| [`frontend/components/DocumentUpload.tsx`](../frontend/components/DocumentUpload.tsx) | File picker aur drag-and-drop upload UI. File extension aur 20 MB limit browser mein check karta hai, `api.uploadDocument()` call karta hai aur success par parent ko naya document record deta hai. |
| [`frontend/components/DocumentList.tsx`](../frontend/components/DocumentList.tsx) | Library ki file rows, filename, size, date, processing status aur upload error dikhata hai. Remove confirm karne par delete request bhejta hai aur parent list update karta hai. |
| [`frontend/components/SourceCitation.tsx`](../frontend/components/SourceCitation.tsx) | Chat answer ke source cards dikhata hai. Card expand karne par source file, page aur relevant text milta hai. |
| [`frontend/components/ArchitectureDiagram.tsx`](../frontend/components/ArchitectureDiagram.tsx) | Indexing aur question-answering ke steps ka clickable diagram. `steps` array mein har node ka label aur explanation hai. Selected node par us step ka description dikhata hai. |
| [`frontend/lib/api.ts`](../frontend/lib/api.ts) | FastAPI ke liye browser HTTP client. `NEXT_PUBLIC_API_URL` se backend address leta hai, requests mein session cookie include karta hai, uploads ke liye `FormData` banata hai aur HTTP failures ko `ApiError` mein convert karta hai. |
| [`frontend/lib/types.ts`](../frontend/lib/types.ts) | TypeScript mein backend responses ke shapes. User, documents, health, citations, answers, conversations aur messages ke types UI aur API client yahin se import karte hain. |

## Frontend build files

| File | Kya kaam karti hai |
| --- | --- |
| [`frontend/package.json`](../frontend/package.json) | npm scripts `dev`, `build`, `start` aur `typecheck` define karta hai. Next.js, React, TypeScript aur Tailwind dependencies bhi yahin declare hoti hain. |
| [`frontend/package-lock.json`](../frontend/package-lock.json) | npm dependency tree ki exact versions lock karta hai, taaki `npm ci` repeatable install kare. |
| [`frontend/tsconfig.json`](../frontend/tsconfig.json) | TypeScript strict checks, JSX handling aur `@/*` import alias set karta hai. Next.js ke generated route types ko include karta hai. |
| [`frontend/next-env.d.ts`](../frontend/next-env.d.ts) | Next.js ki generated TypeScript declaration file. Framework aur generated route definitions ko TypeScript project se jodti hai. `next dev` aur `next build` ise refresh karte hain. |
| [`frontend/next.config.ts`](../frontend/next.config.ts) | Next.js server aur build settings. Current config response ke `X-Powered-By` header ko disable karti hai. |
| [`frontend/postcss.config.mjs`](../frontend/postcss.config.mjs) | PostCSS ke through Tailwind CSS build plugin load karti hai. |
| [`frontend/.env.example`](../frontend/.env.example) | Frontend ke liye API address ka template. Isse local `frontend/.env.local` bana kar browser ke liye `NEXT_PUBLIC_API_URL` set kar sakte ho. |
| [`frontend/.dockerignore`](../frontend/.dockerignore) | Frontend image ke context se local env files, `node_modules`, `.next` aur logs hataati hai. |
| [`frontend/Dockerfile`](../frontend/Dockerfile) | Pehle `npm ci` se dependencies install karta hai, phir `NEXT_PUBLIC_API_URL` build argument ke saath production build banata hai. Image Next.js ko port `3000` par start karti hai. |

## Test aur demo scripts

`testFile/` ki scripts repo root se Python module ke roop mein chalti hain. Ye sample PDF aur chhote example inputs par individual pipeline steps inspect karne ke kaam aati hain.

| File | Kya kaam karti hai |
| --- | --- |
| [`testFile/test_pdf_loader.py`](../testFile/test_pdf_loader.py) | Sample PDF ko `load_pdf()` se read karke filename, page count, extracted text aur page records print karti hai. |
| [`testFile/test_pdf_cleaner.py`](../testFile/test_pdf_cleaner.py) | Sample PDF load karke `clean_document()` chalati hai aur cleaned text preview plus first-page text print karti hai. |
| [`testFile/test_pdf_chunker.py`](../testFile/test_pdf_chunker.py) | PDF ko load aur clean karke `DocumentChunker` ke passage IDs, metadata, length aur text preview print karne ke liye hai. Current script input mein `document_id` missing hone par chunker `ValueError` deta hai. |
| [`testFile/test_pdf_embeddings.py`](../testFile/test_pdf_embeddings.py) | PDF se chunks, embedding dimension, device, vector values aur query vector shape inspect karne ke liye hai. Current script bhi missing `document_id` par chunking step mein rukti hai. |
| [`testFile/test_semantic_similarity.py`](../testFile/test_semantic_similarity.py) | Teen sample sentences embed karti hai aur normalized vectors ka dot product lekar cosine similarity matrix print karti hai. Isse related aur unrelated sentences ke scores dekh sakte ho. |
| [`testFile/test_vector_store.py`](../testFile/test_vector_store.py) | PostgreSQL retrieval benchmark ka chhota CLI wrapper. Seedha `run_dataset.main()` call karta hai, isliye benchmark ke flags bhi isi command se use ho sakte hain. |
| [`testdata/Big_Data_Basics_Complete_Study_Notes.pdf`](../testdata/Big_Data_Basics_Complete_Study_Notes.pdf) | PDF loader demos aur labeled retrieval benchmark ke liye shared sample document. |

```powershell
python -m testFile.test_pdf_loader
python -m testFile.test_vector_store --top-k 5 --with-reranker
```

Vector benchmark ke liye PostgreSQL mein pgvector available hona chahiye, `DATABASE_URL` set hona chahiye aur embedding model load ho sakna chahiye.

## Project docs aur generated folders

| File | Kya kaam karti hai |
| --- | --- |
| [`docs/RetrivAI_Doc.md`](../docs/RetrivAI_Doc.md) | Product requirements, planned architecture, technology choices aur behavior ka detailed specification. |
| [`docs/RetrivAI_CODE_MAP.md`](../docs/RetrivAI_CODE_MAP.md) | Earlier architecture aur coding plan ka reference. Ismein proposed directory names aur test files ke examples bhi hain. |

- `data/postgres_local/` local Windows PostgreSQL instance ke program files, database cluster aur logs ki jagah hai. Docker setup database ke liye `postgres-data` volume use karta hai.
- `data/retrivai.sqlite3` aur purana `data/chroma_df/` legacy import ke expected source paths hain. Alternate backup paths migration CLI ke `--sqlite` aur `--chroma` flags se pass hote hain.
- `data/hf_cache/` container setup mein downloaded embedding aur reranker model files ki cache hai.
- `__pycache__/` aur `*.pyc` Python bytecode cache hain. `RetrivAI_Venv/` installed Python environment hai. `frontend/.next/` generated routes aur build output rakhta hai, aur `frontend/node_modules/` npm packages rakhta hai.
