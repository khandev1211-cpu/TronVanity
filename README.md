# TRON Vanity Address Generator — GPU Server

Production-structured FastAPI service that runs on a GPU instance,
wraps the ProVanity binary, and exposes an authenticated HTTP API for
submitting prefix/suffix generation jobs and polling for results.

## Why this exists

ProVanity's `generate-tron` command only supports **one** pattern at a
time (`prefix:X` OR `suffix:Y`, not both). This server works around
that by running ProVanity in a loop with just the suffix pattern
(GPU-accelerated) and verifying the prefix in Python on each result,
repeating until both match.

## Folder structure

```
gpu-server-v2/
├── app/
│   ├── main.py              # FastAPI app + global exception handlers
│   ├── core/
│   │   ├── config.py         # .env loading + validation (fails fast on bad config)
│   │   └── logging_config.py # Console + rotating file logging
│   ├── api/
│   │   ├── auth.py           # API key verification (constant-time compare)
│   │   └── routes.py         # /generate, /status, /jobs, /health endpoints
│   ├── models/
│   │   └── schemas.py        # Pydantic request/response models + validation
│   └── services/
│       ├── provanity.py      # Subprocess wrapper around the ProVanity binary
│       ├── job_store.py      # Thread-safe job registry, persisted to disk
│       └── worker.py         # Background loop: generate + verify + retry
├── jobs/                      # Job state persisted as JSON (gitignored)
├── logs/                      # Rotating log files (gitignored)
├── run.py                     # Entrypoint
├── start.sh / stop.sh / status.sh
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

```bash
cd gpu-server-v2
pip3 install -r requirements.txt

cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # generate a key
nano .env   # paste it into VANITY_API_KEY=, adjust PROVANITY_BINARY path if needed

chmod +x start.sh stop.sh status.sh
./start.sh
```

If `.env` is missing or invalid (bad key, missing ProVanity binary, binary
not executable, etc.), the server **refuses to start** and prints exactly
what's wrong — it will not silently run in a broken state.

Check it's alive:
```bash
./status.sh
```

Stop it:
```bash
./stop.sh
```

Tail logs:
```bash
tail -f logs/server.log
```

## API Reference

All endpoints except `/health` require header: `X-API-Key: <your key>`

### `POST /generate`
```json
{"prefix": "LaGx", "suffix": "xitv", "case_insensitive": false}
```
→ `201 Created`
```json
{"job_id": "8f14e...", "status": "queued"}
```
Validation errors (e.g. invalid Base58 characters, both fields empty) return
`422` with a clear per-field message.

### `GET /status/{job_id}`
```json
{
  "job_id": "8f14e...",
  "status": "running",
  "prefix": "LaGx",
  "suffix": "xitv",
  "attempts_total": 4188050,
  "elapsed_seconds": 12.4,
  "result": null,
  "error": null
}
```
When done:
```json
{
  "status": "done",
  "result": {
    "address": "TD1uHny8WD6Qxe88MYrbdQzi1UUdT2xitv",
    "private_key": "0x...",
    "offset": "0x..."
  }
}
```
`404` if the job doesn't exist.

### `GET /jobs`
Lists recent jobs, most recent first (capped by `MAX_JOBS_HISTORY`).

### `DELETE /jobs/{job_id}`
Cancels a queued/running job. `400` if it's already finished.

### `GET /health` (no auth required — safe for uptime monitors)
```json
{"status": "ok", "provanity_binary_found": true, "active_jobs": 1}
```

## Error handling summary

| Failure                                   | Behavior                                                        |
|--------------------------------------------|-------------------------------------------------------------------|
| `.env` missing / key too short / binary missing | Server refuses to start, prints exact fix needed                |
| Invalid API key                            | `401 Unauthorized`                                                 |
| Invalid prefix/suffix characters, empty body | `422` with per-field message                                    |
| Job ID doesn't exist                        | `404`                                                              |
| ProVanity subprocess hangs                  | Killed after `PROVANITY_TIMEOUT_SECONDS`, retried with backoff    |
| ProVanity crashes repeatedly                 | Job marked `error` after 10 consecutive failures                 |
| Job runs longer than `MAX_RUNTIME_SECONDS`  | Job marked `error` with a clear message (safety cap)              |
| Server restarts mid-job                     | On restart, any `queued`/`running` job is marked `error` (its worker thread is gone) — resubmit it |
| Any unhandled exception                      | Caught globally, logged with full traceback, client gets a generic `500` (no internal details leaked) |

## Security notes

- API key comparison uses `hmac.compare_digest` (constant-time) to avoid
  timing attacks.
- `.env` is gitignored — never commit it.
- Generated private keys are stored in `jobs/*.json`. Once a client has
  retrieved a result, consider deleting that job's file and moving the
  key to secure storage — this server is not a wallet or key vault.
- This server has no rate limiting or IP allowlisting built in. If
  exposing via ngrok or similar, treat the ngrok URL as sensitive (same
  as the API key) and consider adding a reverse proxy with rate limits
  for production use.

## Running behind ngrok

```bash
ngrok config add-authtoken YOUR_NGROK_TOKEN
ngrok http $(grep -E '^PORT=' .env | cut -d= -f2)
```

Give the printed HTTPS URL + your API key to the client side.
