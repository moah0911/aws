from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    snippet: str
    source: str
    url: str
    score: float


class ContentSearchService:
    def search(self, query: str) -> list[SearchResult]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("Search query cannot be empty")

        results = []
        for provider in (_search_ddgs, _search_wikipedia_pkg, _search_grokipedia_pkg, _search_fallback_wikipedia_opensearch):
            try:
                results.extend(provider(normalized))
            except Exception:  # noqa: BLE001
                continue

        deduped = _dedupe_by_url(results)
        return sorted(deduped, key=lambda item: item.score, reverse=True)[:20]


def _search_ddgs(query: str) -> list[SearchResult]:
    try:
        from ddgs import DDGS  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("ddgs package not available") from exc

    results: list[SearchResult] = []
    with DDGS() as client:
        for idx, item in enumerate(client.text(query, max_results=8)):
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("body", "")).strip()
            href = str(item.get("href", "")).strip()
            if title and href:
                results.append(SearchResult(title, snippet, "ddgs", href, 0.95 - idx * 0.03))

    return results


def _search_wikipedia_pkg(query: str) -> list[SearchResult]:
    try:
        import wikipedia  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("wikipedia package not available") from exc

    titles = wikipedia.search(query, results=5)
    results: list[SearchResult] = []

    for idx, title in enumerate(titles):
        try:
            summary = wikipedia.summary(title, sentences=2)
            page = wikipedia.page(title, auto_suggest=False)
        except Exception:  # noqa: BLE001
            continue

        results.append(SearchResult(str(title), str(summary), "wikipedia", str(page.url), 0.86 - idx * 0.04))
    return results


def _search_grokipedia_pkg(query: str) -> list[SearchResult]:
    try:
        import grokipedia_api  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("grokipedia-api package not available") from exc

    raw_results = []
    if hasattr(grokipedia_api, "search"):
        raw_results = grokipedia_api.search(query)
    elif hasattr(grokipedia_api, "GrokipediaAPI"):
        client = grokipedia_api.GrokipediaAPI()
        raw_results = client.search(query)
    else:
        raise RuntimeError("Unsupported grokipedia_api interface")

    results: list[SearchResult] = []
    for idx, item in enumerate(raw_results[:6]):
        title = str(item.get("title") or item.get("name") or "").strip()
        snippet = str(item.get("snippet") or item.get("summary") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        if title and url:
            results.append(SearchResult(title, snippet, "grokipedia", url, 0.78 - idx * 0.04))

    return results


def _search_fallback_wikipedia_opensearch(query: str) -> list[SearchResult]:
    params = urllib.parse.urlencode({"action": "opensearch", "search": query, "limit": "5", "namespace": "0", "format": "json"})
    data = _fetch_json(f"https://en.wikipedia.org/w/api.php?{params}")

    titles = data[1] if len(data) > 1 else []
    snippets = data[2] if len(data) > 2 else []
    urls = data[3] if len(data) > 3 else []

    results: list[SearchResult] = []
    for idx, title in enumerate(titles):
        url = urls[idx] if idx < len(urls) else ""
        snippet = snippets[idx] if idx < len(snippets) else ""
        if url:
            results.append(SearchResult(title, snippet, "wikipedia", url, 0.60 - idx * 0.03))
    return results


def _fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=9) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def _dedupe_by_url(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    deduped: list[SearchResult] = []
    for result in results:
        key = result.url.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped
