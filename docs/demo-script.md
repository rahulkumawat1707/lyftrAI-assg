# 2–3 minute demo outline (record with your own voice)

Record only after both public URLs are deployed and verified. Keep `.env`, API keys, account settings and private browser tabs out of the recording.

- **0:00–0:20** Open the deployed frontend. “This is Lyftr Chat, built with React, FastAPI, SQLite and LiteLLM. Each reply shows how it was resolved, its model, latency and per-request token usage.”
- **0:20–0:45** Send “My name is Ada. Remember that.” Then “What is my name?” Explain that only the new message is sent by the client; the backend restores session history from SQLite.
- **0:45–1:10** Start a new conversation and send a unique factual question. Start another conversation and send exactly the same question. Show LIVE_INFERENCE then LLM_CACHE, identical reply/usage and lower latency.
- **1:10–1:40** Open settings, enable key_1=429, and send a fresh question. Show key_2 and one fallback. Explain the corresponding X-Simulate-Failure header. Repeat key_1=500 if time allows.
- **1:40–2:05** Enable all-keys failure and send a new question. Show the readable error. Use the history endpoint or verification output to show the failed turn was not saved. Reset simulation.
- **2:05–2:35** Show public GET /health, POST /chat and GET /sessions/{session_id}/messages responses. Show the public GitHub repository and Docker Compose volume configuration. “SQLite persists at /data/app.db. The key pool and all configuration use environment variables.”

Keep the final recording between 2 and 3 minutes and make its link publicly accessible without sign-in. This outline is not itself the required video.
