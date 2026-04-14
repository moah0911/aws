from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class ChatTurn:
    role: str
    content: str
    created_at: str


@dataclass
class Artifact:
    kind: str
    path: str
    prompt: str
    created_at: str


class SessionMemory:
    """Persistent session memory with creator-focused intelligence.

    USP: Unlike plain chat history, each session stores both conversation turns and
    produced artifacts (voice/image/text references), plus an auto-generated brief
    that captures recurring themes to keep creator intent stable over time.
    """

    def __init__(self, store_path: str | None = None, context_window: int = 12) -> None:
        default_path = os.path.join(os.path.expanduser("~"), ".vooc", "sessions.json")
        self.store_path = store_path or os.getenv("VOOC_SESSION_STORE", default_path)
        self.context_window = context_window
        self.sessions: dict[str, list[ChatTurn]] = {}
        self.artifacts: dict[str, list[Artifact]] = {}
        self._load()

    def create_session(self, session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError("session_id must not be empty")
        self.sessions.setdefault(normalized, [])
        self.artifacts.setdefault(normalized, [])
        self._save()
        return normalized

    def list_sessions(self) -> list[str]:
        return sorted(self.sessions.keys())

    def append(self, session_id: str, role: str, content: str) -> None:
        self.create_session(session_id)
        self.sessions[session_id].append(
            ChatTurn(role=role, content=content, created_at=datetime.now(timezone.utc).isoformat())
        )
        self._save()

    def register_artifact(self, session_id: str, kind: str, path: str, prompt: str) -> None:
        self.create_session(session_id)
        self.artifacts[session_id].append(
            Artifact(kind=kind, path=path, prompt=prompt, created_at=datetime.now(timezone.utc).isoformat())
        )
        self._save()

    def get_recent_context(self, session_id: str) -> list[ChatTurn]:
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id][-self.context_window :]

    def build_context_text(self, session_id: str) -> str:
        turns = self.get_recent_context(session_id)
        if not turns:
            return ""
        lines = [f"{turn.role}: {turn.content}" for turn in turns]
        return "\n".join(lines)

    def list_artifacts(self, session_id: str) -> list[Artifact]:
        return self.artifacts.get(session_id, [])

    def session_brief(self, session_id: str) -> str:
        turns = self.sessions.get(session_id, [])
        artifacts = self.artifacts.get(session_id, [])

        user_text = " ".join(turn.content for turn in turns if turn.role == "user")
        top_keywords = self._extract_keywords(user_text)

        lines = [
            f"Session: {session_id}",
            f"Turns: {len(turns)}",
            f"Artifacts: {len(artifacts)}",
            f"Top themes: {', '.join(top_keywords) if top_keywords else 'n/a'}",
        ]

        if artifacts:
            lines.append("Recent artifacts:")
            for item in artifacts[-5:]:
                lines.append(f"- [{item.kind}] {item.path} (prompt: {item.prompt[:80]})")

        return "\n".join(lines)

    def _extract_keywords(self, text: str, limit: int = 6) -> list[str]:
        tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
        stopwords = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "your",
            "what",
            "when",
            "where",
            "which",
            "will",
            "into",
            "about",
            "would",
            "could",
            "should",
            "there",
            "their",
            "them",
        }
        filtered = [token for token in tokens if token not in stopwords]
        return [word for word, _ in Counter(filtered).most_common(limit)]

    def _load(self) -> None:
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        sessions_raw = payload.get("sessions", {})
        for session_id, turns in sessions_raw.items():
            self.sessions[session_id] = [
                ChatTurn(
                    role=str(item.get("role", "user")),
                    content=str(item.get("content", "")),
                    created_at=str(item.get("created_at", "")),
                )
                for item in turns
            ]

        artifacts_raw = payload.get("artifacts", {})
        for session_id, items in artifacts_raw.items():
            self.artifacts[session_id] = [
                Artifact(
                    kind=str(item.get("kind", "text")),
                    path=str(item.get("path", "")),
                    prompt=str(item.get("prompt", "")),
                    created_at=str(item.get("created_at", "")),
                )
                for item in items
            ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        payload = {
            "sessions": {
                session_id: [asdict(turn) for turn in turns]
                for session_id, turns in self.sessions.items()
            },
            "artifacts": {
                session_id: [asdict(item) for item in items]
                for session_id, items in self.artifacts.items()
            },
        }
        with open(self.store_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
