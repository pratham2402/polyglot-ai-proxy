# polyglot-ai-proxy

[![forthebadge](data:image/svg+xml;base64,PHN2ZyBkYXRhLXYtODY1ODNhZmQ9IiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB3aWR0aD0iMTkxLjE2NjY2NzkzODIzMjQyIiBoZWlnaHQ9IjM1IiB2aWV3Qm94PSIwIDAgMTkxLjE2NjY2NzkzODIzMjQyIDM1IiBjbGFzcz0iYmFkZ2Utc3ZnIj48ZGVmcyBkYXRhLXYtODY1ODNhZmQ9IiI+PCEtLS0tPjwhLS0tLT48IS0tLS0+PC9kZWZzPjxyZWN0IGRhdGEtdi04NjU4M2FmZD0iIiB3aWR0aD0iMTA4LjcxNjY2NzE3NTI5Mjk3IiBoZWlnaHQ9IjM1IiBmaWxsPSIjMzA2OTk4Ii8+PHJlY3QgZGF0YS12LTg2NTgzYWZkPSIiIHg9IjEwOC43MTY2NjcxNzUyOTI5NyIgd2lkdGg9IjgyLjQ1MDAwMDc2MjkzOTQ1IiBoZWlnaHQ9IjM1IiBmaWxsPSIjZmZkNDNiIi8+PCEtLS0tPjx0ZXh0IGRhdGEtdi04NjU4M2FmZD0iIiB4PSI1NC4zNTgzMzM1ODc2NDY0ODQiIHk9IjE3LjUiIGR5PSIwLjM1ZW0iIGZvbnQtc2l6ZT0iMTIiIGZvbnQtZmFtaWx5PSJSb2JvdG8sIHNhbnMtc2VyaWYiIGZpbGw9IiNGRkZGRkYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGxldHRlci1zcGFjaW5nPSIyIiBmb250LXdlaWdodD0iNjAwIiBmb250LXN0eWxlPSJub3JtYWwiIHRleHQtZGVjb3JhdGlvbj0ibm9uZSIgZmlsbC1vcGFjaXR5PSIxIiBmb250LXZhcmlhbnQ9Im5vcm1hbCIgc3R5bGU9InRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7Ij5NQURFIFdJVEg8L3RleHQ+PCEtLS0tPjx0ZXh0IGRhdGEtdi04NjU4M2FmZD0iIiB4PSIxNDkuOTQxNjY3NTU2NzYyNyIgeT0iMTcuNSIgZHk9IjAuMzVlbSIgZm9udC1zaXplPSIxMiIgZm9udC1mYW1pbHk9Ik1vbnRzZXJyYXQsIHNhbnMtc2VyaWYiIGZpbGw9IiNGRkZGRkYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtd2VpZ2h0PSI5MDAiIGxldHRlci1zcGFjaW5nPSIyIiBmb250LXN0eWxlPSJub3JtYWwiIHRleHQtZGVjb3JhdGlvbj0ibm9uZSIgZmlsbC1vcGFjaXR5PSIxIiBmb250LXZhcmlhbnQ9Im5vcm1hbCIgc3R5bGU9InRleHQtdHJhbnNmb3JtOiB1cHBlcmNhc2U7Ij5QWVRIT048L3RleHQ+PCEtLS0tPjwvc3ZnPg==)](https://forthebadge.com)

Concurrent translation and text-to-speech orchestration proxy built with FastAPI.

## How it works

1. Accepts text and a list of target languages via `POST /v1/dub`
2. Translates the text into all target languages concurrently using the DeepSeek API
3. Generates TTS audio for each translation concurrently using the ElevenLabs API
4. Returns the translated text and base64-encoded audio in a single JSON response

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | yes | — | DeepSeek API key |
| `ELEVENLABS_API_KEY` | yes | — | ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | no | `EXAVITQu4vr4xnSDxMaL` | ElevenLabs voice ID (Bella) |

## Setup

```bash
cp .env.example .env
# Fill in your DeepSeek and ElevenLabs API keys
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --port 8000
```

## Run with Docker

```bash
docker build -t polyglot-ai-proxy .
docker run -p 8000:8000 --env-file .env polyglot-ai-proxy
```

## API

### `POST /v1/dub`

```json
{
  "text": "Hello, how are you?",
  "target_languages": ["Hindi", "Tamil", "French"]
}
```

Response:

```json
{
  "status": "completed",
  "results": {
    "Hindi": {
      "translated_text": "नमस्ते, आप कैसे हैं?",
      "audio_base64": "..."
    },
    "Tamil": {
      "translated_text": "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?",
      "audio_base64": "..."
    },
    "French": {
      "translated_text": "Bonjour, comment allez-vous ?",
      "audio_base64": "..."
    }
  }
}
```

## Architecture

- `models.py` — Pydantic request/response schemas
- `services.py` — Async API connectors with exponential backoff retry, structured logging, and tenacity retry hooks
- `main.py` — FastAPI app with global `aiohttp.ClientSession` managed via lifespan handler; concurrent orchestration via `asyncio.gather`
- `Dockerfile` — Single-stage container build

### Resilience

Both `translate_text` and `generate_tts` are wrapped with tenacity's `@retry`:
- **Backoff**: Exponential (`wait_exponential`), 2–10s range
- **Attempts**: 3 max (`stop_after_attempt`)
- **Triggers**: HTTP 429, 500, 503
- **Observability**: `before_sleep` hook logs every retry attempt with delay and error detail

### Connection pooling

A single `aiohttp.ClientSession` is created at startup via FastAPI's lifespan handler and shared across all requests — no per-request TCP handshake overhead.
