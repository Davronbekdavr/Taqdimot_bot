"""Presentation generation through Google's Gemini generateContent REST API."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.services.content import ContentError, LANGUAGE_NAMES


class GeminiPresentationGenerator:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 180):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.timeout = timeout

    def generate(self, *, kind: str, topic: str, language: str, size: int, **_ignored) -> tuple[dict, int | None]:
        if kind != "presentation":
            raise ContentError("gemini_supports_presentations_only")
        if not self.api_key:
            raise ContentError("missing_gemini_api_key")

        language_name = LANGUAGE_NAMES[language]
        prompt = (
            f"Create a polished educational presentation about: {topic}. Write in {language_name}. "
            f"Return valid JSON only, with this exact structure: {{\"title\": string, \"slides\": "
            "[{\"title\": string, \"bullets\": [string], \"speaker_notes\": string}], \"sources\": []}. "
            f"Produce exactly {size} slides. Each slide needs 3 to 6 concise, informative bullets and useful speaker notes. "
            "Arrange ideas in a clear story with an opening and conclusion inside those slides. "
            "Do not invent references or URLs; always return an empty sources array."
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": min(12000, max(3000, size * 450)),
            },
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Avoid sending provider diagnostics back to users or logs with sensitive request data.
            raise ContentError(f"gemini_http_{exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ContentError(f"gemini_unavailable: {type(exc).__name__}") from exc

        candidates = result.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text:
            raise ContentError("empty_gemini_response")
        try:
            material = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ContentError("invalid_gemini_json") from exc
        slides = material.get("slides") if isinstance(material, dict) else None
        if not isinstance(slides, list) or len(slides) != size:
            raise ContentError("slide_count_mismatch")
        for slide in slides:
            if not isinstance(slide, dict) or not isinstance(slide.get("title"), str) or not isinstance(slide.get("bullets"), list) or not isinstance(slide.get("speaker_notes"), str):
                raise ContentError("invalid_gemini_slide")
        material["sources"] = []  # Gemini response is not search-grounded in this simple API integration.
        usage = result.get("usageMetadata") or {}
        tokens = usage.get("totalTokenCount")
        return material, (int(tokens) if tokens is not None else None)
