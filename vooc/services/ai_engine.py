from __future__ import annotations

import re
from collections import Counter

from vooc.services.local_model import FallbackLocalModelClient, LocalModelClient, PyTorchLocalModelClient
from vooc.types import ContentGenerationRequest, GeneratedContent, Platform, TopicSuggestion, VoiceProfile

BANNED_PATTERNS = [re.compile(r"hate", re.I), re.compile(r"violence", re.I), re.compile(r"explicit", re.I), re.compile(r"misinformation", re.I)]


class AIEngine:
    def __init__(self, local_model: LocalModelClient | None = None) -> None:
        self.local_model = local_model or PyTorchLocalModelClient()
        self.voice_profiles: dict[str, VoiceProfile] = {}
        self.creator_history: dict[str, list[str]] = {}

    def ingest_creator_history(self, creator_id: str, assets: list[str]) -> None:
        if not creator_id.strip():
            raise ValueError("creator_id is required")
        self.creator_history[creator_id] = assets[-50:]

    def analyze_voice(self, creator_id: str, samples: list[str]) -> VoiceProfile:
        if not creator_id.strip():
            raise ValueError("creator_id is required")
        if len(samples) < 10:
            raise ValueError("At least 10 samples are required to build a voice profile")

        words = [word.lower() for sample in samples for word in re.split(r"\W+", sample) if word]
        counts = Counter(words)
        top_vocabulary = [word for word, _ in counts.most_common(25)]

        profile = VoiceProfile(
            id=f"{creator_id}-voice",
            creator_id=creator_id,
            top_vocabulary=top_vocabulary,
            consistency_threshold=90,
        )
        self.voice_profiles[profile.id] = profile
        return profile

    def generate_content(self, request: ContentGenerationRequest) -> GeneratedContent:
        if not request.brief_id.strip() or not request.prompt.strip():
            raise ValueError("brief_id and prompt are required")

        profile = self.voice_profiles.get(request.voice_profile_id) if request.voice_profile_id else None
        prompt = "\n".join(
            [
                f"Brief ID: {request.brief_id}",
                f"Prompt: {request.prompt}",
                f"Target platform: {request.target_platform or 'generic'}",
                f"Tone: {request.constraints.tone or 'balanced'}",
                f"Voice hints: {', '.join(profile.top_vocabulary[:10]) if profile else 'none'}",
                "Return a production-ready script with sections: Hook, Development, Resolution, CTA.",
                "Ensure clarity, factual caution, and platform-safe language.",
            ]
        )

        try:
            draft = self.local_model.generate(prompt)
        except Exception:  # noqa: BLE001
            draft = FallbackLocalModelClient().generate(prompt)

        voiced = self._apply_voice_profile(draft, request.voice_profile_id)
        flags = self._scan_safety(voiced)
        content = self._trim_to_word_limit(voiced, request.constraints.max_words)

        return GeneratedContent(
            content=content,
            voice_consistency_score=92 if request.voice_profile_id else 75,
            safety_flags=flags,
        )

    def suggest_topics(self, creator_id: str, seed: str) -> list[TopicSuggestion]:
        if not creator_id.strip() or not seed.strip():
            raise ValueError("creator_id and seed are required")

        categories = ["technology", "wellness", "business", "culture", "education"]
        history = " ".join(self.creator_history.get(creator_id, [])).lower()

        suggestions: list[TopicSuggestion] = []
        for index, category in enumerate(categories):
            for offset, angle in enumerate(["contrarian", "practical"]):
                similarity = 84 if seed.lower() in history else 45 + index * 6 + offset
                suggestions.append(
                    TopicSuggestion(
                        topic=f"{seed} for {category}: {angle} angle",
                        relevance_score=min(100, 72 + index * 5 + offset * 4),
                        similarity_to_existing=similarity,
                        fresh_angle=f"Frame {seed} through a {angle} {category} lens with a concrete execution example.",
                    )
                )
        return suggestions

    def optimize_for_platform(self, content: str, platform: Platform) -> str:
        if platform == "youtube":
            return f"00:00 Hook\n00:30 Core narrative\n01:30 Tactical breakdown\n02:30 CTA\n\n{content}"
        if platform == "tiktok":
            return f"{content[:240]}\n#CreatorStrategy #ShortForm"
        if platform == "linkedin":
            return f"Professional Brief:\n{content}\n\nQuestion for peers: what would you add?"
        return f"<h1>Newsletter Draft</h1>\n<p>{content}</p>"

    def _apply_voice_profile(self, content: str, voice_profile_id: str | None) -> str:
        if not voice_profile_id:
            return content
        profile = self.voice_profiles.get(voice_profile_id)
        if not profile:
            return content
        signature = " • ".join(profile.top_vocabulary[:3])
        return f"{content}\n\nVoice signature: {signature}"

    def _scan_safety(self, content: str) -> list[str]:
        return [f"Flagged pattern: {pattern.pattern}" for pattern in BANNED_PATTERNS if pattern.search(content)]

    @staticmethod
    def _trim_to_word_limit(content: str, max_words: int = 180) -> str:
        words = content.split()
        if len(words) <= max_words:
            return content
        return " ".join(words[:max_words]) + "..."
