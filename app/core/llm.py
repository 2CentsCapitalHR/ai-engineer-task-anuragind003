from __future__ import annotations

from typing import Any, List

from app.core.config import get_settings


class LLMClient:
    def generate_json_list(self, prompt: str) -> List[Any]:
        raise NotImplementedError
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        import google.generativeai as genai  # type: ignore

        self._genai = genai
        self._genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def _gen(self, prompt: str) -> str:
        resp = self._model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text

    def generate_json_list(self, prompt: str) -> List[Any]:
        text = self._gen(prompt)
        import json
        import re

        def _try_parse(s: str):
            s = s.strip()
            if not s:
                return []
            try:
                data = json.loads(s)
                # normalize to list
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
                return []
            except Exception:
                return None

        # 1) direct parse
        data = _try_parse(text)
        if isinstance(data, list):
            return data

        # 2) fenced code block ```json ... ``` or ``` ... ```
        m = re.search(r"```json\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
        if not m:
            m = re.search(r"```\s*([\s\S]*?)```", text)
        if m:
            data = _try_parse(m.group(1))
            if isinstance(data, list):
                return data

        # 3) first JSON array/object substring
        # try array
        start = text.find("[")
        end = text.rfind("]")
        if 0 <= start < end:
            data = _try_parse(text[start : end + 1])
            if isinstance(data, list):
                return data
        # try object
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            data = _try_parse(text[start : end + 1])
            if isinstance(data, list):
                return data

        # give up with empty list (caller may fallback)
        return []

    def generate_text(self, prompt: str) -> str:
        return self._gen(prompt)


def get_llm_client() -> LLMClient | None:
    s = get_settings()
    provider = (s.llm_provider or "").lower()
    model = s.llm_model
    try:
        if provider == "gemini" and s.google_api_key:
            return GeminiClient(api_key=s.google_api_key, model=model)
        # Future: add OpenAI, Anthropic, Ollama implementations
    except Exception:
        return None
    return None


