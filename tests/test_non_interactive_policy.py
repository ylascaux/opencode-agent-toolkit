import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / ".generated" / "prompts"


class NonInteractivePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python3", str(ROOT / "scripts" / "generate-config")], check=True)
        cls.config = json.loads((ROOT / "opencode.jsonc").read_text())

    @staticmethod
    def _effect_section(text: str, effect: str) -> str:
        capabilities = text.split("## Effective capabilities", 1)[1]
        headings = {"allow": "### ALLOW", "ask": "### ASK", "deny": "### DENY"}
        start = capabilities.split(headings[effect], 1)[1]
        later = [
            heading
            for key, heading in headings.items()
            if key != effect and heading in start
        ]
        if not later:
            return start
        positions = [start.index(heading) for heading in later]
        return start[: min(positions)]

    def test_every_generated_prompt_enforces_non_interactive_execution(self):
        required = [
            "## Non-interactive execution",
            "All tool and shell execution MUST be non-interactive.",
            "NEVER open or intentionally invoke an interactive pager",
            "git --no-pager ...",
            "## Effective capabilities",
            "### ALLOW",
            "### ASK",
            "### DENY",
        ]
        for name in self.config["agent"]:
            text = (PROMPTS / f"{name}.md").read_text()
            for expected in required:
                self.assertIn(expected, text, f"{name}: {expected}")

    def test_capability_map_matches_effective_v1_permissions(self):
        labels = {"bash": "bash / shell", "task": "task / subagent"}
        for name, agent in self.config["agent"].items():
            text = (PROMPTS / f"{name}.md").read_text()
            for action, value in agent["permission"].items():
                label = labels.get(action, action)
                rules = {"*": value} if isinstance(value, str) else value
                for resource, effect in rules.items():
                    section = self._effect_section(text, effect)
                    self.assertIn(f"`{label}`:", section, f"{name}: {action}/{effect}")
                    self.assertIn(f"`{resource}`", section, f"{name}: {action}/{resource}/{effect}")

    def test_interactive_terminal_tools_are_denied_for_every_agent(self):
        denied = [
            "less*",
            "more*",
            "man*",
            "vim*",
            "vi *",
            "nano*",
            "emacs*",
            "top*",
            "htop*",
            "btop*",
            "watch*",
            "fzf*",
            "lazygit*",
            "tig*",
            "git add -p*",
            "git add --patch*",
            "git rebase -i*",
            "git rebase --interactive*",
        ]
        allowed_non_paging_git = [
            "git --no-pager status*",
            "git --no-pager diff*",
            "git --no-pager show*",
            "git --no-pager log*",
        ]

        for name, agent in self.config["agent"].items():
            shell = agent["permission"]["bash"]
            for pattern in denied:
                self.assertEqual(shell[pattern], "deny", f"{name}: {pattern}")
            for pattern in allowed_non_paging_git:
                self.assertEqual(shell[pattern], "allow", f"{name}: {pattern}")

    def test_v2_runtime_requires_shell_create_hook(self):
        text = (ROOT / ".opencode" / "plugins" / "reliability-v2.ts").read_text()
        self.assertIn('ctx.shell.hook("create.before"', text)
        self.assertIn("applyNonInteractiveShellEnv(event.env)", text)
        self.assertIn("required for non-interactive agent execution", text)


if __name__ == "__main__":
    unittest.main()
