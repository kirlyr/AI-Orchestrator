"""Regression tests for SmartCodex CLI argument guardrails."""

import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

# Test this repository checkout, not a separately installed copy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import smartcodex.cli as cli


class CliGuardrailTests(unittest.TestCase):
    def test_write_is_rejected_in_chat_mode(self):
        stderr = io.StringIO()
        with patch.object(
            cli.shutil, "which", side_effect=AssertionError("Codex must not be queried")
        ), redirect_stderr(stderr):
            result = cli.main(["hello", "--mode", "chat", "--write"])

        self.assertEqual(result, 2)
        self.assertIn("--write", stderr.getvalue())

    
    def test_file_and_positional_prompt_are_mutually_exclusive(self):
        stderr = io.StringIO()

        with patch.object(
            cli.shutil,
            "which",
            side_effect=AssertionError("Codex must not be queried"),
        ):
            with redirect_stderr(stderr):
                result = cli.main([
                    "hello",
                    "--file",
                    "prompt.txt",
                    "--dry-run",
                ])

        self.assertEqual(result, 2)
        self.assertIn("ATAU --file", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
