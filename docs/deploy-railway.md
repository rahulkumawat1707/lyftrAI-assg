# Railway backend deployment

Use the Free plan or its no-card introductory trial. Do not upgrade to a paid plan for this setup. Verify the account's current allowance and volume eligibility before creating resources. Railway's Free plan documentation lists $1/month of usage, idle sleeping, and one persistent volume capped at 500 MB; exhausting the allowance stops services until the next cycle.

## Service settings

| Setting                 | Value                                |
| ----------------------- | ------------------------------------ |
| Source                  | `rahulkumawat1707/lyftrAI-assg`      |
| Branch                  | `main`                               |
| Root directory          | `/backend`                           |
| Builder                 | Dockerfile                           |
| Dockerfile              | `Dockerfile` within the backend root |
| Instances               | 1                                    |
| Public HTTP target port | 8000                                 |
| Health check            | `/health`                            |
| Persistent volume mount | `/data`                              |

Use the Dockerfile's default start command. Do not add Postgres or Redis: history must stay in SQLite. Configure build settings in the service dashboard/API rather than adding deprecated `railway.toml` or `railway.json` files.

## Runtime variables

| Variable                    | Value                                                                             |
| --------------------------- | --------------------------------------------------------------------------------- |
| `LLM_API_KEYS`              | Two real provider keys, comma-separated; enter using secret settings              |
| `LLM_MODEL`                 | `gemini/gemini-3.5-flash-lite`, or another model verified with both keys          |
| `DATABASE_URL`              | `sqlite:////data/app.db`                                                          |
| `ALLOWED_ORIGINS`           | `https://lyftr-ai-assg.vercel.app`                                                |
| `ENABLE_FAILURE_SIMULATION` | `true`                                                                            |
| `DEFAULT_SYSTEM_PROMPT`     | `You are a helpful, clear and concise assistant.`                                 |
| `LLM_TIMEOUT_SECONDS`       | `25`                                                                              |
| `CACHE_TTL_SECONDS`         | `3600`                                                                            |
| `PORT`                      | `8000`                                                                            |
| `RAILWAY_RUN_UID`           | `0` (Railway documents this for non-root images using root-owned mounted volumes) |

Do not copy real keys into this file, the repository, frontend variables, build arguments, or logs.

## Connect Vercel and verify

1. Generate the backend's Railway public domain and verify unauthenticated `GET /health` returns HTTP 200.
2. Set the Vercel frontend's production `VITE_API_BASE_URL` to that HTTPS base URL. Redeploy the frontend; the value is read at build time.
3. Run `scripts/verify_live.py` against the actual frontend/backend URLs. A healthy server alone does not prove the model provider can answer.
4. Save a successful conversation, restart the backend, and fetch its history again to verify mounted SQLite persistence.
5. Add only verified public URLs to the README and submission form. Keep the backend service within the free allowance.

References: [Free plan](https://docs.railway.com/pricing/free-plan), [volumes](https://docs.railway.com/volumes), [Docker builds](https://docs.railway.com/builds/dockerfiles).
