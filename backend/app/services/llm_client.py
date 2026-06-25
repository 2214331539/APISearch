from __future__ import annotations

import json
from typing import Any, Dict

import httpx


class GeminiClient:
    """Minimal client for a Gemini-compatible ``:generateContent`` endpoint.

    The configured proxy mirrors Google's generativelanguage REST shape:
    ``{base_url}/models/{model}:generateContent?key=...`` and returns the answer
    at ``candidates[0].content.parts[0].text``.
    """

    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def generate_json(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Call the model with JSON-mode output and return the parsed object."""
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0,
            },
        }
        response = httpx.post(
            url, params={"key": self.api_key}, json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
