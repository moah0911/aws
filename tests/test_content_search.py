import json
import sys
import types
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
            self.assertGreaterEqual(len(results), 1)

    def test_ddgs_provider_integration(self) -> None:
        fake_ddgs = types.ModuleType("ddgs")

        class FakeDDGS:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
                return False

            def text(self, query, max_results=8):  # noqa: ANN001, ARG002
                return [{"title": "DDGS Result", "body": "Snippet", "href": "https://example.com/ddgs"}]

        fake_ddgs.DDGS = FakeDDGS

        with patch.dict(sys.modules, {"ddgs": fake_ddgs}):
            service = ContentSearchService()
            results = service.search("creator strategy")
            self.assertTrue(any(item.source == "ddgs" for item in results))

    def test_wikipedia_and_grokipedia_package_integration(self) -> None:
        fake_wikipedia = types.ModuleType("wikipedia")
        fake_wikipedia.search = lambda query, results=5: ["Creator economy"]  # noqa: ARG005
        fake_wikipedia.summary = lambda title, sentences=2: "Summary text"  # noqa: ARG005

        class FakePage:
            url = "https://example.com/wiki"

        fake_wikipedia.page = lambda title, auto_suggest=False: FakePage()  # noqa: ARG005

        fake_grok = types.ModuleType("grokipedia_api")
        fake_grok.search = lambda query: [  # noqa: ARG005
            {"title": "Grok Result", "snippet": "Grok snippet", "url": "https://example.com/grok"}
        ]

        with patch.dict(sys.modules, {"wikipedia": fake_wikipedia, "grokipedia_api": fake_grok}):
            service = ContentSearchService()
            results = service.search("creator economy")
            sources = {item.source for item in results}
            self.assertIn("wikipedia", sources)
            self.assertIn("grokipedia", sources)


if __name__ == "__main__":
    unittest.main()
