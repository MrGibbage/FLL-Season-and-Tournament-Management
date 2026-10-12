"""Open/locked OJS files should show recovery instructions, not a console traceback."""
import io
import logging
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class WorkbookAccessTests(unittest.TestCase):
    def test_open_and_permission_denied_are_friendly(self):
        for reason in ("excel-lock", "permission-denied"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                workbook = folder / "DunfordD1.xlsm"
                workbook.touch()
                if reason == "excel-lock":
                    (folder / "~$DunfordD1.xlsm").touch()
                previous = folder / "previous-summary.html"
                previous.write_text("Keep prior results")
                console = io.StringIO()
                module = runpy.run_path(str(ROOT / "fll-toast.py"))
                try:
                    with patch("sys.argv", ["toast", "--tournament-dir", str(folder), "--output-dir", str(folder)]), \
                         patch("builtins.input", return_value="") as prompt, patch("sys.stdout", console), \
                         patch("modules.ceremony_workbooks.load_workbook", side_effect=PermissionError(13, "Permission denied", str(workbook))) as load:
                        with self.assertRaises(SystemExit) as exit_error:
                            module["main"]()
                        self.assertEqual(exit_error.exception.code, 1)
                        self.assertEqual(load.call_count, 0 if reason == "excel-lock" else 1)
                    output = console.getvalue()
                    self.assertIn("DunfordD1.xlsm", output)
                    self.assertIn("Save and close", output)
                    prompt.assert_called_once_with("Press ENTER to exit...")
                    self.assertNotIn("Traceback", output)
                    self.assertNotIn("PermissionError", output)
                    log = next(folder.glob("ceremony_generator_*.log")).read_text(encoding="utf-8")
                    self.assertIn("Traceback", log)
                    self.assertIn(str(workbook), log)
                    self.assertEqual(previous.read_text(), "Keep prior results")
                finally:
                    logger = logging.getLogger("ceremony_generator")
                    for handler in list(logger.handlers):
                        handler.close()
                        logger.removeHandler(handler)
