import json
import re
import unittest
from pathlib import Path

from runtime.common.normalization import load_normalized_agents
from runtime.opencode.adapter import OpenCodeAdapter

ROOT = Path(__file__).resolve().parents[1]
LEADS = {"meta-router", "orchestrator", "review-lead", "platform-architect", "security-lead", "research-runner"}


def last_effect(agent: dict, action: str, resource: str) -> str | None:
    effect = None
    for rule in agent["permissions"]:
        if rule.get("action") != action:
            continue
        if rule.get("resource") in {"*", resource}:
            effect = rule.get("effect")
    return effect


class StableConfigParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()
        cls.config = OpenCodeAdapter().build(cls.specs)

    def test_single_stable_shape_and_agent_count(self):
        self.assertEqual(len(self.config["agents"]), 41)
        self.assertEqual(set(self.config["agents"]), set(self.specs))
        self.assertNotIn("agent", self.config)
        self.assertNotIn("command", self.config)
        self.assertNotIn("plugin", self.config)
        self.assertIn("commands", self.config)
        self.assertIn("plugins", self.config)

    def test_meta_router_is_default(self):
        self.assertEqual(self.config["default_agent"], "meta-router")
        self.assertEqual(self.config["agents"]["meta-router"]["mode"], "primary")

    def test_model_envs_remain_explicit(self):
        values = set()
        for agent in self.config["agents"].values():
            match = re.fullmatch(r"\{env:(MODEL_[A-Z0-9_]+)\}", agent["model"])
            self.assertIsNotNone(match, agent["model"])
            values.add(match.group(1))
        self.assertEqual(len(values), 41)

    def test_leaf_agents_cannot_delegate(self):
        for name, agent in self.config["agents"].items():
            self.assertEqual(last_effect(agent, "subagent", "arbitrary-agent"), "deny", name)
            if name not in LEADS:
                allowed = [
                    rule for rule in agent["permissions"]
                    if rule["action"] == "subagent" and rule["effect"] == "allow"
                ]
                self.assertEqual(allowed, [], name)

    def test_destructive_shell_commands_remain_denied(self):
        for name, agent in self.config["agents"].items():
            for command in ("rm -rf*", "git push --force*", "terraform destroy*", "kubectl delete*"):
                self.assertEqual(last_effect(agent, "shell", command), "deny", f"{name}: {command}")

    def test_default_env_defines_model_tiers(self):
        env_text = (ROOT / ".env.example").read_text()
        for variable in ("MODEL_PROFILE", "MODEL_LOW", "MODEL_MEDIUM", "MODEL_HIGH"):
            self.assertRegex(env_text, rf"(?m)^{variable}=.+$")
        self.assertIn("github-copilot/gpt-5.6-luna", env_text)
        self.assertIn("github-copilot/gpt-5.6-terra", env_text)
        self.assertIn("github-copilot/gpt-5.6-sol", env_text)


if __name__ == "__main__":
    unittest.main()
