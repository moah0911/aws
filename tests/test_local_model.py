import unittest

from vooc.services.local_model import FallbackLocalModelClient


class LocalModelTests(unittest.TestCase):
    def test_fallback_format(self) -> None:
        model = FallbackLocalModelClient()
        output = model.generate("Prompt: launch plan\nTone: professional\nTarget platform: linkedin")
        self.assertIn("Hook:", output)
        self.assertIn("Development:", output)
        self.assertIn("Resolution:", output)


if __name__ == "__main__":
    unittest.main()
