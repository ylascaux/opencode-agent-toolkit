import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts" / "configure-models"))


class ModelConfiguratorTests(unittest.TestCase):
    def test_parse_models_payload(self):
        parse = MODULE["parse_models_payload"]
        self.assertEqual(parse({"data": [{"id": "gpt-code"}, {"id": "fast-mini"}]}), ["fast-mini", "gpt-code"])

    def test_normalize_model_id(self):
        normalize = MODULE["normalize_model_id"]
        self.assertEqual(normalize("gpt-code"), "litellm/gpt-code")
        self.assertEqual(normalize("custom/model"), "custom/model")

    def test_recommend_profiles_prefers_obvious_signals(self):
        recommend = MODULE["recommend_profiles"]
        result = recommend(["fast-mini", "smart-router", "awesome-coder", "deep-reasoning-pro"])
        self.assertEqual(result["fast"], "fast-mini")
        self.assertEqual(result["general"], "smart-router")
        self.assertEqual(result["coding"], "awesome-coder")
        self.assertEqual(result["deep"], "deep-reasoning-pro")


if __name__ == "__main__":
    unittest.main()
