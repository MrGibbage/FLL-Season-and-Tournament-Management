import contextlib
import io
import json
import logging
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from modules.season_config import program_season_name, tournament_identity, using_divisions, single_division_code
from modules.worksheet_setup import set_up_meta_worksheet
from modules.constants import (COL_SHORT_NAME, COL_LONG_NAME, COL_ADVANCING, COL_OJS_FILENAME)

ROOT = Path(__file__).resolve().parents[1]

class SeasonConfigTests(unittest.TestCase):
    def test_single_division_requires_explicit_identity(self):
        self.assertEqual(single_division_code({"Div": "D2"}), "D2")
        self.assertEqual(single_division_code({"Div": "d1"}), "D1")
        for value in [None, "", 0, "D3"]:
            with self.assertRaises(ValueError):
                single_division_code({"Short Name": "Test", "Div": value})

    def test_discovery_requires_nested_name(self):
        with contextlib.redirect_stdout(io.StringIO()):
            maestro = runpy.run_path(str(ROOT / 'fll-maestro.py'), init_globals={'logger': logging.getLogger('test')})
        config = json.loads((ROOT / 'qualifiers-with-divisions.json').read_text())
        self.assertNotIn('season_name', config)
        self.assertEqual(program_season_name(config), 'Bioglow')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'season.json'
            path.write_text(json.dumps(config))
            self.assertEqual(maestro['find_season_config_files'](directory), ['season.json'])
            for invalid in ['', None, 123]:
                config['ceremony']['program_season_name'] = invalid
                path.write_text(json.dumps(config))
                self.assertEqual(maestro['find_season_config_files'](directory), [])

    def test_workbook_metadata_uses_nested_name_and_top_level_year(self):
        config = {'season_yr': '2026', 'ceremony': {'program_season_name': 'Bioglow'}}
        tournament = {COL_SHORT_NAME: 'Test', COL_LONG_NAME: 'Test Tournament',
                      COL_ADVANCING: 1, COL_OJS_FILENAME: 'test.xlsm'}
        with patch('modules.worksheet_setup.add_table_dataframe') as write:
            set_up_meta_worksheet(tournament, None, config, 'tournaments', False)
        metadata = write.call_args.args[3].set_index('Key')['Value']
        self.assertEqual(metadata['FLL Season Title'], 'Bioglow')
        self.assertEqual(metadata['Tournament Year'], '2026')


class TournamentIdentityTests(unittest.TestCase):
    def test_json_overrides_stale_workbook_names(self):
        for suffix, divisions in [("with-divisions", True), ("without-divisions", False)]:
            config = json.loads((ROOT / f"qualifiers-{suffix}.json").read_text())
            row = {"Short Name": "Dunford", "Div": "D2",
                   "Long Name": "Dunford 2025 Unearthed",
                   "OJS_FileName": "stale.xlsm"}
            identity = tournament_identity(row, config)
            self.assertEqual(identity["Long Name"], "Dunford 2026 Bioglow Qualifier Tournament")
            division = "D2" if divisions else ""
            self.assertEqual(identity["OJS_FileName"],
                             f"2026-vadc-fll-challenge-Bioglow-ojs-Dunford{division}.xlsm")
            config['season_yr'] = '2027'
            config['ceremony']['program_season_name'] = 'Future'
            self.assertIn('2027 Future', tournament_identity(row, config)['Long Name'])

    def test_explicit_division_mode_required(self):
        for value in [None, 'False', 0, 1]:
            with self.assertRaises(ValueError):
                using_divisions({'using_divisions': value})

    def test_unsafe_generated_path_rejected(self):
        config = {'season_yr': '2026', 'ceremony': {'program_season_name': 'Bioglow'},
                  'using_divisions': False, 'ojs_filename_format': '../{short_name}.xlsm'}
        with self.assertRaises(ValueError):
            tournament_identity({'Short Name': 'Dunford'}, config)
