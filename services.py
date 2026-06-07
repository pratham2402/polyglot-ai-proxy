import os
import base64
import logging
import aiohttp
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("polyglot-proxy")

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500, provider: str = "unknown"):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        return exc.status_code in (429, 500, 503)
    return False


def _log_retry_attempt(retry_state):
    logger.warning(
        "retry attempt %d after %.2fs — %s",
        retry_state.attempt_number,
        retry_state.idle_for or 0,
        retry_state.outcome.exception() if retry_state.outcome else "unknown",
    )


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(APIError),
    before_sleep=_log_retry_attempt,
    reraise=True,
)
async def translate_text(session: aiohttp.ClientSession, text: str, target_lang: str) -> str:
    if not DEEPSEEK_KEY:
        raise APIError("DeepSeek API key missing", status_code=500, provider="deepseek")

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"Translate the user's text into {target_lang}. "
                    "Return ONLY the direct translation. No notes, no explanations."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }

    logger.info("translating to %s (%d chars)", target_lang, len(text))
    async with session.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=15.0) as resp:
        if resp.status != 200:
            error_body = await resp.text()
            raise APIError(
                f"DeepSeek returned {resp.status}: {error_body}",
                status_code=resp.status,
                provider="deepseek",
            )
        data = await resp.json()
        translated = data["choices"][0]["message"]["content"].strip()
        logger.info("translation to %s complete", target_lang)
        return translated


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(APIError),
    before_sleep=_log_retry_attempt,
    reraise=True,
)
async def generate_tts(session: aiohttp.ClientSession, text: str) -> str:
    if not ELEVENLABS_KEY:
        raise APIError("ElevenLabs API key missing", status_code=500, provider="elevenlabs")

    url = ELEVENLABS_URL.format(voice_id=VOICE_ID)
    headers = {
        "xi-api-key": ELEVENLABS_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    logger.info("generating TTS (%d chars)", len(text))
    async with session.post(url, json=payload, headers=headers, timeout=30.0) as resp:
        if resp.status != 200:
            error_body = await resp.text()
            raise APIError(
                f"ElevenLabs returned {resp.status}: {error_body}",
                status_code=resp.status,
                provider="elevenlabs",
            )
        audio_bytes = await resp.read()
        logger.info("TTS generation complete (%d bytes)", len(audio_bytes))
        return base64.b64encode(audio_bytes).decode("utf-8")
