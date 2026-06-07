# polyglot-ai-proxy

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

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
