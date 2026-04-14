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
        for provider in (_search_duckduckgo, _search_wikipedia, _search_grokipedia):
            try:
                results.extend(provider(normalized))
            except Exception:  # noqa: BLE001
                continue

        deduped = _dedupe_by_url(results)
        return sorted(deduped, key=lambda item: item.score, reverse=True)[:15]


def _search_duckduckgo(query: str) -> list[SearchResult]:
    params = urllib.parse.urlencode({"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"})
    data = _fetch_json(f"https://api.duckduckgo.com/?{params}")

    results: list[SearchResult] = []
    abstract = data.get("AbstractText")
    abstract_url = data.get("AbstractURL")
    if abstract and abstract_url:
        results.append(SearchResult(data.get("Heading") or "DuckDuckGo Result", abstract, "duckduckgo", abstract_url, 0.95))

    for topic in data.get("RelatedTopics", [])[:7]:
        text = topic.get("Text") if isinstance(topic, dict) else None
        first_url = topic.get("FirstURL") if isinstance(topic, dict) else None
        if text and first_url:
            results.append(SearchResult(text.split(" - ")[0], text, "duckduckgo", first_url, 0.75))

    return results


def _search_wikipedia(query: str) -> list[SearchResult]:
    params = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": query, "utf8": "1", "format": "json"})
    data = _fetch_json(f"https://en.wikipedia.org/w/api.php?{params}")

    entries = data.get("query", {}).get("search", [])[:7]
    results: list[SearchResult] = []
    for idx, item in enumerate(entries):
        title = item.get("title", "")
        snippet = str(item.get("snippet", "")).replace("<span class=\"searchmatch\">", "").replace("</span>", "")
        pageid = item.get("pageid")
        if title and pageid:
            results.append(SearchResult(title, snippet, "wikipedia", f"https://en.wikipedia.org/?curid={pageid}", 0.85 - idx * 0.03))
    return results


def _search_grokipedia(query: str) -> list[SearchResult]:
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
            results.append(SearchResult(title, snippet, "grokipedia", url, 0.65 - idx * 0.04))
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
