"""Build an offline browser feasibility probe with local, Python-verified samples.

Run with .venv/Scripts/python.exe scripts/build_toast_browser_probe.py.
Requires pinned fflate and Nunjucks bundles in workspace/toast-browser-vendor/.
Generated HTML contains local tournament data; it is for local testing.
"""
import base64
import contextlib
import copy
import hashlib
import html
import io
import json
import logging
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch
import warnings
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.ceremony_workbooks import CeremonyWorkbooks
from modules.ceremony_validator import OJSValidator
from modules.tournament_assets import discover_embedded_config, write_embedded_config
from openpyxl import load_workbook


def fixture(directory, name):
    cache = CeremonyWorkbooks()
    try:
        config = discover_embedded_config(directory, cache)[0]
        validator = OJSValidator(cache, config['INFO'].get('robot_game_max_score', 530))
        labels = next((set(a['Labels']) for a in config['AWARDS'] if a['ID'] == 'J_AWD_Judges'), set())
        files, tables = [], {}
        for entry in config['INFO']['ojs_files']:
            path = directory / entry['filename']
            validator.validate_all_sheets(str(path), entry['division'], judges_labels=labels)
            book = cache.workbook(str(path))
            tables[path.name] = {}
            for sheet in book:
                for table_name in sheet.tables:
                    table = sheet.tables[table_name]
                    rows = list(sheet[table.ref])
                    normalize = lambda v: (v.strip() or None) if isinstance(v, str) else v
                    tables[path.name][table_name] = {
                        'sheet': sheet.title, 'ref': table.ref,
                        'headers': [str(c.value).strip() for c in rows[0]],
                        'rows': [[normalize(c.value) for c in row] for row in rows[1:]],
                    }
            files.append({'name': path.name, 'base64': base64.b64encode(path.read_bytes()).decode()})
        validator.validate_tournament(config, str(directory))
        if validator.errors:
            raise RuntimeError(f'{name}: baseline is invalid: {[str(e) for e in validator.errors]}')
        with tempfile.TemporaryDirectory() as out:
            module = runpy.run_path(str(ROOT / 'fll-toast.py'))
            try:
                with patch('sys.argv', ['toast', '--tournament-dir', str(directory), '--output-dir', out]), patch('builtins.input', return_value='YES'), contextlib.redirect_stdout(io.StringIO()):
                    module['main'](cache)
            finally:
                for handler in list(logging.getLogger('ceremony_generator').handlers):
                    handler.close()
                    logging.getLogger('ceremony_generator').removeHandler(handler)
            outputs = {
                'script': next(Path(out).glob('*closing-ceremony.html')).read_text(encoding='utf-8'),
                'summary': next(Path(out).glob('*summary.html')).read_text(encoding='utf-8'),
            }
            for handler in list(logging.getLogger('ceremony_generator').handlers):
                handler.close()
                logging.getLogger('ceremony_generator').removeHandler(handler)
        return {'name': name, 'files': files, 'reference': {
            'tables': tables, 'outputs': outputs,
            'expected': {'errors': 0, 'warnings': len(validator.warnings), 'missing': len(validator.missing_awards)},
        }}
    finally:
        cache.close()
        for handler in list(logging.getLogger('ceremony_generator').handlers):
            handler.close()
            logging.getLogger('ceremony_generator').removeHandler(handler)


def main():
    warnings.simplefilter('ignore', UserWarning)
    vendor = ROOT / 'workspace/toast-browser-vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    dependencies = [
        ('fflate.js', 'fflate@0.8.2/umd/index.js', 'c3b34f2e9f5e74d4d7d64e01cac7a0c01954c6c406414d42185c7b53d6875ddf'),
        ('nunjucks.js', 'nunjucks@3.2.4/browser/nunjucks.min.js', '93769288b3eb63fff02d40406ba4d2d49f48b70f31576cdc330ee7f626856f3f'),
        ('fflate.LICENSE', 'fflate@0.8.2/LICENSE', None),
        ('nunjucks.LICENSE', 'nunjucks@3.2.4/LICENSE', None),
    ]
    for filename, url, checksum in dependencies:
        path = vendor / filename
        if not path.exists():
            urllib.request.urlretrieve('https://cdn.jsdelivr.net/npm/' + url, path)
        if checksum and hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError('Dependency checksum mismatch: ' + filename)
    libraries = [(vendor / name).read_text(encoding='utf-8') for name in ['fflate.js', 'nunjucks.js']]
    real = ROOT / 'tournaments/Dunford'
    fixtures = [fixture(real, 'Real two-division Dunford OJS files')]
    # A controlled single-division fixture uses saved values from real D1. This
    # exercises the other templates; it is not presented as a real single event.
    cache = CeremonyWorkbooks()
    config = copy.deepcopy(discover_embedded_config(real, cache)[0])
    cache.close()
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        source = real / config['INFO']['ojs_files'][0]['filename']
        book = load_workbook(source, data_only=True, keep_vba=True)
        info = config['INFO']
        info.update(using_divisions=False, division_label='Single Division',
                    tournament_long_name='Single Division Browser Test & Compatibility',
                    ojs_files=[{'division': '', 'filename': 'single-division-test.xlsm'}],
                    advancing_count=info['advancing_count_d1'])
        # Read award selections by table header instead of assuming its column.
        sheet = book['Results and Rankings']
        rows = list(sheet[sheet.tables['TournamentData'].ref])
        headers = [c.value for c in rows[0]]
        selected = [row[headers.index('Award')].value for row in rows[1:]]
        for award in config['AWARDS']:
            if award['DivAwd']:
                award['TournCount'] = award['D1_count']
                award['ScriptTagNoDiv'] = award.get('ScriptTagD1', '').removesuffix('_D1')
            if award['ID'] == 'J_AWD_Judges':
                award['TournCount'] = sum(v in award['Labels'] for v in selected)
            award['DivAwd'] = False
        book['Team and Program Information']['F2'] = True
        write_embedded_config(book, config)
        book.save(directory / 'single-division-test.xlsm')
        book.close()
        if book.vba_archive:
            book.vba_archive.close()
        fixtures.append(fixture(directory, 'Controlled single-division / dual-emcee case'))
    templates = {p.name: p.read_text(encoding='utf-8') for p in ROOT.glob('*_template-*.html.jinja') if p.name.startswith(('script_', 'summary_'))}
    probe = {'version': '0.1.0', 'templates': templates, 'fixtures': fixtures}
    js = (ROOT / 'scripts/toast-browser-probe.js').read_text(encoding='utf-8')
    def script(s):
        return '<script>' + s.replace('</script', '<\\/script') + '</script>'
    head = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; connect-src 'none'; img-src data: blob:">
<title>TOAST browser compatibility test</title>
<style>body{font:16px system-ui;max-width:1050px;margin:36px auto;padding:0 24px;background:#f3f5f7;color:#17263c}h1{margin-bottom:8px}section{background:white;padding:24px;border-radius:12px;margin:18px 0}button,input{font:inherit;margin:6px 8px 6px 0}button{padding:10px 16px;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;max-height:65vh;overflow:auto}small{color:#485b70}#status{font-weight:600}code{background:#e9eef4;padding:2px 5px}</style>
<h1>TOAST browser compatibility test</h1>
<p>A local feasibility experiment. Your OJS files stay on this computer. No server, installation, or internet connection is needed.</p>
<section><h2>1. Run the reference tests</h2><p>Includes actual two-division OJS workbooks and a controlled single-division case. Compares extracted tables and both HTML documents with Python TOAST, then tests failure cases.</p><button id="samples">Run built-in tests</button><small>Bundled samples contain local tournament data. Keep this test file private.</small></section>
<section><h2>2. Try your tournament</h2><p>Select one OJS file, or both division files together. For older OJS files, also select <code>tournament_config.json</code>. Save changes in Excel first. Reselect files after editing.</p><input id="files" type="file" accept=".xlsm,.xlsx,.json" multiple><p>Custom files run browser checks; Python parity comparisons apply only to the bundled reference cases. This prototype does not implement every configuration guard in production TOAST.</p><div id="downloads"></div></section>
<section><h2>Results</h2><p id="status" role="status" aria-live="polite">Ready. For an offline test, disconnect your network, reopen this file, and run the tests.</p><button id="export">Download test report</button><pre id="report">No tests run yet.</pre></section>
'''
    runtime_size = len((head + ''.join(script(s) for s in libraries) + script('const PROBE = ' + json.dumps({**probe, 'fixtures': []})) + script(js)).encode())
    head += f'<p><small>Runtime and templates: {runtime_size:,} bytes before compression. Bundled reference workbooks and expected outputs increase this test file’s size. Libraries: fflate 0.8.2 (MIT), Nunjucks 3.2.4 (BSD-2-Clause); original license notices retained.</small></p>'
    head += '<details><summary>Third-party license notices</summary>' + ''.join(
        '<pre>' + html.escape((vendor / name).read_text(encoding='utf-8')) + '</pre>'
        for name in ['fflate.LICENSE', 'nunjucks.LICENSE']) + '</details>'
    output = ROOT / 'workspace/toast-browser-test.html'
    output.write_text(head + ''.join(script(s) for s in libraries) + script('const PROBE = ' + json.dumps(probe, ensure_ascii=True)) + script(js) + '</html>', encoding='utf-8')
    print(json.dumps({'file': str(output), 'bytes': output.stat().st_size, 'runtimeBytes': runtime_size, 'fixtures': [f['name'] for f in fixtures]}, indent=2))


if __name__ == '__main__':
    main()
