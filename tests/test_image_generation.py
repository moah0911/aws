import base64
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from vooc.services.image_generation import GeminiImageService


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class ImageGenerationTests(unittest.TestCase):
    def test_extracts_image_bytes_and_saves_file(self) -> None:
        png_stub = base64.b64encode(b"fake-png-bytes").decode("utf-8")
        payload = {
            "candidates": [
                {"content": {"parts": [{"inlineData": {"data": png_stub}}]}},
            ]
        }

        def fake_urlopen(req, timeout=60):  # noqa: ANN001, ARG001
            return _FakeResponse(json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", side_effect=fake_urlopen):
            output_path = os.path.join(tmp, "image.png")
            service = GeminiImageService(api_key="dummy-key")
            result = service.generate("test image", output_path)
            self.assertTrue(os.path.exists(result.output_path))


if __name__ == "__main__":
    unittest.main()
