"""MAESTRO distributes the TOAST binary for the host platform."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from modules.file_operations import available_toast_mappings, companion_toast_mapping, copy_files


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
            (source / 'fll-toast-macos-intel').write_bytes(b'Intel TOAST')
            (source / 'fll-toast-macos-apple-silicon').write_bytes(b'Apple silicon TOAST')
            template = source / 'template.xlsm'
            template.write_bytes(b'template')
            mappings = [companion_toast_mapping('win32')]
            mappings.extend({'source': name, 'dest': name} for name in
                            ('fll-toast-macos-intel', 'fll-toast-macos-apple-silicon'))
            copy_files(pd.Series({'Short Name': 'Example', 'OJS_FileName': 'example.xlsm'}),
                       str(source), str(template), mappings,
                       [], [], str(tournament_root), False)
            self.assertEqual((tournament_root / 'Example' / 'fll-toast.exe').read_bytes(),
                             b'current TOAST')
            self.assertEqual((tournament_root / 'Example' / 'fll-toast-macos-intel').read_bytes(),
                             b'Intel TOAST')
            self.assertEqual((tournament_root / 'Example' / 'fll-toast-macos-apple-silicon').read_bytes(),
                             b'Apple silicon TOAST')

    def test_director_folder_keeps_pdf_and_omits_authoring_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Example').mkdir()
            (root / 'instructions.pdf').write_bytes(b'instructions')
            (root / 'template.xlsm').write_bytes(b'OJS')
            for divisions in (False, True):
                copy_files(pd.Series({'Short Name': 'Example', 'OJS_FileName': 'example.xlsm'}),
                           str(root), str(root / 'template.xlsm'),
                           [{'source': 'instructions.pdf', 'dest': 'instructions.pdf'}],
                           [{'type': 'script_template', 'source': 'not-needed.jinja', 'dest': 'script_template.html.jinja'}],
                           [{'type': 'summary_template', 'source': 'not-needed.jinja', 'dest': 'summary_template.html.jinja'}],
                           str(root), divisions)
                self.assertEqual((root / 'Example/instructions.pdf').read_bytes(), b'instructions')
                self.assertFalse(list((root / 'Example').glob('*.jinja')))

    def test_extra_platform_binaries_are_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(available_toast_mappings(directory, 'win32'),
                             [companion_toast_mapping('win32')])
            (root / 'fll-toast-macos-intel').write_bytes(b'Intel')
            mappings = available_toast_mappings(directory, 'win32')
            self.assertEqual([entry['dest'] for entry in mappings],
                             ['fll-toast.exe', 'fll-toast-macos-intel'])
            (root / 'fll-toast-macos-apple-silicon').write_bytes(b'Apple')
            mappings = available_toast_mappings(directory, 'win32')
            self.assertEqual([entry['dest'] for entry in mappings],
                             ['fll-toast.exe', 'fll-toast-macos-intel',
                              'fll-toast-macos-apple-silicon'])


if __name__ == '__main__':
    unittest.main()
