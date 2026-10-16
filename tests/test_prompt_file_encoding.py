"""Regression tests for UTF-8 prompt file handling (Issue #1)."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

# Import SmartCodex from this repository checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import smartcodex.cli as s


class PromptFileEncodingTests(unittest.TestCase):
    def test_invalid_utf8_reports_error_without_traceback(self):
        with TemporaryDirectory() as folder:
            prompt_file = Path(folder) / "invalid-prompt.txt"
            prompt_file.write_bytes(b"\xff")
            stderr = StringIO()
            with patch.object(s.shutil, "which") as which, redirect_stderr(stderr):
                exit_code = s.main(["--file", str(prompt_file), "--dry-run"])

        self.assertEqual(exit_code, 2)
        self.assertIn("Tidak bisa membaca file", stderr.getvalue())
        self.assertIn("utf-8", stderr.getvalue().lower())
        self.assertNotIn("Traceback", stderr.getvalue())
        which.assert_not_called()

    def test_valid_utf8_file_still_works_in_dry_run(self):
        with TemporaryDirectory() as folder:
            prompt_file = Path(folder) / "valid-prompt.txt"
            prompt_file.write_text("Ubah warna tombol login", encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout), patch.object(s.shutil, "which", return_value=None), \
                    patch.object(s.subprocess, "run") as run:
                exit_code = s.main(["--file", str(prompt_file), "--dry-run"])

        self.assertEqual(exit_code, 0)
        self.assertIn("DRY RUN", stdout.getvalue())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
