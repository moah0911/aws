import unittest

from vooc.services.ai_engine import AIEngine
from vooc.types import ContentConstraints, ContentGenerationRequest


class MockLocalModel:
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:  # noqa: ARG002
        return f"MOCK_MODEL_OUTPUT: {prompt[:60]}"


class AIEngineTests(unittest.TestCase):
    def test_voice_profile(self) -> None:
        ai = AIEngine(MockLocalModel())
        profile = ai.analyze_voice("creator-1", [f"sample {idx} strategy" for idx in range(10)])
        self.assertEqual(profile.creator_id, "creator-1")
        self.assertEqual(profile.consistency_threshold, 90)

    def test_topic_count(self) -> None:
        ai = AIEngine(MockLocalModel())
        topics = ai.suggest_topics("creator-1", "audience growth")
        self.assertGreaterEqual(len(topics), 10)

    def test_generate_content(self) -> None:
        ai = AIEngine(MockLocalModel())
        result = ai.generate_content(
            ContentGenerationRequest(
                brief_id="brief-1",
                prompt="Improve retention",
                constraints=ContentConstraints(tone="professional"),
            )
        )
        self.assertIn("MOCK_MODEL_OUTPUT", result.content)


if __name__ == "__main__":
    unittest.main()
