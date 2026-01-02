# Release Notes

## 0.9.0
- Added explicit TOAST versioning with env override (`TOAST_VERSION`), printing/logging at startup.
- Switched tournament configs to `INFO.ojs_files` (objects with `division` and `filename`), replacing `ojs_filenames`.
- Updated TOAST to consume `ojs_files` for validation, data collection, and template variable checks.
- Updated MAESTRO config generation to emit `ojs_files` with normalized division codes.
- Added `build-toast.bat` to stamp version via `git describe`, run PyInstaller, and copy the exe to repo root.
- Improved logging clarity by including division labels tied to each OJS entry.

## 0.9.1
- Removed filename pattern assumptions in TOAST output naming; now uses the OJS basename only.
- (No breaking changes; rebuild exe to pick up version bump.)

## 0.8.0 (baseline summary)
- Introduced MAESTRO to build per-tournament folders from season Excel + templates, copy assets, and generate `tournament_config.json`.
- Introduced TOAST to validate OJS data (scores, awards, allocations) and render ceremony script/summary HTML outputs.
- Added template-driven ceremony outputs with division/non-division support and dual-emcee highlighting.


## 0.9.2
- MAESTRO no longer writes the AwardDef table to OJS workbooks (AwardDef is unused by TOAST and downstream tools).
- Eliminated warnings about extra label columns in AwardDef.
- Version bump to 0.9.2.


## 0.9.11
- build-all.bat now prompts before committing: shows staged files, commit message, and allows edit or abort for safer, more transparent workflow.
- build-all.bat no longer edits version.py; version.py is now the single source for both version and commit message.
- Maestro and Toast print both the GitHub version (commit_message) and the local version string after the splash screen.

## Unreleased / Next
- (Add new entries here as changes are made.)
