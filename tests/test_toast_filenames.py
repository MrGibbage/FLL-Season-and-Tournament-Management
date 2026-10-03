import logging
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OutputFilenameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module = runpy.run_path(str(ROOT / "fll-toast.py"),
                               init_globals={"logger": logging.getLogger("test")})
        cls.generate = staticmethod(module["generate_output_filename"])

    def test_combined_divisions(self):
        stem = "2026-vadc-fll-challenge-Unearthed-ojs-Dunford"
        for marker in ["D", "-D", "_D", "-div", "d"]:
            for first, second in [(1, 2), (2, 1)]:
                files = [{"filename": f"{stem}{marker}{n}.xlsm", "division": f"D{n}"}
                         for n in [first, second]]
                for suffix in ["closing-ceremony", "summary"]:
                    with self.subTest(marker=marker, first=first, suffix=suffix):
                        self.assertEqual(self.generate(files, suffix), f"{stem}-{suffix}.html")

    def test_single_file_preserves_division(self):
        for stem in ["DunfordD1", "DunfordD2", "Dunford"]:
            self.assertEqual(self.generate([{"filename": stem + ".xlsm"}]),
                             stem + "-closing-ceremony.html")

    def test_only_trailing_division_is_removed(self):
        self.assertEqual(self.generate(["D1-TournamentD1.xlsm", "D1-TournamentD2.xlsm"]),
                         "D1-Tournament-closing-ceremony.html")
        self.assertEqual(self.generate(["Tournament.xlsm", "Other.xlsm"]),
                         "Tournament-closing-ceremony.html")
