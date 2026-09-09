import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from memory_candidates import append_learned, find_candidate, learned_bullet, render_candidate_markdown, resolve_target


class MemoryCandidateTests(unittest.TestCase):
    def sample(self):
        return {
            "id": "abcdef123456",
            "fingerprint": "abcdef1234567890",
            "created_at": "2026-09-09T20:00:00Z",
            "session_id": "ses_123",
            "project_id": "repo",
            "kind": "decision",
            "title": "Use Git memory",
            "statement": "Keep durable memory in a private Git repository.",
            "rationale": "It remains reviewable.",
            "confidence": "high",
            "source": "opencode-v2-session-idle",
            "suggested_target": "project/decisions.md",
        }

    def test_render_candidate_does_not_embed_raw_transcript(self):
        text = render_candidate_markdown(self.sample(), status="accepted")
        self.assertIn("status: accepted", text)
        self.assertIn("raw transcript is not stored", text)
        self.assertNotIn("Conversation:", text)

    def test_resolve_target_is_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            name, path = resolve_target(vault, self.sample())
            self.assertEqual(name, "project/decisions.md")
            self.assertEqual(path, (vault / "projects/repo/decisions.md").resolve())
            hat_name, hat_path = resolve_target(vault, {**self.sample(), "suggested_target": "hat:reviewer"})
            self.assertEqual(hat_name, "hat:reviewer")
            self.assertEqual(hat_path, (vault / "hats/reviewer.md").resolve())

    def test_append_learned_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.md"
            self.assertTrue(append_learned(path, self.sample()))
            self.assertFalse(append_learned(path, self.sample()))
            self.assertEqual(path.read_text().count(learned_bullet(self.sample())), 1)

    def test_find_candidate_by_short_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pending = root / "candidates"
            pending.mkdir()
            data = self.sample()
            (pending / f"{data['fingerprint']}.json").write_text(json.dumps(data))
            ref = find_candidate(root, "abcdef")
            self.assertEqual(ref.bucket, "candidates")
            self.assertEqual(ref.data["id"], "abcdef123456")


if __name__ == "__main__":
    unittest.main()
