import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OneCommandInstallTests(unittest.TestCase):
    def test_just_install_routes_through_bootstrap(self):
        text = (ROOT / 'justfile').read_text()
        install_block = text.split('\ninstall:\n', 1)[1].split('\n# Apply a model-provider profile', 1)[0]
        self.assertIn('bash ./scripts/bootstrap', install_block)

    def test_bootstrap_generates_then_links_without_containers_or_global_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / 'scripts'
            scripts.mkdir()
            shutil.copy2(ROOT / 'scripts/bootstrap', scripts / 'bootstrap')
            (root / '.env.example').write_text('MODEL_PROFILE=copilot\n')
            log = root / 'calls'
            env = os.environ.copy()
            env['INSTALL_LOG'] = str(log)
            for name in ('opencode-agents', 'user-link'):
                (scripts / name).write_text('#!/bin/bash\nprintf "%s %s\\n" "$(basename "$0")" "$*" >> "$INSTALL_LOG"\n')
            result = subprocess.run(['bash', str(scripts / 'bootstrap')], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().splitlines(), ['opencode-agents config', 'user-link install oc', 'user-link install oc2'])
            self.assertEqual((root / '.env').read_text(), 'MODEL_PROFILE=copilot\n')
            (root / '.env').write_text('MODEL_PROFILE=personal\nOAT_MEMORY_ENABLED=1\n')
            (root / '.env.local').write_text('MODEL_BUILDER=personal/model\n')
            result = subprocess.run(['bash', str(scripts / 'bootstrap')], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / '.env').read_text(), 'MODEL_PROFILE=personal\nOAT_MEMORY_ENABLED=1\n')
            self.assertEqual((root / '.env.local').read_text(), 'MODEL_BUILDER=personal/model\n')
            self.assertFalse((root / '.venv').exists())
            self.assertFalse((root / 'node_modules').exists())
            self.assertFalse((root / 'compose.yaml').exists())

    def test_bootstrap_remains_valid_bash(self):
        result = subprocess.run(['bash', '-n', str(ROOT / 'scripts/bootstrap')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
