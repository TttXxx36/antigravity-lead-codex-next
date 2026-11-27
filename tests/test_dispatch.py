import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DispatchAndHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatch = load_module("dispatch", "skills/multi-agent-dispatch/scripts/dispatch.py")
        cls.hook = load_module("allow_dispatch", "plugins/codex-auto-router/hooks/allow_dispatch.py")

    def test_semver_ordering(self):
        parse = self.dispatch.parse_codex_semver
        self.assertGreater(parse("codex-cli 0.171.0"), parse("codex-cli 0.171.0-alpha.13"))
        self.assertGreater(parse("codex-cli 0.172.0-alpha.1"), parse("codex-cli 0.171.0"))

    def test_valid_backends_codex_only(self):
        self.assertEqual(self.dispatch.VALID_BACKENDS, ("codex",))

    def test_hook_blocks_shell_chaining_and_gates_worker_merge(self):
        # Shell chaining must never be auto-allowed
        self.assertFalse(self.hook.is_pure_dispatch_command("python3 dispatch.py status && rm -rf /"))
        self.assertTrue(self.hook.has_unsafe_shell_syntax("echo a | cat"))

        # Merging agy-worker/* must force explicit human confirmation
        res = self.hook.evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "git merge agy-worker/feat-auth"},
                }
            }
        )
        self.assertEqual(res["decision"], "force_ask")

        # Unknown / malformed payloads fail safe to standard approval
        self.assertEqual(self.hook.evaluate_hook(None)["decision"], "ask")

    def test_network_flag_command_building_and_guardrails(self):
        report_path = pathlib.Path("/tmp/report.json")
        workdir = pathlib.Path("/tmp/demo-repo")

        offline_cmd = self.dispatch.build_codex_exec_cmd(
            codex_bin="codex",
            workdir=workdir,
            model="gpt-6.2-sol",
            effort="high",
            sandbox="workspace-write",
            network=False,
            report_path=report_path,
            is_git_repo=True,
        )
        self.assertNotIn("sandbox_workspace_write.network_access=true", offline_cmd)
        self.assertIn("workspace-write", offline_cmd)

        self.assertIn("sandbox_workspace_write.network_access=false", offline_cmd)
        for builder, extra in (
            (self.dispatch.build_codex_exec_cmd, {"workdir": workdir}),
            (self.dispatch.build_codex_resume_cmd, {"session_id":"01a9-demo"}),
        ):
            for sandbox, network in (("workspace-write", True), ("read-only", True), ("danger-full-access", False)):
                with self.assertRaises(ValueError):
                    builder(codex_bin="codex", model="mock", effort="high", sandbox=sandbox,
                            network=network, report_path=report_path, is_git_repo=True, **extra)

    def test_hook_gates_network_dispatch_and_forbids_danger_mode(self):
        import shlex
        script = shlex.quote(self.hook.DISPATCH_SCRIPT)

        offline = self.hook.evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f'python3 {script} run --cwd /tmp --prompt "fix bug"'},
                }
            }
        )
        self.assertEqual(offline["decision"], "ask")

        networked = self.hook.evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f'python3 {script} run --cwd /tmp --network --prompt "sync api"'},
                }
            }
        )
        self.assertEqual(networked["decision"], "force_ask")
        self.assertFalse(self.hook.is_pure_dispatch_command(f'python3 {script} run --network --prompt "x"'))

        danger = self.hook.evaluate_hook(
            {
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": f'python3 {script} run --sandbox danger-full-access --prompt "x"'},
                }
            }
        )
        self.assertEqual(danger["decision"], "ask")


if __name__ == "__main__":
    unittest.main()
