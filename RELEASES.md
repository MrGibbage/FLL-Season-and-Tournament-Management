## 1.00.09
- Name the Windows executable fll-toast-win.exe in builds, release archives, and MAESTRO tournament folders.
- Show friendly recovery instructions for open or locked OJS files, keeping technical tracebacks in the log.
- Refresh tournament director instructions.
- Bundle division and single-division ceremony/summary templates inside the shared TOAST executables.
- Embed identical complete tournament configuration in each OJS; use the lowest division as authoritative.
- Keep authoring JSON in tournaments/_maestro-config, outside director folders.
- Label form, summary, and ceremony titles with the event's divisions; single-division labels come from the required Div column on the Single Division worksheet.
- Include division-aware advancement and alternate entries in forms and historical summaries.

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
- build-all.bat, Maestro, and Toast now all read version and commit_message from version.json (using PowerShell and Python's json module).
- The old version.py is no longer used for versioning or commit messages.
- Maestro and Toast print both the GitHub version (commit_message) and the local version string after the splash screen.

## 1.00.00
- Initial production release in preparation for the VA-DC FLL Championship

## 1.00.01
- TOAST: Award winners now render in reverse ranking order (3rd, 2nd, 1st) to match presentation flow.
- No changes to MAESTRO other than version bump.
- Version bump to 1.00.01.

## 1.00.02
- Include ceremony configuration in TOAST's template data so season-aware templates render in downloaded builds.
- Generate tournament names and OJS filenames from season JSON, and label division awards in scripts.
- Remove division suffixes from combined ceremony filenames; keep single-division suffixes.
- Refresh 2026 Bioglow qualifier workbooks and templates.

## 1.00.08 (next build)
- Rename source-workbook tournament tabs to Single Division and Two Divisions and update MAESTRO to read them.
- Allow the non-division script's optional Breakthrough section to be absent when that award is not allocated.
- Package only TOAST in Windows and Mac releases; run MAESTRO from Python source.

## 1.00.07
- Keep the password input (Team and Program Information!I1) unlocked in generated OJS workbooks; I2 remains locked.
- TOAST waits for Enter after a declined missing-award override and explains how to continue.

## 1.00.06
- Keep the Dual Emcee input (Team and Program Information!F2) unlocked in generated OJS workbooks while protecting cells outside the tables.

## 1.00.05
- Executables are distributed through releases and ignored by Git; the small source workbooks stay tracked.
- MAESTRO copies any extra Mac TOAST builds present beside it without requiring them in a source checkout.

## 1.00.04
- MAESTRO now copies the matching TOAST executable into every generated tournament folder.

## 1.00.03
- TOAST can continue after an explicit `YES` when regular or tournament-level Judges awards are intentionally left unawarded; unfilled places render as `NONE`. Judges labels are interchangeable, including repeated labels across or within OJS workbooks. Selections above the tournament allocation remain errors.
- Updated both closing-ceremony templates with volunteer and coach recognition text.
- MAESTRO locks cells and inherited row/column styles outside OJS table data rows in newly generated workbooks.
- Added Windows and macOS first-run instructions for downloaded executables in the README.
- TOAST supports local tournament/output paths, caches workbook reads, supports both team-list naming conventions, and stops on missing template data or collection failures.
- Added configurable robot-game maximum (530 by default), integer score checks, saved-calculation checks, team consistency, award allocation, and advancement validation.
- Fixed non-division and single-division warning/rendering paths and HTML escaping of team names and award labels.
- MAESTRO now calculates each team's Core Values GP contribution from its own subtotal, counted once, including when using the existing templates.
- Restored AwardDef population: TOAST uses tournament_config.json, but the OJS still needs the ADV allocation for its advancement count and status message.
