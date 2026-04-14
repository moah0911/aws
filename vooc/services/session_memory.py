from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class ChatTurn:
    role: str
    content: str
    created_at: str


class SessionMemory:
    def __init__(self, store_path: str | None = None, context_window: int = 12) -> None:
        default_path = os.path.join(os.path.expanduser("~"), ".vooc", "sessions.json")
        self.store_path = store_path or os.getenv("VOOC_SESSION_STORE", default_path)
        self.context_window = context_window
        self.sessions: dict[str, list[ChatTurn]] = {}
        self._load()

    def create_session(self, session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError("session_id must not be empty")
        self.sessions.setdefault(normalized, [])
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

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        payload = {
            "sessions": {
                session_id: [asdict(turn) for turn in turns]
                for session_id, turns in self.sessions.items()
            }
        }
        with open(self.store_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
