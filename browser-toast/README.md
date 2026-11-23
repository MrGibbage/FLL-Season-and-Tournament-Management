# Browser TOAST

Standalone, offline ceremony generation for FIRST LEGO League OJS workbooks.
MAESTRO and Python TOAST are unchanged.

## Use

Open `dist/TOAST.html` in your browser. Save and close the OJS files in Excel,
then choose or drop the single workbook or both division workbooks together.
Review validation results. Warnings require acknowledgment; intentional missing
award winners require typing exactly `YES`. Preview and download the ceremony
and summary. Download a diagnostic report when troubleshooting.

After every Excel change, save and click **Check again**. The supported file
picker retains read-only file handles for the current session and calls
`getFile()` again on every check. Supported drag/drop handles work the same way.
When the browser or selection supplies only File snapshots, Check again opens
the selector and explains that reselecting is required; it never silently checks
stale bytes. Handles are not persisted across page reloads. TOAST does not watch
Excel, recalculate its formulas, or reliably detect locks. New selections and
refreshes clear previews, approvals, and old results, including after read errors.

No installation, server, network access, account, or executable is needed. All
libraries and standard templates are inside the HTML file. The distributed
production file contains no tournament samples, references, or test code.
Workbooks are read only; VBA macros are neither loaded nor executed.

## Build

From the repository root, using its Python environment:

```powershell
.venv/Scripts/python.exe scripts/build_browser_toast.py
```

The first build downloads fflate 0.8.2 and Nunjucks 3.2.4 plus their licenses.
Their JavaScript SHA-256 checksums are verified. Later builds use the cached files
in `workspace/toast-browser-vendor`. There are no runtime CDN dependencies.
Source is in this directory; standard templates remain at the repository root.
`dist/` and `workspace/` are ignored build/test outputs.

## Automated validation

Requires Python dependencies from the existing project, Node.js, and installed
Chrome and/or Edge. No npm packages, browser downloads, or local server needed.

```powershell
.venv/Scripts/python.exe scripts/test_browser_toast.py
# Or choose a browser:
.venv/Scripts/python.exe scripts/test_browser_toast.py --browser edge
# Reuse an already built test harness when no source has changed:
.venv/Scripts/python.exe scripts/test_browser_toast.py --no-build
```

The runner builds `dist/TOAST.html` and a separate private test harness, then
launches isolated headless browsers using a DevTools pipe and real browser time.
External hostname resolution is blocked. Tests cover the actual production
engine and interface, not a duplicate test-only implementation.

Reports: `workspace/browser-toast-results-{chrome,edge}.json`. Desktop and narrow
viewport screenshots are saved beside them. Assertions, incomplete test runs,
missing browsers, and browser failures produce a nonzero exit code.

Only `tournaments/Dunford` supplies fixtures. It is read only. After the first
capture, tests use `workspace/toast-browser-fixtures.json`; current Dunford edits
cannot invalidate the clean baseline. Python expectations are regenerated from
those snapshot bytes in temporary folders on every test build. To explicitly
replace the snapshot from clean live files, run
`scripts/build_browser_toast.py --tests --refresh-fixtures`. Generated
single-division samples and corrupted workbooks are built in memory or temporary
directories. No neighboring tournament folder is accessed by the build/test
scripts. The private harness contains Dunford data; distribute only `TOAST.html`.

See [TEST_PLAN.md](TEST_PLAN.md) for coverage and release checks.

## Compatibility and deliberate changes

- Current embedded-config `.xlsm` workbooks: use workbook identity, so renaming
  files is supported. The lowest division supplies authoritative configuration;
  differences in another division produce a warning. Missing, duplicate, and
  mixed tournament/division selections are rejected. Sole D1 or D2 works when
  the embedded configuration actually describes a one-division event.
- Older `.xlsx`/`.xlsm` files: select their JSON configuration as well; filenames
  must match. Built-in standard ceremony templates are used. Custom legacy
  templates are explicitly rejected and still require Python TOAST.
- Saved formula values are checked against independently recomputed scores and
  ranks. This is not an Excel formula engine. Recalculate and save in Excel when
  cached values are absent or wrong. Errors in unused workbook columns are not
  treated as errors in ceremony data.
- Team names and tournament titles are HTML-escaped. Python's existing title
  insertion was unescaped; reference comparisons explicitly allow this security
  correction and otherwise compare the entire output text after normalizing
  line endings and outer whitespace.
- Downloads use normal browser behavior, not direct writes into a selected
  tournament folder. Diagnostic reports identify the latest selected files and
  current warning/omission approval state, including failures.
- Limits: 25 MiB per input file, 100 MiB expanded ZIP size, 3,000 ZIP entries,
  200,000 cells per table. Encrypted files and malformed packages are rejected.
  Only XML/relationship parts are decompressed. Preview frames are sandboxed;
  text is inserted into the app through `textContent`. Runtime network access
  is blocked by Content Security Policy. Trusted bundled Nunjucks templates
  require its inline compiler; arbitrary user templates are not accepted.

## Release status

Version 1.0.2 is ready for local acceptance testing. Automated Windows Chrome and
Edge coverage is recorded in the generated reports. The responsive layout is
also visually inspected at desktop and 390px widths. Actual macOS Safari,
Firefox, native file dialogs, printing, and school-managed download policies
still need the manual checks in the test plan before broad distribution.

Score-entry errors identify the division, worksheet, Excel cell, team, and valid
input range. Invalid inputs defer saved-calculation/rank checks in that workbook
until the next run, preventing cascades from one blank score. Independent input,
award, advancement, and other-workbook errors remain visible. With valid inputs,
stale calculations produce one recalculate/save message per workbook; individual
calculation mismatches are retained in the diagnostic report.

## Final Notes

The browser build is independent of MAESTRO and existing executables. The critical
operational rule is to save/recalculate the workbook and check again after edits.
Keep the standalone HTML with tournament materials for offline use, and export
the latest diagnostic report when a director needs help. No hosting routes or
cross-service dependencies are involved.
