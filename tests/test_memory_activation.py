from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MEMORY_PATH = SCRIPTS / "memory"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
loader = SourceFileLoader("memory_cli_activation", str(MEMORY_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec and spec.loader
memory_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory_cli)


class MemoryActivationTests(unittest.TestCase):
    def test_capture_on_auto_enables_memory_when_repo_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "runtime.env"
            env = {
                "OAT_RUNTIME": "container",
                "OAT_RUNTIME_ENV_FILE": str(settings),
                "OAT_MEMORY_REPO": "git@github.com:example/opencode-memory.git",
                "OAT_MEMORY_BACKEND": "legacy",
                "OAT_MEMORY_ENABLED": "0",
                "OAT_MEMORY_CAPTURE_ENABLED": "0",
            }
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(memory_cli, "ensure_plugin") as ensure_plugin,
            ):
                result = memory_cli.cmd_capture_on(argparse.Namespace())

            self.assertEqual(result, 0)
            self.assertEqual(
                settings.read_text().splitlines(),
                ["OAT_MEMORY_CAPTURE_ENABLED=1", "OAT_MEMORY_ENABLED=1"],
            )
            ensure_plugin.assert_called_once_with(force_sync=True)

    def test_capture_on_fails_without_memory_repo_instead_of_fake_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "runtime.env"
            env = {
                "OAT_RUNTIME": "container",
                "OAT_RUNTIME_ENV_FILE": str(settings),
                "OAT_MEMORY_BACKEND": "legacy",
                "OAT_MEMORY_ENABLED": "0",
                "OAT_MEMORY_CAPTURE_ENABLED": "0",
            }
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(memory_cli, "ensure_plugin") as ensure_plugin,
            ):
                result = memory_cli.cmd_capture_on(argparse.Namespace())

            self.assertEqual(result, 2)
            self.assertFalse(settings.exists())
            ensure_plugin.assert_not_called()

    def test_configure_postgres_validates_before_writing_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "runtime.env"
            env = {
                "OAT_RUNTIME": "container",
                "OAT_RUNTIME_ENV_FILE": str(settings),
            }
            args = argparse.Namespace(dsn="postgresql://user:secret@db.example/memory")
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(memory_cli, "_ensure_v2_python"),
                mock.patch.object(
                    memory_cli,
                    "_validate_v2_updates",
                    side_effect=RuntimeError("cannot connect"),
                ),
            ):
                with self.assertRaises(SystemExit) as raised:
                    memory_cli.cmd_configure_postgres(args)

            self.assertIn("validation failed", str(raised.exception).lower())
            self.assertFalse(settings.exists(), "failed validation must not persist the PostgreSQL DSN")

    def test_configure_postgres_persists_only_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / "runtime.env"
            env = {
                "OAT_RUNTIME": "container",
                "OAT_RUNTIME_ENV_FILE": str(settings),
            }
            dsn = "postgresql://user:secret@db.example/memory"
            args = argparse.Namespace(dsn=dsn)
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(memory_cli, "_ensure_v2_python"),
                mock.patch.object(memory_cli, "_validate_v2_updates") as validate,
                mock.patch("builtins.print") as output,
            ):
                result = memory_cli.cmd_configure_postgres(args)

            self.assertEqual(result, 0)
            validate.assert_called_once()
            saved = settings.read_text()
            self.assertIn("OAT_MEMORY_BACKEND=postgres", saved)
            self.assertIn("OAT_MEMORY_POSTGRES_DSN=", saved)
            rendered = "\n".join(" ".join(str(value) for value in call.args) for call in output.call_args_list)
            self.assertNotIn(dsn, rendered)
            self.assertNotIn("secret", rendered)

    def test_status_exposes_requested_and_effective_capture_state(self) -> None:
        fake_settings = SimpleNamespace(repo="plugin-repo", ref="v1", directory=Path("/plugin"))
        env = {
            "OAT_MEMORY_BACKEND": "legacy",
            "OAT_MEMORY_ENABLED": "0",
            "OAT_MEMORY_CAPTURE_ENABLED": "1",
            "OAT_MEMORY_REPO": "git@github.com:example/opencode-memory.git",
        }
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(memory_cli.PluginSettings, "from_env", return_value=fake_settings),
            mock.patch("builtins.print") as output,
        ):
            result = memory_cli.cmd_status(argparse.Namespace())

        self.assertEqual(result, 0)
        rendered = "\n".join(" ".join(str(value) for value in call.args) for call in output.call_args_list)
        self.assertIn("memory=off", rendered)
        self.assertIn("capture=on", rendered)
        self.assertIn("effective_capture=off", rendered)


if __name__ == "__main__":
    unittest.main()
