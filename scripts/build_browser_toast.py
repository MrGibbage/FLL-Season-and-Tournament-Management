"""Build the offline TOAST.html; optionally generate the automated browser suite.

python scripts/build_browser_toast.py --tests
Only tournaments/Dunford is used for local reference fixtures. All writes are
under browser-toast/, dist/, or workspace/; tournament files are never changed.
"""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jinja2 import Environment, meta

DEPENDENCIES = [
    ('fflate.js', 'fflate@0.8.2/umd/index.js', 'c3b34f2e9f5e74d4d7d64e01cac7a0c01954c6c406414d42185c7b53d6875ddf'),
    ('nunjucks.js', 'nunjucks@3.2.4/browser/nunjucks.min.js', '93769288b3eb63fff02d40406ba4d2d49f48b70f31576cdc330ee7f626856f3f'),
    ('fflate.LICENSE', 'fflate@0.8.2/LICENSE', None),
    ('nunjucks.LICENSE', 'nunjucks@3.2.4/LICENSE', None),
]


def script(source):
    # Bundled source maps are not distributed. Keep script boundaries off line
    # comments so HTML/JavaScript language services can parse each block cleanly.
    source = re.sub(r'^\s*//# sourceMappingURL=.*$', '', source, flags=re.M)
    return '<script>\n' + re.sub('</script', r'<\\/script', source, flags=re.I) + '\n</script>\n'


def build(include_tests=False, refresh_fixtures=False):
    vendor = ROOT / 'workspace/toast-browser-vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    for filename, url, checksum in DEPENDENCIES:
        path = vendor / filename
        if not path.exists():
            urllib.request.urlretrieve('https://cdn.jsdelivr.net/npm/' + url, path)
        if checksum and hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError('Dependency checksum mismatch: ' + filename)
    templates = {p.name: p.read_text(encoding='utf-8') for p in ROOT.glob('*_template-*.html.jinja') if p.name.startswith(('script_', 'summary_'))}
    env = Environment()
    assets = {'templates': templates, 'required': {k: sorted(meta.find_undeclared_variables(env.parse(v)) - {'bg_color_0', 'bg_color_1'}) for k, v in templates.items()}}
    source = ROOT / 'browser-toast'
    bundles = ''.join(script((vendor / name).read_text(encoding='utf-8')) for name in ['fflate.js', 'nunjucks.js'])
    bundles += script('const TOAST_ASSETS = ' + json.dumps(assets, ensure_ascii=True).replace('<', '\\u003c') + ';')
    bundles += ''.join(script((source / name).read_text(encoding='utf-8')) for name in ['core.js', 'app.js'])
    page = (source / 'index.html').read_text(encoding='utf-8')
    page = page.replace('/*STYLE*/', (source / 'style.css').read_text(encoding='utf-8'))
    notices = ''.join('<pre>' + html.escape((vendor / name).read_text(encoding='utf-8')) + '</pre>' for name in ['fflate.LICENSE', 'nunjucks.LICENSE'])
    page = page.replace('/*LICENSES*/', notices).replace('<!--BUNDLES-->', bundles)
    output = ROOT / 'dist/TOAST.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(page, encoding='utf-8')
    print(f'Built {output} ({output.stat().st_size:,} bytes; no sample data included)')
    if include_tests:
        import build_toast_browser_probe
        snapshot = ROOT / 'workspace/toast-browser-fixtures.json'
        probe_path = ROOT / 'workspace/toast-browser-test.html'
        if refresh_fixtures or not snapshot.exists() and not probe_path.exists():
            build_toast_browser_probe.main()
        if snapshot.exists() and not refresh_fixtures:
            data = json.loads(snapshot.read_text(encoding='utf-8'))
        else:
            probe = probe_path.read_text(encoding='utf-8')
            data = json.loads(re.search(r'<script>const PROBE = (.*?)</script>', probe, re.S).group(1))
        # Freeze input bytes, but regenerate expected outcomes through current
        # Python TOAST in isolation. Live Dunford edits never affect this run.
        from toast_browser_oracle import scenarios
        with tempfile.TemporaryDirectory(prefix='toast-fixtures-', dir=ROOT / 'workspace') as temp:
            regenerated = []
            for i, fixture in enumerate(data['fixtures']):
                directory = Path(temp) / str(i)
                directory.mkdir()
                for file in fixture['files']:
                    if Path(file['name']).name != file['name'] or '/' in file['name'] or '\\' in file['name']:
                        raise ValueError('Invalid fixture filename')
                    (directory / file['name']).write_bytes(base64.b64decode(file['base64']))
                regenerated.append(build_toast_browser_probe.fixture(directory, fixture['name']))
                if i == 0:
                    data['oracle'] = scenarios(directory)
            data['fixtures'] = regenerated
        snapshot.write_text(json.dumps(data, ensure_ascii=True), encoding='utf-8')
        # Intentional security correction: Python's title insertion is unescaped.
        # All other output bytes must match (apart from line-ending normalization).
        for fixture in data['fixtures']:
            old_name = re.search(r'<title>(.*?) Closing Ceremony Script</title>', fixture['reference']['outputs']['script']).group(1)
            for kind, content in fixture['reference']['outputs'].items():
                fixture['reference']['outputs'][kind] = content.replace(old_name, html.escape(old_name))
        harness = script('const TEST_DATA = ' + json.dumps(data, ensure_ascii=True) + ';') + script((source / 'tests.js').read_text(encoding='utf-8'))
        before, after = page.rsplit('</body>', 1)
        testpage = before + '<pre id="test-results" hidden></pre>' + harness + '</body>' + after
        target = ROOT / 'workspace/toast-browser-suite.html'
        target.write_text(testpage, encoding='utf-8')
        print(f'Built {target} ({len(data["oracle"])} Python oracle scenarios)')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests', action='store_true', help='Include private Dunford fixtures in a separate test harness')
    parser.add_argument('--refresh-fixtures', action='store_true', help='Explicitly replace the test snapshot from clean live Dunford files')
    args = parser.parse_args()
    build(args.tests, args.refresh_fixtures)
