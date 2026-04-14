from dataclasses import dataclass
from typing import Literal

Platform = Literal["youtube", "tiktok", "linkedin", "substack"]


@dataclass
class ContentConstraints:
    max_words: int = 180
    tone: str | None = None
    duration_seconds: int | None = None


@dataclass
class ContentGenerationRequest:
    brief_id: str
    prompt: str
    constraints: ContentConstraints
    voice_profile_id: str | None = None
    target_platform: Platform | None = None


@dataclass
class GeneratedContent:
    content: str
    voice_consistency_score: int
    safety_flags: list[str]


@dataclass
class VoiceProfile:
    id: str
    creator_id: str
    top_vocabulary: list[str]
    consistency_threshold: int


@dataclass
class TopicSuggestion:
    topic: str
    relevance_score: int
    similarity_to_existing: int
    fresh_angle: str
