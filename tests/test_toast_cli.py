"""Exercise source-mode TOAST with isolated output and real saved OJS scores."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ToastCliTests(unittest.TestCase):
    def test_nondivision_from_project_with_separate_output(self):
        source = ROOT / "tournaments/Dunford/tournament_config.json"
        if not source.exists():
            self.skipTest("Requires the local scored Dunford fixture")
        config = json.loads(source.read_text(encoding="utf-8"))
        info = config["INFO"]
        entry = info["ojs_files"][0]
        entry["filename"] = str(source.parent / entry["filename"])
        entry["division"] = ""
        info["ojs_files"] = [entry]
        info["using_divisions"] = False
        # This fixture tests CLI paths and the nondivision render branch,
        # not the tournament's division-specific award allocations.
        info["advancing_count"] = info["advancing_count_d1"]
        for award in config["AWARDS"]:
            if award["DivAwd"]:
                award["TournCount"] = award["D1_count"]
                award["ScriptTagNoDiv"] = award["ScriptTagD1"]
            elif award["ID"] == "J_AWD_Judges":
                award["TournCount"] = 1
            award["DivAwd"] = False
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            assets = base / "assets"
            assets.mkdir()
            output = base / "output"
            (assets / "tournament_config.json").write_text(json.dumps(config), encoding="utf-8")
            for key in ["script_template", "summary_template"]:
                info[key] = key + ".html.jinja"
                (assets / info[key]).write_text(
                    "{{ tournament_name }} {{ team_list }} {{ ADV }}", encoding="utf-8"
                )
            (assets / "tournament_config.json").write_text(json.dumps(config), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "fll-toast.py"), "--tournament-dir", str(assets),
                 "--output-dir", str(output)],
                cwd=ROOT, input="\ny\n\n", capture_output=True, text=True,
                encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            files = list(output.glob("*.html"))
            self.assertEqual(len(files), 2)
            self.assertTrue(list(output.glob("*.log")))
            self.assertFalse(list(assets.glob("*.html")))
            for path in files:
                text = path.read_text(encoding="utf-8")
                self.assertIn(info["tournament_long_name"], text)
                self.assertIn("Team ", text)

    def test_saved_tournaments_include_alternates_in_summary(self):
        for name, suffix, alternates in [
            ("Dunford", "with-divisions", [43930, 65394]),
            ("Brindlewick", "without-divisions", [71574]),
        ]:
            with self.subTest(tournament=name), tempfile.TemporaryDirectory() as directory:
                folder = ROOT / "tournaments" / name
                if not (folder / "tournament_config.json").exists():
                    self.skipTest("Requires local scored tournament fixtures")
                config = json.loads((folder / "tournament_config.json").read_text(encoding="utf-8"))
                config["INFO"]["dual_emcee"] = True
                base = Path(directory)
                for entry in config["INFO"]["ojs_files"]:
                    entry["filename"] = str(folder / entry["filename"])
                for key in ["script_template", "summary_template"]:
                    (base / config["INFO"][key]).write_bytes(
                        (ROOT / f"{key}-{suffix}.html.jinja").read_bytes())
                (base / "tournament_config.json").write_text(json.dumps(config), encoding="utf-8")
                import io
                import runpy
                from unittest.mock import patch
                from modules.ceremony_workbooks import CeremonyWorkbooks
                cache = CeremonyWorkbooks()
                try:
                    # Set the actual OJS toggle in memory; keep saved score caches and files intact.
                    for entry in config["INFO"]["ojs_files"]:
                        cache.workbook(entry["filename"])["Team and Program Information"]["F2"] = True
                    with patch("sys.argv", ["fll-toast.py", "--tournament-dir", str(base)]), \
                         patch("builtins.input", return_value="y"), patch("sys.stdout", new=io.StringIO()):
                        runpy.run_path(str(ROOT / "fll-toast.py"))["main"](cache)
                finally:
                    cache.close()
                ceremony = next(base.glob("*-closing-ceremony.html")).read_text(encoding="utf-8")
                self.assertIn("background-color: lightblue", ceremony)
                self.assertIn("background-color: yellow", ceremony)
                self.assertIn("<h2>Advancing Teams</h2>", ceremony)
                import re
                colors = re.findall(r'<span class="highlight([01])">', ceremony)
                self.assertGreater(len(colors), 30)
                changes = sum(left != right for left, right in zip(colors, colors[1:]))
                self.assertGreater(changes / (len(colors) - 1), 0.65)
                summary = next(base.glob("*-summary.html")).read_text(encoding="utf-8")
                alternate_section = summary.split("<h2>Alternate", 1)[1]
                for number in alternates:
                    self.assertIn(f"Team {number},", alternate_section)
                if name == "Brindlewick":
                    for number in [72326, 72066, 71459]:
                        self.assertIn(f"Team {number},", summary.split("<h2>Alternate", 1)[0])
                    self.assertNotIn("Division 1", summary)
