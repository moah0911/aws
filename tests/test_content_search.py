import json
import unittest
from unittest.mock import patch

from vooc.services.content_search import ContentSearchService


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False


class ContentSearchTests(unittest.TestCase):
    def test_fallback_provider(self) -> None:
        def fake_urlopen(url, timeout=9):  # noqa: ANN001, ARG001
            if "action=opensearch" in str(url):
                return _FakeResponse(json.dumps(["qwen", ["Qwen"], ["Model family"], ["https://en.wikipedia.org/wiki/Qwen"]]))
            raise RuntimeError("offline")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            service = ContentSearchService()
            results = service.search("qwen local model")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].source, "grokipedia")


if __name__ == "__main__":
    unittest.main()
