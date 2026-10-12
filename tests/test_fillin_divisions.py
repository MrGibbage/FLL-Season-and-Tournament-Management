"""Regression coverage for division forms and summary advancement."""
import ast
from pathlib import Path
import unittest
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
source = ast.parse((ROOT / "fll-maestro.py").read_text(encoding="utf-8"))
function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "build_fillin_template_data")
from modules.tournament_assets import tournament_display_title
namespace = {"tournament_display_title": tournament_display_title}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(ROOT / "fll-maestro.py"), "exec"), namespace)
build_data = namespace["build_fillin_template_data"]

class DivisionFormsTests(unittest.TestCase):
    def test_unequal_allocations_and_custom_labels(self):
        config = {"INFO": {"using_divisions": True, "advancing_count_d1": 1, "advancing_count_d2": 2},
                  "AWARDS": [{"ID": "J_AWD_IP", "Name": "Project", "DivAwd": True,
                              "Labels": ["Custom winner", "Custom runner-up"], "D1_count": 1, "D2_count": 2},
                             {"ID": "J_AWD_Judges", "Name": "Judges", "DivAwd": False,
                              "TournCount": 2}]}
        data = build_data(config)
        self.assertEqual(data["rows_core"], ["Division 1 (D1): Custom winner", "Division 2 (D2): Custom winner", "Division 2 (D2): Custom runner-up"])
        self.assertEqual(len(data["rows_judges"]), 2)
        env = Environment(loader=FileSystemLoader(str(ROOT)))
        html = env.get_template("fillin_template-with-divisions.html.jinja").render(**data)
        self.assertEqual(html.count(": Advancing Team"), 3)
        self.assertEqual(html.count(": Alternate"), 2)
        self.assertIn("Tournament-wide", html)

    def test_summary_with_only_d2_advancement(self):
        env = Environment(loader=FileSystemLoader(str(ROOT)))
        html = env.get_template("summary_template-with-divisions.html.jinja").render(ADV_D2="<p>Team 123</p>")
        self.assertIn("<h2>Advancing Teams</h2>", html)
        self.assertIn("Division 2 (D2)", html)
        self.assertIn("Team 123", html)
        self.assertNotIn("Division 1 (D1)", html)

    def test_nondivision_count(self):
        data = build_data({"INFO": {"using_divisions": False, "advancing_count": 4}, "AWARDS": []})
        self.assertEqual(data["adv_count"], 4)

    def test_brindlewick_saved_form(self):
        import json
        path = ROOT / "tournaments/Brindlewick/tournament_config.json"
        if not path.exists():
            self.skipTest("Requires local Brindlewick fixture")
        data = build_data(json.loads(path.read_text(encoding="utf-8")))
        html = Environment(loader=FileSystemLoader(str(ROOT))).get_template(
            "fillin_template-without-divisions.html.jinja").render(**data)
        self.assertEqual(html.count('class="blank short"'), 19)  # 15 awards, 3 advancing, 1 alternate
        self.assertNotIn("Division 1", html)
        self.assertEqual(html.count('>Alternate</td>'), 1)
