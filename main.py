import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from models import DubRequest, DubResponse, LanguageResult
from services import translate_text, generate_tts, APIError

app = FastAPI(title="polyglot-ai-proxy")


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": str(exc)},
    )


@app.post("/v1/dub", response_model=DubResponse)
async def dub_endpoint(body: DubRequest):
    lang_count = len(body.target_languages)

    # Phase 1: concurrent translation across all target languages
    translations = await asyncio.gather(
        *[translate_text(body.text, lang) for lang in body.target_languages]
    )

    # Phase 2: concurrent TTS for all translated strings
    audio_results = await asyncio.gather(
        *[
            generate_tts(translated, lang)
            for translated, lang in zip(translations, body.target_languages)
        ]
    )

    results = {
        lang: LanguageResult(
            translated_text=translated,
            audio_base64=audio,
        )
        for lang, translated, audio in zip(
            body.target_languages, translations, audio_results
        )
    }

    return DubResponse(status="completed", results=results)
