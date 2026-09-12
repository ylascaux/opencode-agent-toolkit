import tempfile
import tomllib
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.codex.adapter import CodexAdapter
from runtime.common.normalization import load_normalized_agents


class CodexReasoningLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()

    def _native_agent(self, plan, root: Path, name: str):
        path = root / ".generated" / "codex" / "agents" / f"{name}.toml"
        return tomllib.loads(plan.files[path].decode())

    def test_tier_override_accepts_max_and_ultra(self):
        builder = self.specs["builder"]
        for effort in ("max", "ultra"):
            with self.subTest(effort=effort), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                env = {f"CODEX_REASONING_{builder.tier.upper()}": effort}
                plan = CodexAdapter(root, environ=env).plan(self.specs)
                native = self._native_agent(plan, root, "builder")
                self.assertEqual(native["model_reasoning_effort"], effort)

    def test_per_agent_and_extension_overrides_accept_ultra_and_max(self):
        builder = self.specs["builder"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = {
                **self.specs,
                "builder": replace(
                    builder,
                    extensions={**builder.extensions, "codex": {"reasoning": "max"}},
                ),
            }
            plan = CodexAdapter(root, environ={}).plan(specs)
            self.assertEqual(
                self._native_agent(plan, root, "builder")["model_reasoning_effort"],
                "max",
            )

            plan = CodexAdapter(
                root,
                environ={"CODEX_REASONING_BUILDER": "ultra"},
            ).plan(specs)
            self.assertEqual(
                self._native_agent(plan, root, "builder")["model_reasoning_effort"],
                "ultra",
            )


if __name__ == "__main__":
    unittest.main()
