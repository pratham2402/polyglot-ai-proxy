import asyncio
import logging
import aiohttp
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from models import DubRequest, DubResponse, LanguageResult
from services import translate_text, generate_tts, APIError

logger = logging.getLogger("polyglot-proxy")


class AppState:
    session: aiohttp.ClientSession | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = aiohttp.ClientTimeout(total=45.0)
    state.session = aiohttp.ClientSession(timeout=timeout)
    logger.info("global aiohttp session initialized")
    yield
    await state.session.close()
    logger.info("global aiohttp session closed")


app = FastAPI(title="polyglot-ai-proxy", lifespan=lifespan)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    logger.error("pipeline failure [%s]: %s", exc.provider, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "provider": exc.provider, "detail": str(exc)},
    )


@app.post("/v1/dub", response_model=DubResponse)
async def dub_endpoint(body: DubRequest):
    logger.info("dub request received — %d target languages", len(body.target_languages))

    # Phase 1: concurrent translation across all target languages
    translations = await asyncio.gather(
        *[translate_text(state.session, body.text, lang) for lang in body.target_languages]
    )

    # Phase 2: concurrent TTS for all translated strings
    audio_results = await asyncio.gather(
        *[generate_tts(state.session, translated) for translated in translations]
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

    logger.info("dub workflow complete — %d results", len(results))
    return DubResponse(status="completed", results=results)
