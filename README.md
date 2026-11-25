# Lyftr AI — LLM Chatbot with Key Failover and Response Caching

A full-stack conversational AI application built with React, FastAPI, LiteLLM and SQLite. It demonstrates multi-turn session memory, provider-key failover, response caching, per-request token metadata and containerized deployment.

## 1. Live URLs

- Frontend: _Add deployed frontend URL_
- Backend: _Add deployed backend URL_
- Health: `<backend-url>/health`
- API docs: `<backend-url>/docs`

## 2. Run locally: with Docker and without

### Prerequisites

- Docker Desktop and Docker Compose, or Python 3.11+ and Node.js 20+
- An OpenAI API key and a Gemini API key

### Docker

```bash
# Windows PowerShell:
Copy-Item .env.example .env
# Edit .env and add your real OpenAI and Gemini API keys. Never share or commit .env.
docker compose up -d --build

docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Open the frontend at http://localhost:3000 and API docs at http://localhost:8000/docs.

Stop the stack:

```bash
docker compose down
```

The named `app_data` volume persists the SQLite database and LiteLLM disk cache. The backend container runs as root so it can initialize the mounted named volume on Windows Docker Desktop; the data directory is created with write permissions during image build.

### Without Docker

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Set OPENAI_API_KEY, GEMINI_API_KEY, DATABASE_URL=sqlite:///./app.db and other variables
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
# Optional: set VITE_API_URL=http://localhost:8000 in frontend/.env
npm run dev -- --port 3000
```

## 3. Design decisions: key fallback, caching, SQLite session storage

- **Key fallback:** OpenAI (`OPENAI_API_KEY`) is the primary provider and Gemini (`GEMINI_API_KEY`) is the fallback provider and assigned stable display identifiers (`key_1`, `key_2`, ...). A failed provider attempt moves to the next key. Provider secrets are never returned to the browser.
- **Failure simulation:** `X-Simulate-Failure` is honored only when `ENABLE_FAILURE_SIMULATION=true`. It accepts comma-separated key/status pairs, including `*=429`, and is scoped to one request.
- **Caching:** LiteLLM disk caching is enabled. A deterministic application response cache also makes exact prompt cache hits explicit and returns the original response and token usage. The cache key is based on model and the complete ordered message list, not the session ID.
- **Session history:** SQLite stores user and assistant messages in order. Only the new user message is sent by the browser; the backend reconstructs context from persisted history.
- **Persistence:** Docker Compose mounts a named volume at `/data`; configure `DATABASE_URL=sqlite:////data/app.db`.
- **Metadata:** every assistant message includes source, model, latency, input/output token usage, key identifier and fallback attempt count.

## 4. Verification: how to see failover, cache hits and per-message token usage

### Health

```bash
curl http://localhost:8000/health
```

Expected shape:

```json
{"status":"ok","keys_configured":2,"cache_enabled":true}
```

### Live response and cache hit

Send the same first message with two different session IDs. The second identical request should be marked `LLM_CACHE`.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-a","message":"Explain API caching in one sentence."}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-b","message":"Explain API caching in one sentence."}'
```

### Failover

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id":"demo-fallback","message":"Give me a short welcome message."}'
```

Expected: HTTP 200, `key_id` is `key_2`, and `fallback_attempts` is `1` (assuming both provider keys are configured and the request is a cache miss).

### All providers unavailable

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id":"demo-outage","message":"This request should fail cleanly."}'
```

Expected: HTTP 503 and `{"detail":"all providers unavailable"}`. The failed request is not stored in message history.

### History and per-message tokens

```bash
curl http://localhost:8000/sessions/demo-a/messages
```

Each assistant message contains its own metadata; token counts are not conversation totals.

## 5. Setup Used

- Editor: _Fill in the editor you used_
- AI tools: _List the tools you used_
- Frontend: React 18, Vite, Tailwind CSS
- Backend: Python, FastAPI, SQLAlchemy
- LLM gateway: LiteLLM
- Storage: SQLite
- Tests: Pytest and FastAPI TestClient
- Containers: Docker, Docker Compose

## 6. Bonus features (if any): what you added beyond the requirements and why

- Session-specific system prompt support.
- API connection status in the interface.
- Expandable per-response diagnostics including key identifier and fallback attempts.
- Suggested prompts for a more welcoming first-use experience.
- A compact request metadata panel designed to make caching and failover observable.

## Environment variables

See `.env.example`. Real API keys must stay in local/deployment secrets and must never be committed.

## Important implementation note

The in-process response cache is intentionally simple for this single-instance assignment deployment. For multiple backend replicas, replace it with a shared cache while retaining LiteLLM's configured cache backend and the same model-plus-messages cache key semantics.
