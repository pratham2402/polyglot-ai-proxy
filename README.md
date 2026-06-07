# polyglot-ai-proxy

Concurrent translation and text-to-speech orchestration proxy built with FastAPI.

## How it works

1. Accepts text and a list of target languages via `POST /v1/dub`
2. Translates the text into all target languages concurrently using the DeepSeek API
3. Generates TTS audio for each translation concurrently using the ElevenLabs API
4. Returns the translated text and base64-encoded audio in a single JSON response

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
- `services.py` — Async API connectors with exponential backoff retry
- `main.py` — FastAPI app and concurrent orchestration via `asyncio.gather`
- `Dockerfile` — Single-stage container build
