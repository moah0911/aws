from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class ImageGenerationResult:
    output_path: str
    prompt: str


class GeminiImageService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("VOOC_GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")

    def generate(self, prompt: str, output_path: str, context: str = "") -> ImageGenerationResult:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for image generation")
        if not prompt.strip():
            raise ValueError("Image prompt must not be empty")

        merged_prompt = f"Session context:\n{context}\n\nUser request:\n{prompt}" if context.strip() else prompt
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={urllib.parse.quote(self.api_key)}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": merged_prompt}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }

        req = urllib.request.Request(
            url=endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=60) as response:  # noqa: S310
            raw = response.read().decode("utf-8")

        binary = _extract_image_bytes(raw)
        if not binary:
            raise RuntimeError("Gemini did not return image bytes")

        with open(output_path, "wb") as handle:
            handle.write(binary)

        return ImageGenerationResult(output_path=output_path, prompt=prompt)


def _extract_image_bytes(raw_json: str) -> bytes:
    parsed = json.loads(raw_json)
    for candidate in parsed.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    return b""
