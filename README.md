# Lyftr Chat

React chat with a FastAPI backend, LiteLLM key failover and in-memory response caching, and SQLite session history.

## 1. Live URLs

Public source repository: [rahulkumawat1707/lyftrAI-assg](https://github.com/rahulkumawat1707/lyftrAI-assg).

Add the public frontend URL, backend base URL, and demo recording URL to your assignment submission. Local addresses below are for development and do not replace public deployment URLs.

Local frontend: http://127.0.0.1:3000

Local backend health: http://127.0.0.1:8000/health

If `localhost` times out on your machine, use the numeric `127.0.0.1` URLs above.

## 2. Run locally: with Docker and without

Copy `.env.example` to `.env` and set two distinct real API keys and an available LiteLLM model name. Never commit `.env`. If `.env` already contains your keys, keep that file instead of overwriting it.

### Docker

Install Docker and Make, then run:

```sh
make up
```

Frontend: http://localhost:3000; backend: http://localhost:8000. `make down` stops both services while preserving the named `sqlite_data` volume mounted at `/data`. Both images use multi-stage builds. Without Make, use `docker compose up --build -d` and `docker compose down`.

### Without Docker (Windows PowerShell)

```powershell
git clone https://github.com/rahulkumawat1707/lyftrAI-assg.git
cd lyftrAI-assg
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

If you already have the project open, skip the clone and directory-change commands. Configure `.env` before starting the servers.

The frontend reads `VITE_API_BASE_URL` from the root `.env` at build/start time. Restart Vite after changing it. Backend environment changes also require a restart. Set `ALLOWED_ORIGINS` to include every frontend origin you use, including `http://127.0.0.1:3000` when using the numeric address.

### Configuration

| Variable | Purpose |
| --- | --- |
| `LLM_API_KEYS` | Comma-separated provider keys, at least two; assigned IDs `key_1`, `key_2`, etc. |
| `LLM_MODEL` | LiteLLM model identifier supported by your provider account |
| `DATABASE_URL` | SQLite URL; use `sqlite:////data/app.db` inside Docker |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins permitted by CORS |
| `ENABLE_FAILURE_SIMULATION` | Set `true` to enable the request-scoped failover test header |
| `DEFAULT_SYSTEM_PROMPT` | Default assistant instructions when no session override is supplied |
| `LLM_TIMEOUT_SECONDS` | Timeout for a provider attempt |
| `CACHE_TTL_SECONDS` | Lifetime of a cached response in seconds |
| `VITE_API_BASE_URL` | Backend base URL embedded in the React build; contains no API keys |

The backend container also honors the host-provided `PORT`, defaulting to `8000`.

### Publish to GitHub

To publish further changes to the existing repository, run from the project root:

```powershell
git add README.md
git commit -m "Update project documentation"
git push origin main
```

Stage other intended source files explicitly when publishing code changes. Git Credential Manager may open your browser to sign in. `.gitignore` excludes API keys in `.env`, the local database, dependencies, and generated output.

### Public deployment

Deploy `backend/Dockerfile` to a Python/container host with backend root directory `backend`. Attach a persistent disk at `/data`, set `DATABASE_URL=sqlite:////data/app.db`, and set every backend environment variable from `.env.example`. Use one backend worker because session locks and LiteLLM's cache are process-local. Set the health path to `/health` and enable failure simulation. Set `ALLOWED_ORIGINS` to the public frontend origin.

Deploy the frontend as a static site with root directory `frontend`, build command `npm ci && npm run build`, and publish directory `dist`. Set `VITE_API_BASE_URL` to the public HTTPS backend URL **before building**. It is embedded into the frontend bundle; API keys must never use a `VITE_` prefix. Configure the host to serve `index.html` for frontend routes.

Use a host with persistent disk support: an ephemeral filesystem does not preserve SQLite history across container replacement. Review hosting account requirements, storage allowances, and costs before provisioning.

### Vercel frontend settings

Import `rahulkumawat1707/lyftrAI-assg` into Vercel with **Root Directory `frontend`** and **Framework Preset Vite**. The included `frontend/vercel.json` sets `npm ci`, `npm run build`, output directory `dist`, and the SPA fallback.

Set `VITE_API_BASE_URL` to your public HTTPS FastAPI backend base URL when it is available, then redeploy. Do not enter API keys in the frontend environment. A production build without a backend URL still renders the interface and displays a readable message when chat is attempted. It does not connect to a visitor's localhost.

Use the project's public production domain for the submission frontend URL. Verify it opens without signing in. Add that exact origin to the backend's `ALLOWED_ORIGINS` before testing chat from Vercel.

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

The contract tests exercise the actual LiteLLM Router and Cache with mocked provider responses; they do not establish that real provider credentials work. `scripts/check_provider.py` tests real keys separately and prints redacted provider diagnostics. Real inference verification uses your provider quota.

```powershell
.\.venv\Scripts\python scripts/check_provider.py
npm.cmd run build --prefix frontend
```

Run these commands from the repository root. Check that your selected model is available to your account.

For manual checks, use a fresh unique message for each failure test so a prior cache hit does not bypass inference. With `ENABLE_FAILURE_SIMULATION=true`, `X-Simulate-Failure: key_1=429` and `key_1=500` must return key_2 with one fallback. `*=429` must return 503 with `{"detail":"all providers unavailable"}` and add no history. Simulations are request-local. Supported statuses are 429, 500, 502, 503; 5xx simulations use LiteLLM's built-in internal-server-error mock.

Send the same first question in two new sessions: the second should say `LLM_CACHE`, retain the same reply and token usage, and be faster. A different question or system prompt must miss. Ask a follow-up to verify history is included. Inspect the history endpoint to confirm oldest-first user/assistant pairs and no system messages. Input tokens count this request's full prompt; output tokens count only this reply. Neither value is a running total.

The UI supplies all required `data-testid` hooks and shows source, model, latency, input/output tokens, successful key ID and fallback attempts next to each assistant message. Its settings include optional system prompts, failure-test controls, and history reload.

### Endpoint checks

```sh
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"session_id":"demo-one","message":"What is the capital of France?"}'
curl http://localhost:8000/sessions/demo-one/messages
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d '{"session_id":"demo-fallback","message":"Explain Python in one sentence. Reference demo-fallback."}'
```

These examples use a POSIX shell. In PowerShell, use `Invoke-RestMethod` or `curl.exe` with the appropriate JSON quoting. For deployment verification, replace the local backend address with the public backend base URL.

The `POST /chat` body accepts `session_id` (1–128 characters), `message` (1–4000 characters after trimming), and optional `system_prompt`. A successful response contains `session_id`, non-empty `reply`, and `metadata`: `resolution_source`, `model`, `latency_ms`, `input_tokens`, `output_tokens`, `key_id`, and `fallback_attempts`. Invalid input or malformed JSON returns 422; an unknown history session returns 404; provider exhaustion returns 503. Errors contain `detail`.

Use `scripts/verify_live.py --backend YOUR_BACKEND_URL --frontend YOUR_FRONTEND_URL` with the virtual-environment Python interpreter to run live acceptance checks. After saving a successful conversation, restart the backend and fetch its history again to verify persistence independently of the in-memory cache.

## 5. Setup Used: your editor and AI tools

Editor: **Visual Studio Code**. AI coding assistant: **OpenAI Codex**, used for implementation, documentation, dependency setup, and contract testing. The assignment PDF was extracted and rendered locally for review. Provider calls use LiteLLM; simulated failures affect the selected keys while successful fallback replies still come from a real provider.

## 6. Bonus features (if any): what you added beyond the requirements and why

- Markdown replies with code blocks and tables, plus copy controls for readability.
- Session settings and conversation switching for trying distinct contexts.
- Visible backend connectivity and resilience controls to make debugging/demo steps repeatable.
- A Windows background start script to keep the local preview available between terminal sessions.

### Assignment submission checklist

Submit the following through the assignment's Submission Form within **24 hours of receiving the assignment**:

- **Public frontend URL:** the React application must be accessible without login and connected to the deployed backend.
- **Public backend base URL:** the running FastAPI service must expose `GET /health`, `POST /chat`, and `GET /sessions/{session_id}/messages`, with CORS allowing the frontend origin.
- **Public GitHub repository URL:** include `/backend`, `/frontend`, `docker-compose.yml`, `Makefile` with `up` and `down`, `.env.example` containing placeholders, this README, backend tests, and multi-stage Dockerfiles for both services. Never submit real keys in source.
- **A 2–3 minute screen recording with your own voice:** show the deployed app, multi-turn conversation, all three endpoints, the per-request metadata, a cache hit, and key failover using `X-Simulate-Failure`. Make the video link accessible without login. See [the recording outline](docs/demo-script.md).

Both deployed tiers must be connected and testable. Localhost addresses and the GitHub source URL do not replace the mandatory live frontend/backend URLs. SQLite must live on a persistent volume, and failure simulation must be enabled on the deployed backend.
