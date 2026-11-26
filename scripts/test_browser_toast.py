"""Build and run the offline browser suite in installed Chrome and/or Edge.

Exit status is nonzero for assertion failures, missing results, or browser errors.
Reports are saved to workspace/browser-toast-results-<browser>.json.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from build_browser_toast import ROOT, build


def find_browser(name):
    candidates = {
        'chrome': [os.environ.get('TOAST_CHROME'), shutil.which('google-chrome'), shutil.which('chromium'), 'C:/Program Files/Google/Chrome/Application/chrome.exe', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'],
        'edge': [os.environ.get('TOAST_EDGE'), shutil.which('microsoft-edge'), 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'],
    }
    return next((Path(p) for p in candidates[name] if p and Path(p).is_file()), None)


def run(browser, executable):
    work = ROOT / 'workspace'
    with tempfile.TemporaryDirectory(prefix='toast-test-', dir=work) as profile:
        path = work / f'browser-toast-results-{browser}.json'
        path.unlink(missing_ok=True)
        cmd = ['node', str(ROOT / 'scripts/run_browser_toast.mjs'), str(executable), profile, (work / 'toast-browser-suite.html').as_uri(), str(path), (ROOT / 'dist/INSTRUCTIONS.html').as_uri()]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', timeout=100)
        (work / f'browser-toast-{browser}.stderr.log').write_text(result.stderr, encoding='utf-8')
        if not path.exists():
            raise RuntimeError(f'{browser}: browser did not emit a report. {result.stderr}')
        report = json.loads(path.read_text(encoding='utf-8'))
        if not report or report.get('running') or not report.get('total') or report.get('fatal'):
            raise RuntimeError(f'{browser}: empty test report; suite did not finish')
        print(f'{browser}: {report.get("passed",0)}/{report.get("total",0)} passed; {report["failed"]} failed — {path}')
        for test in report.get('results', []):
            if not test['pass']:
                print('FAIL:', test['name'], test.get('error', ''))
        if report.get('fatal'):
            print(report['fatal'])
        return not report['failed'] and result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chrome', 'edge', 'all'], default='all')
    parser.add_argument('--no-build', action='store_true')
    args = parser.parse_args()
    if not args.no_build:
        build(include_tests=True)
    browsers = ['chrome', 'edge'] if args.browser == 'all' else [args.browser]
    found = [(b, find_browser(b)) for b in browsers]
    if any(not exe for _, exe in found):
        raise RuntimeError('Requested browser is not installed. Use --browser chrome or --browser edge, or set TOAST_CHROME / TOAST_EDGE.')
    ok = True
    for browser, executable in found:
        ok = run(browser, executable) and ok
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
