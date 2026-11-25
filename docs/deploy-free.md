# Alternative hosting reference

The primary deployment uses Vercel and Railway; see [the README](../README.md) and [Railway settings](deploy-railway.md). This document describes an alternative Northflank setup. Account verification can require a payment card even for its Sandbox plan. Verify account requirements, pricing, and persistent-volume eligibility before selecting an alternative host.

## Backend

1. Create a Northflank account and select Sandbox. Create a project in an available region.
2. Create a combined build/deploy service from the public GitHub repository `https://github.com/rahulkumawat1707/lyftrAI-assg`, branch `main`.
3. Select Dockerfile build, Dockerfile path `/backend/Dockerfile`, build context `/backend`. Use the dashboard's repository-relative path syntax. The Docker build context must contain `requirements.txt` and `app/` directly.
4. Use one instance and the smallest available Sandbox allocation with at least 512 MB RAM (1 GB preferred for LiteLLM if covered by the free allowance). Do not upgrade billing. Check resource and storage estimates against the free allocation.
5. Add an HTTP public port targeting container port `8000`, with HTTPS provided by the host. Use `/health` for a readiness check, allowing sufficient startup time.
6. Attach a persistent **single read/write** volume at `/data`, using the smallest available capacity. The container uses `app:app` (UID/GID 10001) so Northflank can assign volume group permissions. Do not create a managed Postgres/Redis addon.
7. Enter runtime variables below using the host's secret/environment UI. Keep LLM keys out of source and build arguments.

| Variable                  | Value                                             |
| ------------------------- | ------------------------------------------------- |
| LLM_API_KEYS              | The two existing keys, comma-separated            |
| LLM_MODEL                 | An available Gemini model tested with your keys   |
| DATABASE_URL              | `sqlite:////data/app.db`                          |
| ALLOWED_ORIGINS           | `https://lyftr-ai-assg.vercel.app`                |
| ENABLE_FAILURE_SIMULATION | `true`                                            |
| DEFAULT_SYSTEM_PROMPT     | `You are a helpful, clear and concise assistant.` |
| LLM_TIMEOUT_SECONDS       | `25`                                              |
| CACHE_TTL_SECONDS         | `3600`                                            |
| PORT                      | `8000`                                            |

8. Deploy, inspect logs without revealing secrets, and copy the returned public backend URL. A configured key pool can pass health even if the provider is unavailable; test a real chat request separately.

## Frontend

Build the existing React frontend with `VITE_API_BASE_URL` set to the returned public HTTPS backend URL, then publish `frontend/dist` to free static hosting. Do not publish a bundle pointing to `localhost` or `127.0.0.1`. Add the actual frontend origin to the backend's `ALLOWED_ORIGINS` and redeploy the backend if needed.

## Verify before reporting deployment complete

- Frontend and backend URLs work without login.
- Health returns status ok, at least two keys, and cache_enabled true.
- A real message returns a non-empty response with exact metadata fields.
- Same first message in a new session hits cache with identical reply and stored usage.
- Fresh prompts with `key_1=429` and `key_1=500` return a real reply from key_2.
- `*=429` returns the specified JSON 503, adds no history, and does not affect later requests.
- Follow-up messages preserve context and sessions are isolated.
- SQLite history survives restarting the backend container on its mounted volume.
- README lists the verified public frontend and backend URLs.

Run the live acceptance script once the actual backend URL is available:

```powershell
.\.venv\Scripts\python scripts/verify_live.py --backend YOUR_PUBLIC_BACKEND_URL --frontend YOUR_PUBLIC_FRONTEND_URL
```

This makes real LLM requests, verifies cache and fallback behavior, and prints only check results. Restart persistence is a separate check requiring a backend restart.

Hosting allowances do not pay for Gemini usage. Test real inference separately from the health endpoint and select a model supported by your provider account.
