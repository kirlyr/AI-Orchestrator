from pathlib import Path
import sys
import unittest
from unittest.mock import patch

# Test the package in this repository instead of any separately installed copy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import smartcodex.cli as s

class RouterTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(s.rules_route("Ubah warna tombol login jadi biru").tier, "luna-low")
    def test_safe_routine(self):
        self.assertEqual(s.rules_route("Tambahkan validasi untuk form" ).tier, "sol-low")
    def test_risky_complex(self):
        self.assertEqual(s.rules_route("Audit security dan refactor arsitektur auth").tier, "sol-high")
    def test_astra_capped(self):
        self.assertEqual(s.capped(s.Decision("astra-high", "critical"), False).tier, "sol-high")
    def test_force_dry_run(self):
        self.assertEqual(s.main(["Ubah warna tombol", "--dry-run"]), 0)
    def test_missing_prompt(self):
        self.assertEqual(s.main(["--dry-run"]), 2)
    def test_no_ai_when_confident(self):
        with patch.object(s, "ai_route", side_effect=AssertionError("should not call AI")):
            self.assertEqual(s.select_route("Ubah warna tombol", "smart", "codex", False).tier, "luna-low")

    def test_legacy_cli_flags_and_tier_mapping(self):
        args = s.cli_args([
            "prompt", "--file", "prompt.txt", "--router", "rules", "--mode", "exec",
            "--force-tier", "sol-low", "--allow-astra", "--write", "--dry-run",
        ])
        self.assertEqual(args.router, "rules")
        self.assertEqual(args.mode, "exec")
        self.assertEqual(args.force_tier, "sol-low")
        self.assertEqual(s.TIERS["sol-low"], ("gpt-6.1-sol", "low"))

    def test_dry_run_does_not_need_codex(self):
        with patch.object(s.shutil, "which", return_value=None):
            self.assertEqual(s.main(["Ubah warna tombol", "--dry-run"]), 0)

if __name__ == "__main__":
    unittest.main()
