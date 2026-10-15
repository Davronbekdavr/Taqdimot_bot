"""Structured multilingual content generation using the OpenAI Responses API."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LANGUAGE_NAMES = {"uz": "Uzbek", "en": "English", "ru": "Russian", "tr": "Turkish"}


class ContentError(RuntimeError):
    pass


def content_schema(kind: str) -> dict:
    text = {"type": "string"}
    if kind == "presentation":
        return {
            "type": "object", "additionalProperties": False,
            "properties": {
                "title": text,
                "slides": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "properties": {"title": text, "bullets": {"type": "array", "items": text}, "speaker_notes": text},
                    "required": ["title", "bullets", "speaker_notes"]}},
                "sources": {"type": "array", "items": text},
            }, "required": ["title", "slides", "sources"],
        }
    if kind == "tests":
        return {"type":"object","additionalProperties":False,"properties":{
            "title":text,"questions":{"type":"array","items":{"type":"object","additionalProperties":False,
                "properties":{"question":text,"options":{"type":"array","items":text},"answer":text,"explanation":text},
                "required":["question","options","answer","explanation"]}},
        },"required":["title","questions"]}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "title": text, "introduction": text,
            "chapters": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "properties": {"heading": text, "body": text}, "required": ["heading", "body"]}},
            "conclusion": text, "bibliography": {"type": "array", "items": text},
        }, "required": ["title", "introduction", "chapters", "conclusion", "bibliography"],
    }


class OpenAIContentGenerator:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 180):
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.timeout = timeout

    def generate(self, *, kind: str, topic: str, language: str, size: int,
                 font_size: int = 14, education_level: str = "", cover_details: str = "",
                 design: str = "modern", page_scope: str = "main",
                 revision_feedback: str = "", existing_material: dict | None = None) -> tuple[dict, int | None]:
        if not self.api_key:
            raise ContentError("missing_api_key")
        language_name = LANGUAGE_NAMES[language]
        if kind == "presentation":
            instructions = (
                f"Create exactly {size} presentation slides about the topic. Write consistently in {language_name}. "
                "Keep slides concise: one title, 3–6 clear bullets, and useful speaker notes each. Create a narrative "
                "opening and conclusion within the requested slide count. Add only sources you actually verified; "
                "never invent titles, authors, publishers, URLs, or statistics. Return an empty sources list if none were verified."
            )
            max_tokens = min(12000, max(3000, size * 450))
            use_web = True
        elif kind == "tests":
            instructions=(f"Write 10 original multiple-choice questions in {language_name} about {topic}. Each must have four answer options, one correct answer, and a short explanation. Do not add unsupported factual claims.")
            max_tokens=7000; use_web=True
        else:
            size_description = f"Target {size} pages, {font_size} pt body text" + (" for main body only" if page_scope == "main" else " for the whole document including cover and contents")
            instructions = (
                f"Write a coherent academic paper in {language_name}. Topic: {topic}. {size_description}; education level: {education_level or 'unspecified'}. "
                f"Optional cover-page details supplied by user: {cover_details or 'none'}. Include a meaningful introduction, 2–5 logically organized chapters, a conclusion, and bibliography. "
                "Do not invent any institution, student details, sources, authors, DOIs, or URLs. Use web search to verify sources before placing them in bibliography; "
                "if verification is unavailable, return an empty bibliography and clearly avoid fabricated citations. Do not pad with unrelated or repeated text."
            )
            max_tokens = min(20000, max(5000, size * 900))
            use_web = True
            if revision_feedback:
                instructions += " Revision request based on a real page render: " + revision_feedback + ". Keep the requested font size and academic structure unchanged; revise relevant content only."
        request_text=f"Create material on this topic: {topic}"
        if existing_material is not None:
            request_text += "\nRevise this existing JSON material and preserve its topic and factual meaning:\n" + json.dumps(existing_material,ensure_ascii=False)
        body = {
            "model": self.model,
            "instructions": instructions,
            "input": [{"role": "user", "content": request_text}],
            "max_output_tokens": max_tokens,
            "text": {"format": {"type": "json_schema", "name": "studio_material", "strict": True, "schema": content_schema(kind)}},
        }
        if use_web:
            body["tools"] = [{"type": "web_search"}]
            body["include"] = ["web_search_call.action.sources"]
        request = Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode("utf-8"), headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
        }, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read(1200).decode("utf-8", errors="replace")
            raise ContentError(f"provider_http_{exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ContentError(f"provider_unavailable: {type(exc).__name__}") from exc
        chunks = []; verified_urls=[]
        for item in result.get("output", []):
            if item.get("type")=="web_search_call":
                for source in item.get("action",{}).get("sources",[]):
                    if source.get("url"): verified_urls.append(source["url"])
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        chunks.append(part.get("text", ""))
                    elif part.get("type") == "refusal":
                        raise ContentError("generation_refused")
        if not chunks:
            raise ContentError("empty_model_response")
        try:
            data = json.loads("\n".join(chunks))
        except json.JSONDecodeError as exc:
            raise ContentError("invalid_structured_response") from exc
        if kind == "presentation" and len(data.get("slides", [])) != size:
            raise ContentError("slide_count_mismatch")
        if kind == "tests" and len(data.get("questions", [])) != 10:
            raise ContentError("question_count_mismatch")
        if kind not in {"presentation","tests"} and not data.get("chapters"):
            raise ContentError("empty_paper")
        # Keep bibliography items only when their URL appeared in a provider-returned web result.
        if "bibliography" in data:
            data["bibliography"]=[item for item in data["bibliography"] if any(url in item for url in verified_urls)]
        if "sources" in data:
            data["sources"]=[item for item in data["sources"] if any(url in item for url in verified_urls)]
        return data, (result.get("usage") or {}).get("total_tokens")
