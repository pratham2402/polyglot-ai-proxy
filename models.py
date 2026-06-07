from pydantic import BaseModel


class DubRequest(BaseModel):
    text: str
    target_languages: list[str]


class LanguageResult(BaseModel):
    translated_text: str
    audio_base64: str


class DubResponse(BaseModel):
    status: str
    results: dict[str, LanguageResult]
