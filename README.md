# Lyftr Chat

React chat with a FastAPI backend, LiteLLM key failover and in-memory response caching, and SQLite session history.

## 1. Live URLs

Public frontend, backend, repository, and demo URLs are pending deployment.

Local frontend: http://127.0.0.1:3000

Local backend health: http://127.0.0.1:8000/health

If `localhost` times out on your machine, use the numeric `127.0.0.1` URLs above.

## 2. Run locally: with Docker and without

Copy `.env.example` to `.env` and set two distinct real API keys and an available LiteLLM model name. Never commit `.env`.

### Docker

Install Docker and Make, then run `make up`. Frontend: http://localhost:3000; backend: http://localhost:8000. `make down` stops both services while preserving the named `sqlite_data` volume. Both images use multi-stage builds. Docker builds have not yet been verified on this workstation because Docker is unavailable.

### Without Docker (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
npm.cmd ci --prefix frontend
.\scripts\start-local.ps1
```

The restart script launches hidden background servers that outlive the terminal command. If ports are already in use, it leaves existing processes running. Logs are in `tmp/`. To stop an owned server, stop its process ID shown in `Get-NetTCPConnection -LocalPort 3000,8000`.

Alternatively run each server in its own terminal from the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm.cmd run dev --prefix frontend -- --host 127.0.0.1
```

The frontend reads `VITE_API_BASE_URL` from the root `.env` at build/start time. Restart Vite after changing it. Backend environment changes also require a restart. Set `ALLOWED_ORIGINS` to include every frontend origin you use, including `http://127.0.0.1:3000` when using the numeric address.

### Publish to GitHub

1. Sign in to GitHub and create a **public**, empty repository named `lyftr-ai-chat`. Leave the README, license and gitignore options unchecked because the local project supplies its own files.
2. From `C:\Lyftr AI`, run:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/lyftr-ai-chat.git
git push -u origin main
```

Git Credential Manager may open your browser to sign in. Complete authentication yourself. If `origin` already exists, inspect it with `git remote -v` before changing it.

The local repository should already have its initial commit. If copying this source without its `.git` directory, initialize it first:

```powershell
git init -b main
git add .
git commit -m "Build Lyftr React and FastAPI chat application"
```

### Public deployment

Deploy `backend/Dockerfile` to a Python/container host with backend root directory `backend`. Attach a persistent disk at `/data`, set `DATABASE_URL=sqlite:////data/app.db`, and set every backend environment variable from `.env.example`. Use one backend worker because session locks and LiteLLM's cache are process-local. Set the health path to `/health` and enable failure simulation. Set `ALLOWED_ORIGINS` to the public frontend origin.

Deploy the frontend as a static site with root directory `frontend`, build command `npm ci && npm run build`, and publish directory `dist`. Set `VITE_API_BASE_URL` to the public HTTPS backend URL **before building**. It is embedded into the frontend bundle; API keys must never use a `VITE_` prefix. Configure the host to serve `index.html` for frontend routes.

Render persistent disks require a paid service; a free ephemeral filesystem does not satisfy restart persistence. Confirm any hosting costs before provisioning.

## 3. Design decisions: key fallback, caching, SQLite session storage

- Each key becomes an ordered LiteLLM Router deployment named `key_1`, `key_2`, etc. Router performs fallback with no same-key retries. A request-scoped router avoids simulation/cooldown state leaking to subsequent requests. The public metadata includes only key IDs, never secrets.
- LiteLLM's built-in local Cache stores the reply and original usage under model + the complete ordered messages, including system prompt and history. Session IDs do not affect cache identity. Cache hits return identical reply/usage, null key ID, and zero fallback attempts. The cache lasts until its TTL or process restart; SQLite history persists independently.
- SQLite creates its own schema and uses WAL. Both messages and the session system prompt are committed together only after successful inference. Validation and provider failures leave history unchanged.
- Per-session locks serialize simultaneous requests in one backend worker. Different sessions can run concurrently. Deploy exactly one backend worker/instance with the SQLite volume.
- The client sends only the new message. A new session begins on each page load; optional new-conversation controls retain earlier conversations only during that page visit. Session IDs are random UUIDs, not authentication credentials. This assignment implementation does not provide account-based access control.
- Exact API routes: `GET /health`, `POST /chat`, `GET /sessions/{session_id}/messages`. Errors have a JSON `detail` field. Health checks database access and key configuration; it does not spend tokens to validate credentials.

## 4. Verification: how to see failover, cache hits and per-message token usage

Run the backend test suite from the root:

```powershell
cd backend
..\.venv\Scripts\python -m pytest -q
```

The contract tests exercise the actual LiteLLM Router and Cache with mocked provider responses; they do not establish that real provider credentials work. `scripts/check_provider.py` tests real keys separately and prints only safe diagnostics.

For manual checks, use a fresh unique message for each failure test so a prior cache hit does not bypass inference. With `ENABLE_FAILURE_SIMULATION=true`, `X-Simulate-Failure: key_1=429` and `key_1=500` must return key_2 with one fallback. `*=429` must return 503 with `{"detail":"all providers unavailable"}` and add no history. Simulations are request-local. Supported statuses are 429, 500, 502, 503; 5xx simulations use LiteLLM's built-in internal-server-error mock.

Send the same first question in two new sessions: the second should say `LLM_CACHE`, retain the same reply and token usage, and be faster. A different question or system prompt must miss. Ask a follow-up to verify history is included. Inspect the history endpoint to confirm oldest-first user/assistant pairs and no system messages. Input tokens count this request's full prompt; output tokens count only this reply. Neither value is a running total.

The UI supplies all required `data-testid` hooks and shows source, model, latency, input/output tokens, successful key ID and fallback attempts next to each assistant message. Its settings include optional system prompts, failure-test controls, and history reload.

## 5. Setup Used: your editor and AI tools

VS Code with OpenAI Codex for implementation, dependency installation, and contract testing. The provided assignment PDF was extracted and rendered locally for review. No generated provider answer is presented as live inference in production.

## 6. Bonus features (if any): what you added beyond the requirements and why

- Markdown replies with code blocks and tables, plus copy controls for readability.
- Session settings and conversation switching for trying distinct contexts.
- Visible backend connectivity and resilience controls to make debugging/demo steps repeatable.
- A Windows background start script to keep the local preview available between terminal sessions.

### Submission status

Backend contract tests and frontend production build have passed. Public deployment, a public GitHub remote, and the narrated 2–3 minute recording still require completion. See `docs/demo-script.md` for a recording outline.
