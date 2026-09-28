# Development guide

## Environment setup

Python 3.14 and `uv` are used by the automated builds. From the repository root:

```powershell
python -m pip install uv==0.7.13
uv sync --frozen --no-dev --python 3.14
```

For development tools such as Ruff, install the optional development dependencies:

```powershell
uv sync --frozen --extra dev --python 3.14
```

PyInstaller is a build dependency. MAESTRO and TOAST do not import it or require a separate PyInstaller installation at runtime.

## Running from source

Run MAESTRO from the repository root:

```powershell
.venv\Scripts\python.exe fll-maestro.py
.venv\Scripts\python.exe fll-maestro.py --help
```

MAESTRO supports `--verbose`, `--debug`, `--tournament NAME`, `--skip-validation`, and `--no-cleanup`. Use the final two options only for targeted troubleshooting.

TOAST normally runs inside a generated tournament folder. For development, it can read a tournament elsewhere and write generated files into an isolated scratch folder:

```powershell
.venv\Scripts\python.exe fll-toast.py `
  --tournament-dir tournaments/Dunford `
  --output-dir workspace/toast-test/Dunford
```

This is the same program packaged for tournament directors. It does not bypass validation. Save and close the OJS workbooks in desktop Excel first so TOAST reads current calculated values.

Without `--tournament-dir`, TOAST looks for tournament inputs in the current directory and then beside the script or executable. A tournament director can therefore place `fll-toast.exe` in the tournament folder and run it without arguments.

## Tests

Run the complete test suite before packaging:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The always-available tests cover score boundaries, rubric and GP validation, generated workbook formulas, and template-variable validation. Additional integration tests cover division and non-division rendering, award and advancement allocation, workbook caching, and command-line execution. Those integration tests run only when the ignored local Dunford fixtures are present; otherwise they report as skipped. If the fixtures exist, they must contain a complete scored tournament.

The current season maximum robot-game score is configured as `robot_game_max_score` in the season JSON. Generated tournament configurations store it as `INFO.robot_game_max_score`; TOAST defaults to 530 when an older configuration omits it.

TOAST requires integer robot scores from zero through that maximum, integer rubric scores from 0 through 4, and GP values of 0, 2, 3, or 4. It checks team identities across sheets, saved calculated scores and ranks, award labels and quotas, and advancement selections. Missing or duplicate award winners and stale or missing calculations block output. Missing an alternate is a warning; multiple alternates are an error. Champion's-rank ties are valid, while robot-game ties affecting award places require resolution.

Both `team_list_D1/D2` and the legacy `div1_list/div2_list` template names work. TOAST validates both output templates before writing either HTML file. A failed run leaves prior HTML files untouched.

## Local executable builds

PyInstaller must build on the operating system that will run the binary. A Windows build cannot produce the Mac executables, and a Mac build cannot produce the Windows executable.

Use the checked-in specification files rather than passing `-F` directly:

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean fll-maestro.spec
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean fll-toast.spec
```

The results are written to `dist/`:

- Windows: `dist/fll-maestro.exe` and `dist/fll-toast.exe`
- macOS: `dist/fll-maestro` and `dist/fll-toast`

Smoke-test both programs before distribution:

```powershell
dist\fll-maestro.exe --help
dist\fll-toast.exe --help
```

On macOS, use `./dist/fll-maestro --help` and `./dist/fll-toast --help`.

The executables contain Python and all Python dependencies. They do not contain season JSON files, OJS workbooks, instructions, or Jinja templates. MAESTRO must remain beside its regional configuration and source files. TOAST must be delivered with each generated tournament folder and its configuration, workbook, and templates.

## GitHub Actions builds

Current status: the specifications and workflow are committed, and both Windows executables have been built and smoke-tested locally. The first hosted run successfully built, tested, and smoke-tested all three platforms; its two Mac jobs then exposed an archive-path error during artifact upload. That path has been corrected. A second manual run is required to verify all three downloadable artifacts. No GitHub Release has been created yet.

The **Build release binaries** workflow in `.github/workflows/build-release.yml` uses clean hosted runners to:

1. Install Python 3.14 and the dependency versions in `uv.lock`.
2. Run test discovery. Fixture-independent tests run on every hosted runner; tests that require the ignored Dunford tournament report as skipped.
3. Build MAESTRO and TOAST from their PyInstaller specifications.
4. Run each executable with `--help` as a smoke test.
5. Package both programs for Windows x64, Intel Mac, and Apple silicon Mac.

### Test build without a release

1. Open the repository on GitHub.
2. Select **Actions** and then **Build release binaries**.
3. Select **Run workflow**, choose `master`, and run it.
4. When all three build jobs finish, download the artifacts from the workflow run.

The artifacts are temporary CI outputs. This path does not create a tag or a GitHub Release.

### Versioned release

1. Update `MAESTRO_VERSION` in `fll-maestro.py` and `TOAST_VERSION` in `fll-toast.py` to the same three-part version, such as `1.00.02`.
2. Run the tests and commit and push the version change.
3. Create the matching annotated tag and push it:

   ```powershell
   git tag -a v1.00.02 -m v1.00.02
   git push origin v1.00.02
   ```

4. GitHub validates that the tag matches both embedded versions, then builds and tests all three platforms.
5. After every platform succeeds, GitHub creates a **draft** release with these archives:
   - `fll-tools-windows-x64.zip`
   - `fll-tools-macos-intel.tar.gz`
   - `fll-tools-macos-apple-silicon.tar.gz`
6. Download and test the relevant archives. Edit the generated release notes if needed, then publish the draft release in GitHub.

Do not reuse a released version tag. If a build needs a code change, fix it, increment the version, and create a new tag.

The GitHub Windows executable should behave like a local build made from the same commit, Python version, lock file, and specification. It will not necessarily be byte-for-byte identical because build paths, timestamps, and native tooling can differ.

The Mac executables are currently unsigned and unnotarized. Build success confirms that they launch on their runner architecture, but downloaded copies may require approval in macOS Privacy & Security. Signing and notarization require an Apple Developer identity and GitHub release secrets.

## OJS VBA maintenance

The source-controlled team-name module is `vba/TeamNameEditor.bas`. To update a template, import that module into the template's VBA project, save the file as `.xlsm`, close Excel, and test on a disposable generated tournament workbook. The **Home > VA-DC FLL > OJS > Admin > Change Team Name** command calls `cbChangeTeamName`.

Keep VBA source in `vba/` synchronized with both qualifier templates. Excel may rewrite internal XML when it saves a VBA import, so validate formulas, table ranges, locked cells, and protection after changes.

## Template file handling

MAESTRO reads template entries from `copy_file_list_divisions_only` or `copy_file_list_no_divisions_only`. Entries with `type` set to `script_template`, `summary_template`, or `fillin_template` are copied and recorded in the generated `tournament_config.json`.

TOAST reads those filenames from `tournament_config.json`. Older configurations fall back to `script_template.html.jinja` and `summary_template.html.jinja`.

Use forward slashes in JSON paths, including on Windows.
