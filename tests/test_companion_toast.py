"""MAESTRO distributes the TOAST binary for the host platform."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from modules.file_operations import companion_toast_mapping, copy_files


class CompanionToastTests(unittest.TestCase):
    def test_platform_filenames(self):
        self.assertEqual(companion_toast_mapping('win32'),
                         {'source': 'fll-toast.exe', 'dest': 'fll-toast.exe'})
        self.assertEqual(companion_toast_mapping('darwin'),
                         {'source': 'fll-toast', 'dest': 'fll-toast'})

    def test_copy_files_places_companion_in_tournament_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            tournament_root = root / 'tournaments'
            (tournament_root / 'Example').mkdir(parents=True)
            (source / 'fll-toast.exe').write_bytes(b'current TOAST')
            template = source / 'template.xlsm'
            template.write_bytes(b'template')
            copy_files(pd.Series({'Short Name': 'Example', 'OJS_FileName': 'example.xlsm'}),
                       str(source), str(template), [companion_toast_mapping('win32')],
                       [], [], str(tournament_root), False)
            self.assertEqual((tournament_root / 'Example' / 'fll-toast.exe').read_bytes(),
                             b'current TOAST')


if __name__ == '__main__':
    unittest.main()
