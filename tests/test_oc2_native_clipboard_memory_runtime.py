import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NativeClipboardMemoryRuntimeTests(unittest.TestCase):
    def test_docker_runtime_prefers_matching_native_v1_client(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        env = (ROOT / ".env.example").read_text()

        self.assertIn('v1_client_mode="${OAT_OC_CLIENT_MODE:-auto}"', runtime)
        self.assertIn('native_v1_bin="${OAT_OC_NATIVE_BIN:-opencode}"', runtime)
        self.assertIn('command -v "$native_v1_bin"', runtime)
        self.assertIn('host_version="$($native_v1_bin --version', runtime)
        self.assertIn('server_version="$("${compose[@]}" exec -T "$service" opencode --version', runtime)
        self.assertIn('exec "$native_v1_bin" attach "http://127.0.0.1:$host_port" --dir "$cwd"', runtime)
        self.assertIn('exec "$native_v1_bin" run --attach "http://127.0.0.1:$host_port" --dir "$cwd" "$@"', runtime)
        self.assertIn("OAT_OC_CLIENT_MODE=auto", env)
        self.assertIn("# OAT_OC_NATIVE_BIN=opencode", env)

    def test_v1_non_tui_commands_remain_in_persistent_container(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        v1 = runtime.split('if [[ "$major" == "1" ]]; then', 1)[1].split(
            "# Authentication is local credential state", 1
        )[0]

        self.assertIn('exec "${compose[@]}" exec "${exec_opts[@]}" -w "$cwd" "$service" opencode "$@"', v1)
        self.assertIn("falling back to container TUI", v1)

    def test_docker_runtime_prefers_matching_native_v2_client(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        env = (ROOT / ".env.example").read_text()

        self.assertIn('client_mode="${OAT_OC2_CLIENT_MODE:-auto}"', runtime)
        self.assertIn('native_v2_bin="${OAT_OC2_NATIVE_BIN:-opencode2}"', runtime)
        self.assertIn('command -v "$native_v2_bin"', runtime)
        self.assertIn('host_version="$($native_v2_bin --version', runtime)
        self.assertIn('server_version="$("${compose[@]}" exec -T "$service" opencode2 --version', runtime)
        self.assertIn('exec "$native_v2_bin" --server "http://127.0.0.1:$host_port" "$@"', runtime)
        self.assertIn("OAT_OC2_CLIENT_MODE=auto", env)

    def test_auth_remains_in_persistent_container_home(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        auth = runtime.index('if [[ "${1:-}" == "auth" ]]')
        native = runtime.index('use_native_v2=0')
        self.assertLess(auth, native)
        self.assertIn('opencode2 "$@"', runtime[auth:native])

    def test_memory_runtime_settings_persist_and_trigger_reload(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        memory = (ROOT / "scripts" / "memory").read_text()
        compose = (ROOT / "compose.yaml").read_text()

        self.assertIn('runtime_env="$state_dir/runtime.env"', runtime)
        self.assertIn('export OAT_RUNTIME_ENV_FILE_HOST="$runtime_env"', runtime)
        self.assertIn('enable|disable|capture-on|capture-off) restart_memory_consumers', runtime)
        self.assertIn('runtime_path = os.getenv("OAT_RUNTIME_ENV_FILE", "").strip()', memory)
        self.assertIn('OAT_RUNTIME_ENV_FILE: /root/.local/state/opencode-agent-toolkit/runtime.env', compose)
        self.assertIn('${OAT_RUNTIME_ENV_FILE_HOST:-./.runtime.env}', compose)

    def test_v2_server_password_is_generated_locally_when_missing(self):
        runtime = (ROOT / "scripts" / "docker-runtime").read_text()
        env = (ROOT / ".env.example").read_text()

        self.assertIn("ensure_v2_server_password", runtime)
        self.assertIn("OPENCODE_SERVER_PASSWORD=%s", runtime)
        self.assertIn('chmod 600 "$env_local"', runtime)
        self.assertIn("# OPENCODE_SERVER_PASSWORD=", env)


if __name__ == "__main__":
    unittest.main()
