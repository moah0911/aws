from __future__ import annotations

import base64
import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass
class VoiceSynthesisResult:
    provider: str
    output_path: str
    preview_text: str


class VibeVoiceService:
    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("VIBEVOICE_URL", "http://127.0.0.1:5005/synthesize")

    def synthesize(self, text: str, output_path: str) -> VoiceSynthesisResult:
        if not text.strip():
            raise ValueError("Text must not be empty for voice synthesis")

        payload = json.dumps({"text": text, "format": "wav", "voice": "en-US-VibeVoice"}).encode("utf-8")
        req = urllib.request.Request(
            url=self.endpoint,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=15) as response:  # noqa: S310
            content_type = response.headers.get("content-type", "")
            raw = response.read()

        if "application/json" in content_type:
            parsed = json.loads(raw.decode("utf-8"))
            b64 = parsed.get("audioBase64", "")
            if not b64:
                raise RuntimeError("VibeVoice JSON response did not contain audioBase64")
            binary = base64.b64decode(b64)
        else:
            binary = raw

        if not binary:
            raise RuntimeError("VibeVoice returned an empty audio payload")

        with open(output_path, "wb") as handle:
            handle.write(binary)

        return VoiceSynthesisResult(
            provider="microsoft-vibevoice",
            output_path=output_path,
            preview_text=text[:160],
        )
