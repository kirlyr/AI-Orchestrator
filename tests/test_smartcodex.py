from pathlib import Path
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
import unittest
from unittest.mock import Mock, patch

# Exercise this checkout, not a separately installed SmartCodex copy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import smartcodex.cli as s
from smartcodex.repo_analyzer import RepoAnalyzer


class RouterTests(unittest.TestCase):
    def test_smart_router_skips_classifier_when_heuristic_is_confident(self):
        with patch.object(s, "ai_route", side_effect=AssertionError("classifier called")) as ai:
            result = s.select_route("Ubah warna tombol login jadi biru", "smart", "codex.exe", False)
        self.assertEqual(result.tier, "luna-low")
        ai.assert_not_called()

    def test_rules_route_tiers(self):
        self.assertEqual(s.rules_route("Ubah warna tombol login jadi biru").tier, "luna-low")
        self.assertEqual(s.rules_route("Tambahkan validasi untuk form").tier, "sol-low")
        self.assertEqual(s.rules_route("Audit security dan refactor arsitektur auth").tier, "sol-high")

    def test_legacy_force_tier_mapping_is_preserved(self):
        for tier, model_effort in s.TIERS.items():
            with self.subTest(tier=tier):
                self.assertEqual(s.TIERS[tier], model_effort)
        self.assertEqual(s.TIERS["sol-low"], ("gpt-6.1-sol", "low"))
        self.assertEqual(s.TIERS["astra-high"], ("gpt-6-astra", "high"))

    def test_astra_requires_opt_in_including_force_tier(self):
        self.assertEqual(s.capped(s.Decision("astra-high", "manual"), False).tier, "sol-high")
        self.assertEqual(s.capped(s.Decision("astra-high", "manual"), True).tier, "astra-high")

    def test_parser_keeps_v1_options(self):
        args = s.cli_args([
            "prompt", "--file", "prompt.txt", "--router", "rules", "--mode", "exec",
            "--force-tier", "sol-low", "--allow-astra", "--write", "--dry-run",
        ])
        self.assertEqual((args.router, args.mode, args.force_tier), ("rules", "exec", "sol-low"))
        self.assertTrue(args.allow_astra and args.write and args.dry_run)

    def test_ai_router_calls_classifier_and_caps_astra(self):
        ai_decision = s.Decision("astra-high", "exceptional", "ai", True)
        with patch.object(s, "ai_route", return_value=ai_decision) as ai:
            result = s.select_route("uncertain task", "ai", "codex.exe", False)
        ai.assert_called_once_with("uncertain task", "codex.exe")
        self.assertEqual(result.tier, "sol-high")
        self.assertTrue(result.ai_used)

    def test_ai_router_fallbacks_to_rules(self):
        with patch.object(s, "ai_route", side_effect=RuntimeError("offline")):
            with patch("sys.stderr"):
                result = s.select_route("Ubah warna tombol", "ai", "codex.exe", False)
        self.assertEqual(result.tier, "luna-low")

    def test_force_tier_dry_run_does_not_call_codex(self):
        with patch.object(s.shutil, "which", return_value=None), patch.object(s.subprocess, "run") as run:
            self.assertEqual(s.main(["anything", "--force-tier", "sol-low", "--dry-run"]), 0)
        run.assert_not_called()

    def test_exec_uses_argument_list_and_read_only_sandbox(self):
        completed = Mock(returncode=7)
        with patch.object(s.shutil, "which", return_value="codex.exe"), \
             patch.object(s.subprocess, "run", return_value=completed) as run:
            code = s.main(["inspect this", "--mode", "exec", "--force-tier", "sol-low"])
        self.assertEqual(code, 7)
        command = run.call_args.args[0]
        self.assertIsInstance(command, list)
        self.assertEqual(command[:2], ["codex.exe", "exec"])
        self.assertIn("--sandbox", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertEqual(run.call_args.kwargs["input"], "inspect this")
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_exec_write_flag_preserves_workspace_write_sandbox(self):
        with patch.object(s.shutil, "which", return_value="codex.exe"), \
             patch.object(s.subprocess, "run", return_value=Mock(returncode=0)) as run:
            self.assertEqual(s.main(["change it", "--mode", "exec", "--write", "--dry-run"]), 0)
        run.assert_not_called()
        with patch.object(s.shutil, "which", return_value="codex.exe"), \
             patch.object(s.subprocess, "run", return_value=Mock(returncode=0)) as run:
            s.main(["change it", "--mode", "exec", "--write", "--router", "rules"])
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")

    def test_chat_uses_argument_list_and_legacy_sandbox(self):
        with patch.object(s.shutil, "which", return_value="codex.exe"), \
             patch.object(s.subprocess, "call", return_value=0) as call:
            self.assertEqual(s.main(["hello", "--router", "rules"]), 0)
        command = call.call_args.args[0]
        self.assertIsInstance(command, list)
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(command[command.index("--ask-for-approval") + 1], "on-request")

    def test_subprocess_os_error_is_reported(self):
        with patch.object(s.shutil, "which", return_value="codex.exe"), \
             patch.object(s.subprocess, "run", side_effect=OSError("missing executable")), \
             patch("sys.stderr"):
            self.assertEqual(s.main(["hello", "--mode", "exec"]), 1)

    def test_missing_prompt_and_dry_run_without_codex(self):
        self.assertEqual(s.main(["--dry-run"]), 2)
        with patch.object(s.shutil, "which", return_value=None):
            self.assertEqual(s.main(["Ubah warna tombol", "--dry-run"]), 0)

    def test_console_entry_point_targets_cli_main(self):
        project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["requires-python"], ">=3.10")
        self.assertEqual(project["project"]["scripts"]["smartcodex"], "smartcodex.cli:main")


class RepoAnalyzerTests(unittest.TestCase):
    fixtures = Path(__file__).resolve().parent / "fixtures"

    def test_laravel_manifest_and_relevant_candidate(self):
        root = self.fixtures / "laravel"
        result = RepoAnalyzer(root).analyze("update UserController")
        self.assertIn("PHP", result.languages); self.assertIn("Laravel", result.frameworks)
        self.assertIn("app/UserController.php", result.candidates)

    def test_javascript_typescript_manifest(self):
        root = self.fixtures / "javascript"
        result = RepoAnalyzer(root).analyze("Widget")
        self.assertIn("JavaScript", result.languages); self.assertIn("TypeScript", result.languages)
        self.assertIn("React", result.frameworks); self.assertIn("src/Widget.tsx", result.candidates)

    def test_non_git_fallback_and_secret_exclusion(self):
        root = self.fixtures / "non_git"
        result = RepoAnalyzer(root).analyze("app")
        self.assertFalse(result.is_git); self.assertIn("app.py", [f.path for f in result.files])
        self.assertNotIn(".env", [f.path for f in result.files])
        self.assertNotIn("PLACEHOLDER_DO_NOT_USE_AS_A_SECRET", repr(result))

    def test_git_dirty_and_untracked_status(self):
        import smartcodex.repo_analyzer as analyzer
        root = self.fixtures / "git_dirty"
        def git_output(path, *args):
            if args == ("rev-parse", "--show-toplevel"): return str(root) + "\n"
            if args == ("branch", "--show-current"): return "fixture-branch\n"
            if args == ("ls-files", "-z"): return "tracked.py\0"
            if args == ("status", "--porcelain=v1", "-z", "--untracked-files=all"):
                return " M tracked.py\0?? new.py\0"
            raise AssertionError(args)
        with patch.object(analyzer, "_git", side_effect=git_output):
            result = RepoAnalyzer(root).analyze("tracked new")
        by_path = {f.path: f for f in result.files}
        self.assertTrue(result.is_git); self.assertEqual(result.branch, "fixture-branch")
        self.assertNotEqual(by_path["tracked.py"].status, "clean")
        self.assertEqual(by_path["new.py"].status, "??")

    def test_traversal_rejected_and_outside_symlink_ignored(self):
        from smartcodex.repo_analyzer import _safe_relative
        root = self.fixtures / "non_git"
        self.assertIsNone(_safe_relative(root, root.parent / "outside.txt"))
        link = root / "escape-test-link"
        try:
            link.symlink_to(self.fixtures / "javascript", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        try:
            result = RepoAnalyzer(root).analyze("Widget")
            self.assertFalse(any(path.startswith("escape-test-link/") for path in (f.path for f in result.files)))
        finally:
            link.unlink(missing_ok=True)

    def test_path_and_byte_budgets(self):
        root = self.fixtures / "budget"
        result = RepoAnalyzer(root, max_paths=3, max_file_bytes=5, max_total_bytes=8).analyze()
        self.assertLessEqual(len(result.files), 3); self.assertLessEqual(result.total_bytes, 8)
        self.assertTrue(result.truncated)


if __name__ == "__main__":
    unittest.main()
