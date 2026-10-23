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
from smartcodex.intent_gate import decide, load_profile, local_decision


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

    def test_traversal_rejected(self):
        from smartcodex.repo_analyzer import _safe_relative
        root = self.fixtures / "non_git"
        self.assertIsNone(_safe_relative(root, root.parent / "outside.txt"))

    def test_outside_symlink_ignored(self):
        root = self.fixtures / "non_git"
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

    def test_temporary_env_content_is_never_read_or_returned(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = "REGRESSION_SENTINEL_DO_NOT_EXPOSE"
            (root / ".env").write_text(secret, encoding="utf-8")
            (root / "app.py").write_text("print('safe')", encoding="utf-8")
            with patch.object(Path, "read_text", autospec=True, wraps=Path.read_text) as read_text:
                result = RepoAnalyzer(root).analyze()
            self.assertNotIn(".env", [f.path for f in result.files])
            self.assertNotIn(secret, repr(result))
            self.assertFalse(any(call.args[0].name == ".env" for call in read_text.call_args_list))

    def test_git_rename_and_copy_status_records(self):
        import smartcodex.repo_analyzer as analyzer
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "renamed.py").write_text("x", encoding="utf-8")
            (root / "copied.py").write_text("y", encoding="utf-8")
            self._assert_git_rename_copy(analyzer, root)

    def _assert_git_rename_copy(self, analyzer, root):
        def git_output(path, *args):
            if args == ("rev-parse", "--show-toplevel"): return str(root) + "\n"
            if args == ("branch", "--show-current"): return "fixture-branch\n"
            if args == ("ls-files", "-z"): return "renamed.py\0copied.py\0"
            if args == ("status", "--porcelain=v1", "-z", "--untracked-files=all"):
                return "R  renamed.py\0old.py\0C  copied.py\0source.py\0"
            raise AssertionError(args)
        with patch.object(analyzer, "_git", side_effect=git_output):
            result = RepoAnalyzer(root).analyze()
        by_path = {f.path: f for f in result.files}
        self.assertEqual(by_path["renamed.py"].status, "R")
        self.assertEqual(by_path["copied.py"].status, "C")

    def test_path_and_byte_budgets(self):
        root = self.fixtures / "budget"
        result = RepoAnalyzer(root, max_paths=3, max_file_bytes=5, max_total_bytes=8).analyze()
        self.assertLessEqual(len(result.files), 3); self.assertLessEqual(result.total_bytes, 8)
        self.assertTrue(result.truncated)


class IntentGateTests(unittest.TestCase):
    def setUp(self):
        self.summary = RepoAnalyzer(Path(__file__).parent / "fixtures" / "non_git").analyze("UI button")
        self.profile = load_profile(Path(__file__).resolve().parents[1] / "configs" / "model-profiles.toml")

    def test_typo_direct_without_classifier_and_testing_profile(self):
        with patch("smartcodex.intent_gate.classify", side_effect=AssertionError("unexpected classifier")):
            result = decide("Fix typo in button label", self.summary, "codex", self.profile)
        self.assertEqual((result.intent, result.tier), ("DIRECT", "simple"))
        self.assertEqual(self.profile.tiers[result.tier].model, "gpt-6-luna")
        self.assertEqual(self.profile.tiers[result.tier].effort, "low")

    def test_long_prompt_small_change_direct(self):
        result = local_decision("Fix typo in button label. " + "Context. " * 200, self.summary)
        self.assertEqual(result.intent, "DIRECT")

    def test_risky_and_cross_module_tasks_plan(self):
        for prompt in ("Simple database migration", "easy auth change", "payment update", "security fix", "feature across multiple modules"):
            with self.subTest(prompt=prompt):
                self.assertEqual(local_decision(prompt, self.summary).intent, "PLAN")

    def test_ambiguous_classifier_mock_and_failure_fallback(self):
        with patch("smartcodex.intent_gate.classify", return_value=__import__("smartcodex.intent_gate", fromlist=["IntentDecision"]).IntentDecision(
                "PLAN", "standard", "uncertain", (), "medium", .65, "unclear", True)) as classifier:
            result = decide("Make the requested improvement", self.summary, "codex", self.profile)
        classifier.assert_called_once()
        self.assertEqual(result.confidence, .65)
        with patch("smartcodex.intent_gate.classify", side_effect=RuntimeError("offline")):
            failed = decide("Make the requested improvement", self.summary, "codex", self.profile)
        self.assertEqual(failed.intent, "PLAN")
        self.assertTrue(failed.provisional)

    def test_v2_preview_and_plan_never_execute_codex(self):
        with patch.object(s.shutil, "which", return_value="codex.exe"), patch.object(s.subprocess, "run") as run:
            self.assertEqual(s.main(["Fix typo in button label", "--preview-intent"]), 0)
            self.assertEqual(s.main(["database migration", "--v2", "--mode", "exec", "--write"]), 3)
        self.assertFalse(any(call.args and call.args[0][0] == "codex.exe" for call in run.call_args_list))

    def test_fallback_sol_is_approval_gated(self):
        self.assertEqual(self.profile.fallback.model, "gpt-6.1-sol")
        self.assertTrue(self.profile.fallback_approval)
        self.assertTrue(self.profile.fallback.requires_approval)


if __name__ == "__main__":
    unittest.main()
