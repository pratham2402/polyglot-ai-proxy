import os
import base64
import aiohttp
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, APIError):
        return exc.status_code in (429, 500, 503)
    return False


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(APIError),
)
async def translate_text(text: str, target_lang: str) -> str:
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
                    "Return only the direct translation with no extra commentary."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DEEPSEEK_URL, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise APIError(
                    f"DeepSeek API returned {resp.status}: {await resp.text()}",
                    status_code=resp.status,
                )
            data = await resp.json()
            return data["choices"][0]["message"]["content"].strip()


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(APIError),
)
async def generate_tts(text: str, lang: str) -> str:
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

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise APIError(
                    f"ElevenLabs API returned {resp.status}: {await resp.text()}",
                    status_code=resp.status,
                )
            audio_bytes = await resp.read()
            return base64.b64encode(audio_bytes).decode("utf-8")
