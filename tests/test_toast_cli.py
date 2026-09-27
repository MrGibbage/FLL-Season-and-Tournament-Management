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
