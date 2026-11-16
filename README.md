# Transcript & Credential Verifier

A demo full-stack app for admissions reviewers: upload a transcript/certificate/diploma,
extract its coursework, index it for semantic search, and ask plain-language
equivalency questions ("does this cover material equivalent to our CS301 course?")
that get answered by an AI model citing the matched coursework.

Stack: **React (Vite + TypeScript)** frontend, **Django 5 + DRF** backend, **PostgreSQL**
(plain relational, no vector extension) in production-like mode, **SQLite** in dev/test.
Every external Azure/AI dependency is wrapped in a small dual-path module under
`backend/apps/common/` that calls the real SDK when credentials are configured, or
falls back to a deterministic, offline stub otherwise.

## Setup

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # already provided pre-filled for local dev; edit as needed

python manage.py migrate      # applies schema + seed-data migration
python manage.py runserver    # http://localhost:8000
```

`USE_SQLITE=True` (the default in `.env`) runs entirely on local SQLite with every
Azure/AI service stubbed - no network calls, no cost, nothing to configure. This is
also the mode `manage.py test` / CI always run in.

To run against real Postgres instead, set `USE_SQLITE=False` in `.env` and make sure
a Postgres server is reachable with the `POSTGRES_*` values in `.env` (a plain
database + role, no extensions required), then re-run `python manage.py migrate`.
Azure/AI services stay stubbed independently of `USE_SQLITE` - they only switch to
real calls when their own `AZURE_*`/`OPENAI_*` env vars are filled in.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env   # points at http://localhost:8000/api by default
npm run dev               # http://localhost:5173
```

### Demo logins

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `DemoPass123!` | admin |
| `reviewer@example.com` | `DemoPass123!` | admissions_reviewer |
| `reviewer2@example.com` | `DemoPass123!` | admissions_reviewer |

Seed data (idempotent data migration) also includes 5 applicants, 9 credentials
(already processed, with course records and search-index chunks populated), and 3
sample equivalency-query history rows.

## API surface

- `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`
- `GET|POST /api/applicants/`, `GET|PATCH|DELETE /api/applicants/{id}/`
- `GET|POST /api/credentials/` (upload via multipart: `applicant`, `institution`,
  `credential_type`, `issue_date`, `file`), `GET|PATCH|DELETE /api/credentials/{id}/`,
  `POST /api/credentials/{id}/process/`, `GET /api/credentials/{id}/records/`
- `GET|POST /api/equivalency-queries/` (ask a question / list history),
  `DELETE /api/equivalency-queries/{id}/`

Permissions: `admissions_reviewer` and `admin` can create/update/process credentials
and ask equivalency questions; only `admin` can delete (enforced in the DRF
permission class, not just hidden in the UI). Equivalency-query history is
queryset-scoped: reviewers only see their own questions, admins see everyone's.

## The pipeline

1. **Upload** - a reviewer uploads a document for an applicant. It's stored via
   `blob_store.upload_document` and a `Credential` row is created with
   `status=uploaded`.
2. **Process** (`POST /credentials/{id}/process/`) -
   `document_intelligence.extract_records` pulls out course/grade/term rows into
   `CredentialRecord`, descriptive text per course is written to `CredentialChunk`,
   each chunk is embedded via `ai.generate_embedding` and upserted into the
   `credential_chunks` search index via `search_store.upsert_chunks`. The
   credential flips to `status=processed`.
3. **Ask** (`POST /equivalency-queries/`) - the question is embedded, the top
   matching coursework chunks are retrieved via `search_store.search`, and
   `ai.chat_completion` produces a plain-language equivalency recommendation
   citing that coursework. The question, answer, and cited chunk ids are saved as
   an `EquivalencyQuery` row.

## Architecture: what's real vs. stubbed

Every one of the five integrations below lives in `backend/apps/common/` as a
dual-path module with identical function signatures in either mode, so nothing
else in the app needs to know which mode is active:

- **Blob storage** (`blob_store.py`) - real Azure Blob Storage via
  `azure-storage-blob` when `AZURE_STORAGE_CONNECTION_STRING` is set; otherwise
  files are written to/read from `media/blob_stub/<container>/` on local disk.
- **Document extraction** (`document_intelligence.py`) - real Azure Document
  Intelligence (`prebuilt-document`, or ideally a custom-trained transcript model
  in production) when the endpoint+key are set; otherwise a deterministic stub
  parses the uploaded text directly (`Course | Grade | Term` per line) into
  structured rows, seeding any line it can't parse cleanly from a SHA256 hash so
  results stay reproducible.
- **AI chat completions** (`ai.py`) - real Azure OpenAI chat (model
  `OPENAI_CHAT_MODEL`, default `gpt-5.4-mini`) when Azure OpenAI credentials are
  set; otherwise a deterministic stub reply built from a SHA256 hash of the
  prompt.
- **AI embeddings** (`ai.py`) - real Azure OpenAI embeddings (model
  `OPENAI_EMBEDDING_MODEL`, default `text-embedding-3-large`, 1536 dimensions)
  when configured; otherwise a deterministic SHA256-seeded 1536-float vector
  (same text always yields the same vector).
- **Vector/hybrid search** (`search_store.py`) - real Azure AI Search index
  (`credential_chunks`) when `AZURE_SEARCH_ENDPOINT`/`AZURE_SEARCH_KEY` are set;
  otherwise an in-process, in-memory list of `{id, vector, payload}` per index
  name with plain-Python cosine-similarity top-k search (no external deps, no
  persistence beyond the current process - like Qdrant's `:memory:` mode). A
  small self-heal (`services.ensure_index_populated`) rebuilds this in-memory
  index from already-processed `CredentialChunk` rows if a fresh process starts
  with it empty.

Postgres itself is always plain relational - vectors never live in Postgres
columns, only in the `search_store` abstraction above.

## Tests

```bash
cd backend
venv\Scripts\python.exe manage.py test
```

38 tests covering: user model + auth API, applicants CRUD + permissions,
credentials CRUD/upload/process/records + permissions, each `apps/common` stub
module in isolation, the credential-processing and equivalency-answer services,
and a full end-to-end pipeline test (upload -> extract -> chunk/embed -> index ->
search -> AI summary) driven entirely through the real HTTP API in stub mode.

## Notable implementation decisions

- Seed data lives in a dedicated `apps/seed_data` app whose single migration
  depends on `users`, `applicants`, `credentials`, and `equivalency`, and uses
  `get_or_create` + `django.contrib.auth.hashers.make_password()` (never
  `set_password()` on a historical model) so it's safe to run more than once.
- `EquivalencyQuery.credential` is nullable so a question can (in principle) be
  asked across all credentials rather than one in particular; the demo UI always
  scopes to one credential for clarity.
- The in-memory search store is a module-level dict keyed by index name; it is
  intentionally process-local with no persistence, matching the brief's
  ":memory:"-style fallback requirement.
