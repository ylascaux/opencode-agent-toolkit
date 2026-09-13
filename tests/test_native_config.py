import copy
import json
import unittest
from pathlib import Path

from runtime.common.normalization import load_normalized_agents, load_normalized_skills
from runtime.opencode.native import NativeOpenCodeAdapter

ROOT = Path(__file__).resolve().parents[1]


class NativeConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_normalized_agents()
        cls.original = copy.deepcopy(cls.specs)
        cls.adapter = NativeOpenCodeAdapter()
        cls.plan = cls.adapter.plan(cls.specs, load_normalized_skills())

    def test_native_configs_keep_meta_and_agents_without_runtime_plugins(self):
        for filename, agents_key, plugins_key in [
            ('opencode.jsonc', 'agent', 'plugin'),
            ('opencode.v2.jsonc', 'agents', 'plugins'),
        ]:
            with self.subTest(filename=filename):
                config = json.loads(self.plan.files[ROOT / filename])
                self.assertEqual(config['default_agent'], 'meta-router')
                self.assertEqual(set(config[agents_key]), set(self.specs))
                self.assertEqual(config[plugins_key], [])
                self.assertNotIn('shell', config)
                self.assertTrue(all('steps' not in agent for agent in config[agents_key].values()))
                self.assertNotIn('PLAN_APPROVAL_REQUIRED', json.dumps(config))

    def test_no_obsolete_plan_or_host_transport_restrictions_in_prompts(self):
        for path, content in self.plan.files.items():
            if path.suffix == '.md' and path.parent.name in ('prompts', 'prompts-v1'):
                text = content.decode()
                with self.subTest(path=path.name):
                    self.assertNotIn('PLAN_APPROVAL_REQUIRED', text)
                    self.assertNotIn('PLAN_REAPPROVAL_REQUIRED', text)
                    self.assertNotIn('Remote Git access is manual-only', text)
                    self.assertIn('## Native execution', text)

    def test_role_boundaries_and_destructive_permissions_are_preserved(self):
        specs = self.adapter.native_specs(self.specs)
        defaults = specs['builder'].permissions
        self.assertEqual(defaults['edit'], 'allow')
        self.assertEqual(defaults['bash']['*'], 'allow')
        self.assertNotIn('git fetch*', defaults['bash'])
        self.assertEqual(defaults['bash']['terraform destroy*'], 'deny')
        for name, spec in specs.items():
            local = json.loads((spec.path / 'permissions.json').read_text())
            for key, value in local.items():
                if isinstance(value, str):
                    self.assertEqual(spec.permissions[key], value, name)

    def test_native_render_does_not_mutate_canonical_agents_or_codex_source(self):
        self.assertEqual(self.specs, self.original)

    def test_v1_prompts_are_materialized_before_optional_memory(self):
        for name in self.specs:
            self.assertEqual(self.plan.files[ROOT / '.generated/prompts' / f'{name}.md'],
                             self.plan.files[ROOT / '.generated/prompts-v1' / f'{name}.md'])


if __name__ == '__main__':
    unittest.main()
