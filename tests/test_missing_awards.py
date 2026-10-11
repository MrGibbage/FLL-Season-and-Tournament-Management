"""Focused checks for intentional unawarded regular places."""
import contextlib
import io
import json
import logging
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook

from modules.ceremony_data_collector import AwardWinner, CeremonyDataCollector
from modules.ceremony_validator import OJSValidator

ROOT = Path(__file__).resolve().parents[1]


class MissingAwardTests(unittest.TestCase):
    def config(self, divisions=True):
        return {"INFO": {"using_divisions": divisions}, "AWARDS": [
            {"ID": "J_AWD_CV", "Name": "Core Values", "DivAwd": divisions,
             "Labels": ["Core Values 1st Place", "Core Values 2nd Place"],
             "D1_count": 2, "D2_count": 1, "TournCount": 2},
            {"ID": "J_AWD_Judges", "Name": "Judges", "DivAwd": False,
             "Labels": ["Judges 1"], "TournCount": 1},
        ]}

    def results(self):
        return [("D1", pd.DataFrame({"Award": ["Core Values 2nd Place", "Judges 1"],
                                      "Robot Game Rank": [1, 2]})),
                ("D2", pd.DataFrame({"Award": [None], "Robot Game Rank": [1]}))]

    def test_regular_missing_places_listed_by_division(self):
        validator = OJSValidator()
        validator.validate_award_selections(self.config(), self.results())
        self.assertEqual(validator.missing_awards,
                         [("D1", "Core Values 1st Place"),
                          ("D2", "Core Values 1st Place")])
        self.assertFalse(validator.errors)

    def test_missing_judges_warns_and_unknown_remains_error(self):
        results = self.results()
        results[0][1].loc[1, "Award"] = None
        validator = OJSValidator()
        validator.validate_award_selections(self.config(), results)
        self.assertIn(("Tournament", "Judges Awards (0 of 1 selected)"),
                      validator.missing_awards)
        self.assertFalse(validator.errors)

        results[0][1].loc[1, "Award"] = "Unknown Award"
        validator = OJSValidator()
        validator.validate_award_selections(self.config(), results)
        self.assertIn("Unknown or unallocated award",
                      "\n".join(str(error) for error in validator.errors))
        results = self.results()
        results[0][1].loc[1, "Award"] = "Core Values 2nd Place"
        validator = OJSValidator()
        validator.validate_award_selections(self.config(), results)
        self.assertIn("found 2", "\n".join(str(error) for error in validator.errors))

    def test_judges_labels_are_interchangeable_and_count_is_tournament_wide(self):
        config = self.config()
        config['AWARDS'][1]['Labels'] = ['Judges 1', 'Judges 2', 'Judges 3']
        config['AWARDS'][1]['TournCount'] = 2
        for awards in [(['Judges 1', 'Judges 1'], []),
                       (['Judges 2'], ['Judges 2']),
                       ([], ['Judges 3', 'Judges 3'])]:
            with self.subTest(awards=awards):
                results = []
                for division, labels in zip(('D1', 'D2'), awards):
                    selections = (['Core Values 2nd Place'] if division == 'D1' else []) + labels
                    results.append((division, pd.DataFrame({
                        'Award': selections, 'Robot Game Rank': list(range(1, len(selections) + 1))
                    })))
                validator = OJSValidator()
                validator.validate_award_selections(config, results)
                self.assertFalse(validator.errors)
                self.assertFalse(any('Judges Awards' in label for _, label in validator.missing_awards))

        config['AWARDS'][1]['TournCount'] = 1
        results = self.results()
        results[0][1]['Award'] = ['Judges 1', 'Judges 1']
        validator = OJSValidator()
        validator.validate_award_selections(config, results)
        self.assertIn('Judges Awards: 2 selected, 1 allocated',
                      '\n'.join(str(error) for error in validator.errors))

    def test_duplicate_judges_label_is_logged_but_regular_duplicate_is_error(self):
        class Workbooks:
            def __init__(self, awards):
                self.awards = awards

            def table(self, path, sheet, name):
                return pd.DataFrame({'Award': self.awards})

        validator = OJSValidator(Workbooks(['Judges 1', 'Judges 1']))
        with self.assertLogs('ceremony_generator', level='INFO') as logs:
            self.assertTrue(validator.validate_award_duplicates('test.xlsm', judges_labels={'Judges 1'}))
        self.assertIn('Judges label', '\n'.join(logs.output))
        validator = OJSValidator(Workbooks(['Core Values 1st Place'] * 2))
        self.assertFalse(validator.validate_award_duplicates('test.xlsm', judges_labels={'Judges 1'}))

    def test_nondivision_missing_regular_award(self):
        config = self.config(False)
        results = [("", self.results()[0][1])]
        validator = OJSValidator()
        validator.validate_award_selections(config, results)
        self.assertEqual(validator.missing_awards,
                         [("Tournament", "Core Values 1st Place")])

    def test_robot_game_places_remain_hard_errors(self):
        config = {"INFO": {"using_divisions": False}, "AWARDS": [
            {"ID": "P_AWD_RG", "Name": "Robot Game", "DivAwd": False,
             "TournCount": 2},
        ]}
        results = [("", pd.DataFrame({"Award": [None], "Robot Game Rank": [1]}))]
        validator = OJSValidator()
        validator.validate_award_selections(config, results)
        self.assertIn("Robot Game awards have missing places",
                      "\n".join(str(error) for error in validator.errors))
        self.assertFalse(validator.missing_awards)

    def test_prompt_requires_exact_yes(self):
        module = runpy.run_path(str(ROOT / "fll-toast.py"),
                                init_globals={"logger": logging.getLogger("test")})
        for response, accepted in [("", False), ("yes", False), ("NO", False),
                                   ("YES", True), (" YES ", True)]:
            with self.subTest(response=response), \
                    patch("builtins.input", return_value=response), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(module["confirm_missing_awards"](
                    [("D1", "Core Values 1st Place")]), accepted)
                self.assertIn("WARN: AWARDS WITHOUT WINNERS", output.getvalue())
                self.assertIn("Core Values 1st Place in Division 1", output.getvalue())

    def test_none_keeps_places_and_division(self):
        collector = CeremonyDataCollector({})
        html = collector.format_allocated_awards_as_html(
            [AwardWinner(123, "Example", "Core Values 2nd Place")],
            ["Core Values 1st Place", "Core Values 2nd Place"], "Division 1")
        self.assertLess(html.index("2nd Place"), html.index("1st Place"))
        self.assertIn("Division 1 Core Values 1st Place: NONE", html)
        self.assertIn("Division 1 Core Values 2nd Place: Team 123", html)

    def test_toast_writes_none_only_after_yes(self):
        module = runpy.run_path(str(ROOT / "fll-toast.py"))
        config = {"INFO": {"using_divisions": False, "tournament_long_name": "Test",
                           "ojs_files": [{"filename": "test.xlsm"}],
                           "script_template": "script.jinja",
                           "summary_template": "summary.jinja"},
                  "AWARDS": [
                      {"ID": "J_AWD_CV", "Name": "Core Values", "DivAwd": False,
                       "Labels": ["Core Values 1st Place"], "TournCount": 1,
                       "ScriptTagNoDiv": "J_AWD_CV"},
                      {"ID": "J_AWD_Judges", "Name": "Judges", "DivAwd": False,
                       "Labels": ["Judges 1", "Judges 2"], "TournCount": 2,
                       "ScriptTagNoDiv": "J_AWD_Judges"},
                  ]}
        results = pd.DataFrame({"Team #": [1, 2], "Team Name": ["Alpha", "Beta"],
                                "Award": ["Judges 1", None],
                                "Advance?": ["No", "No"],
                                "Robot Game Rank": [1, 2]})

        class Workbooks:
            def __init__(self):
                self.book = Workbook()
                self.book.active.title = "Team and Program Information"

            def workbook(self, path):
                return self.book

            def table(self, path, sheet, name):
                return results.copy() if name == "TournamentData" else results[["Team #", "Team Name"]].copy()

        def validate_tournament(validator, config, base_dir):
            validator.validate_award_selections(config, [("", results)])

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "test.xlsm").touch()
            (base / "tournament_config.json").write_text(json.dumps(config))
            for filename in ("script.jinja", "summary.jinja"):
                (base / filename).write_text("{{ J_AWD_CV|safe }} {{ J_AWD_Judges|safe }}")
            output = base / "output"
            argv = ["toast", "--tournament-dir", folder, "--output-dir", str(output)]
            try:
                for response in ("", "yes"):
                    with patch("sys.argv", argv), patch("builtins.input", side_effect=["", response]), \
                            patch.object(OJSValidator, "validate_all_sheets", return_value=True), \
                            patch.object(OJSValidator, "validate_tournament", validate_tournament), \
                            contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(SystemExit) as stopped:
                            module["main"](Workbooks())
                    self.assertEqual(stopped.exception.code, 1)
                    self.assertFalse(list(output.glob("*.html")))
                with patch("sys.argv", argv), patch("builtins.input", side_effect=["", "YES", ""]), \
                        patch.object(OJSValidator, "validate_all_sheets", return_value=True), \
                        patch.object(OJSValidator, "validate_tournament", validate_tournament), \
                        contextlib.redirect_stdout(io.StringIO()):
                    module["main"](Workbooks())
                script = next(output.glob("*closing-ceremony.html")).read_text()
                self.assertIn("Core Values 1st Place: NONE", script)
                self.assertIn("Judges Award: Team 1, Alpha", script)
                self.assertIn("Judges Award: NONE", script)
            finally:
                logger = logging.getLogger("ceremony_generator")
                for handler in list(logger.handlers):
                    handler.close()
                    logger.removeHandler(handler)
