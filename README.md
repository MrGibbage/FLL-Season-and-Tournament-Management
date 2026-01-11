# FLL Season and Tournament Management

![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)
![License](https://img.shields.io/github/license/MrGibbage/FLL-Season-and-Tournament-Management)
![Last Commit](https://img.shields.io/github/last-commit/MrGibbage/FLL-Season-and-Tournament-Management)
![Repo Size](https://img.shields.io/github/repo-size/MrGibbage/FLL-Season-and-Tournament-Management)
![FIRST LEGO League](https://img.shields.io/badge/FIRST-LEGO%20League-blue.svg)

FLL Tournament and OJS creation, and closing ceremony script generation for FLL tournament leadership

**Platform:** LEGO Spike Prime Controller with MicroPython

# OJS Tournament Builder & Ceremony Script Generator

Automated tools to prepare per-tournament folders, populate OJS (Official Judging Spreadsheet) workbooks, validate data, and generate closing ceremony scripts for FIRST LEGO League tournaments.
Includes two tools for tournament management:
- **MAESTRO**: Managing All Event Seasons, Tournaments, Rosters, and OJSs for FIRST LEGO League. Regional leadership uses this to create tournament folders (with improved OJS files) for each tournament. Think of MAESTRO as orchestrating and coordinating all tournaments in a region.
- **TOAST**: Tournament OJS And Script Toolkit for FIRST LEGO League. Tournament directors and judge advisors use this to validate OJS entries and generate closing ceremony scripts. Think of TOAST as the entry point to the celebration after the tournament.

## Maestro Features

- **Tournament Folder Builder**: Automatically creates tournament folders (select one or all tournaments at once) and populates OJS spreadsheets with team assignments
- **Comprehensive Validation**: Checks tournament assignments, award definitions and allocations before building tournament folders
- **Custom awards**: Supports adding any custom awards as needed
- **Other outputs**: Generates printable blank "fill-in" forms for hand-writing awardees
- **Supports all tournament types**: Division tournaments (such as VA-DC) and non-division tournaments
- **Inputs**: Uses an easy-to-understand excel spreadsheet for all tournaments and teams assigned to those tournaments. Spreadsheet also allocates awards per tournament. Also uses a single json file for overall season configuration.

## Improved OJS Features

- **Judging pods**: Statistics for judging pods
- **Improved macros**: Custom macros support many new features
  - Sort the Results and Rankings worksheet by any column
  - Locked cells prevent inadvertent altering of formulas
  - Admin menu to lock, unlock, and add new teams
  - Practice mode by populating OJS with random scores
- **Automation Support**: OJS directly feeds TOAST. No need to manually transcribe scores, team numbers and names into the closing ceremony script
- **Recognizable**: Improved but familiar OJS is virtually indistinguishable from FIRST-distributed OJS from years past

## Toast Features

- **Closing Ceremony Script Generator**: Validates OJS data and generates HTML ceremony scripts with award winners
- **Dual Emcee Support**: Optional alternating color highlighting for two emcees reading the ceremony script
- **Comprehensive Validation**: Checks scores, ranges, and award allocations before ceremony script generation
- **Custom awards**: Supports adding any custom awards as needed
- **Other outputs**: Generates simplified HTML summaries
- **Supports all tournament types**: Division tournaments (such as VA-DC) and non-division tournaments
- **Presentation order**: Award winners render in reverse ranking order (3rd, 2nd, 1st) for ceremony flow (TOAST 1.00.01+)



## Versioning and Build Workflow

All version and commit message information is now stored in a single file: `version.json`.

- Both Maestro and Toast read their version and commit message from `version.json` at runtime.
- The build script (`build-all.bat`) also reads from `version.json` using PowerShell, ensuring a single source of truth.
- The old `version.py` is no longer used for versioning or commit messages.

As a regional tournament manager or program delivery partner, copy the files from this repo into a folder of your choice. Most testing has been done on Windows, but executables are included for macOS. As a tournament director or judge advisor for a single tournament, you will receive a link to download your ready-to-use OJS files and TOAST software.

## Usage

### Tournament Folder Builder (MAESTRO)

Once you download the repo, do the following:
1) Create one or more season configuration JSON files (e.g., `qualifiers.json`, `championship.json`) in the MAESTRO directory. See Configuration section below for required keys.
2) Edit the tournament Excel workbook (name is set in your configuration file). Update the worksheets per your region; in-sheet instructions are provided.
3) Edit the Jinja template files (closing ceremony, summary, fill-in) with your preferred wording and any custom awards.
4) Close the Excel workbook, then run `fll-maestro.exe` (or `python fll-maestro.py`) from the same folder.
   - If you have only one valid configuration file, MAESTRO will automatically use it
   - If you have multiple configuration files, you'll see a numbered list to choose from
5) Enter a tournament name to build one, or press ENTER to build all. Watch for warnings/errors.
6) When builds succeed, share the generated tournament folders via your preferred cloud service (OneDrive, Google Drive, Dropbox) with tournament directors and judge advisors.

**Note**: MAESTRO automatically scans for all `.json` files and validates them. Only files containing the required configuration keys (`season_yr`, `season_name`, `tournament_folder`, `filename`, `tournament_template`) will be shown as options.

### OJS usage

Review the included toast-instructions.pdf for worksheet details. Two important requirements: (1) use the desktop version of Excel (cloud Excel disables critical features); (2) enable macros when opening the spreadsheet.  
When you finish entering scores, awards, and advancing teams, save and close the workbook, then run `fll-toast.exe` (or `python fll-toast.py`).  

### Closing Ceremony Script Generator (TOAST)

Running TOAST validates every worksheet entry (missing scores, out-of-range judging values, unassigned allocated awards, etc.). Warnings allow you to continue but remind you to double-check; severe errors require fixing and re-running.
On success, TOAST produces two HTML files: the closing ceremony script and a summary. Share with emcees (tablet/phone) or use on a laptop at the ceremony. If you have two emcees, enable the dual-emcee highlighting (Team and Program Information sheet, cell F2) to alternate colors every other paragraph.

## Configuration

MAESTRO supports multiple configuration files to manage different tournament types (e.g., qualifiers and championships). Create one or more JSON configuration files in the MAESTRO directory:

**Example files:**
- `qualifiers.json` - for qualifier tournaments
- `championship.json` - for championship tournaments  
- `season.json` - traditional single configuration

When you run MAESTRO:
- If only **one** valid configuration file exists → automatically selected
- If **multiple** valid files exist → you'll see a numbered list to choose from

### Configuration File Format

Each configuration file should follow this structure:

```json
{
  "season_yr": "2025",
  "season_name": "SUBMERGED",
  "filename": "2025-FLL-Qualifier-Tournaments.xlsx",
  "tournament_template": "2025-Qualifier-Template.xlsm",
  "tournament_folder": "C:/Users/username/Documents/tournaments",
  "copy_file_list_common": [
    {"source": "script_maker-win.exe", "dest": "script_maker-win.exe"},
    {"source": "script_maker-mac", "dest": "script_maker-mac"},
    {"source": "instructions.pdf", "dest": "instructions.pdf"}
  ],
  "copy_file_list_divisions_only": [
    {"type": "script_template", "source": "script_template-with-divisions.html.jinja", "dest": "script_template.html.jinja"},
    {"type": "summary_template", "source": "summary_template-with-divisions.html.jinja", "dest": "summary_template.html.jinja"},
    {"type": "fillin_template", "source": "fillin_template-with-divisions.html.jinja", "dest": "fillin_template.html.jinja"}
  ],
  "copy_file_list_no_divisions_only": [
    {"type": "script_template", "source": "script_template.html.jinja", "dest": "script_template.html.jinja"},
    {"type": "summary_template", "source": "summary_template.html.jinja", "dest": "summary_template.html.jinja"},
    {"type": "fillin_template", "source": "fillin_template.html.jinja", "dest": "fillin_template.html.jinja"}
  ]
}
```

### Configuration Keys

**Required keys** (MAESTRO validates these):
- `season_yr`: Tournament season year
- `season_name`: FLL season theme name
- `filename`: Excel file with tournament list and assignments
- `tournament_template`: OJS template file to copy
- `tournament_folder`: Root folder where tournament subfolders will be created

**Optional keys**:
- `copy_file_list_common`: Files always copied to every tournament folder
- `copy_file_list_divisions_only`: Files only copied when `using_divisions=True`
- `copy_file_list_no_divisions_only`: Files only copied when `using_divisions=False`
- `copy_file_list`: Additional files to copy to each tournament folder

### Per-tournament config generated by MAESTRO

Each tournament folder gets a `tournament_config.json` with an `INFO.ojs_files` array that lists the OJS files to use. This replaces the old `ojs_filenames` list. Example:

```json
  "ojs_files": [
    { "division": "D1", "filename": "2025-vadc-fll-challenge-Unearthed-ojs-Champ-D1.xlsm" },
    { "division": "D2", "filename": "2025-vadc-fll-challenge-Unearthed-ojs-Champ-D2.xlsm" }
  ]
```

- Division-enabled tournaments will have one entry per division present in the Excel Div column (e.g., only `D1` if there is no `D2` row).
- Non-division tournaments still have a single entry; `division` may be empty.

**Details:**
- `tournament_folder`: **Root folder where tournament subfolders will be created**
  - **IMPORTANT**: Use forward slashes `/` in paths (works on all platforms)
  - Will be created automatically if it doesn't exist
  - Must be an absolute path (full path from root)
  - Examples: 
    - Windows: `"C:/tournaments"` or `"C:/Users/username/Documents/tournaments"`
    - Mac: `"/Users/username/Documents/tournaments"`
    - Linux: `"/home/username/tournaments"`
- `copy_file_list_common`: Files always copied to every tournament folder
  - Each entry is a dict with `source` (filename in MAESTRO directory) and `dest` (filename in tournament folder)
  - Common files like executables and PDFs that don't vary by division setting
- `copy_file_list_divisions_only`: Files only copied when `using_divisions=True`
  - Typically includes division-specific templates (e.g., `script_template-with-divisions.html.jinja`)
  - Source and dest can differ to provide consistent naming in tournament folders
  - **Optional `type` field**: Use `"type": "script_template"`, `"summary_template"`, or `"fillin_template"` to indicate template files
  - MAESTRO writes template filenames to `tournament_config.json` for TOAST to use
- `copy_file_list_no_divisions_only`: Files only copied when `using_divisions=False`
  - Typically includes non-division templates (e.g., `script_template.html.jinja`)
  - Allows TOAST to always use the same filenames regardless of division setting
  - **Optional `type` field**: Same as above - identifies template files for TOAST
  - **TOAST Fallback**: If template filenames are not in `tournament_config.json`, TOAST defaults to:
    - `script_template.html.jinja` for ceremony scripts
    - `summary_template.html.jinja` for ceremony summaries
  - ⚠️ **Don't use backslashes** `\` - they require escaping in JSON as `\\`
- `copy_file_list`: Additional files to copy to each tournament folder

## Logs

Log files are automatically created with timestamps in the script directory:

### Tournament Builder Logs
- **Format**: `ojs_builder_YYYYMMDD_HHMMSS.log`
- **Location**: Repository directory (beside the scripts)
- **Contents**: Full debug information (even in quiet mode)

### Ceremony Generator Logs
- **Format**: `ceremony_generator_YYYYMMDD_HHMMSS.log`
- **Location**: Repository directory (TOAST logs next to `fll-toast.py`)
- **Contents**: Validation results, data collection, and rendering details


## Troubleshooting

### Tournament Builder Issues (MAESTRO)

**"Could not open tournament file"**
- Ensure Excel file is closed before running
- Check path in `season.json` is correct
- Verify file exists in the expected location

**"No teams assigned to [tournament], OJS file removed"**
- This is normal if a division has no teams
- The script automatically skips empty divisions
- Check the Assignments sheet if unexpected

**"Missing required columns in assignments"**
- Verify Assignments table has: `Team #`, `Team Name`, `Coach Name`
- Check for typos in column headers
- Ensure no extra spaces in column names

**Module import errors**
- Ensure virtual environment is activated
- Run `uv sync` to reinstall dependencies

### Ceremony Script Generator Issues (TOAST)

**"Validation errors found"**
- Review the error messages - they indicate specific OJS data issues
- Check scores are within valid ranges (Innovation/Robot Design: 0-4, Core Values: 0-3)
- Verify all award selections match allocated counts
- Ensure Champion's Rank values are sequential starting from 1

**"Missing critical template variables"**
- Ensure tournament_config.json exists (run build-tournament-folders first)
- Check that OJS files have all required award selections
- Verify advancing teams are marked correctly

**"No highlighting in ceremony script"**
- Check cell F2 in "Team and Program Information" sheet is set to TRUE
- Verify the value is boolean TRUE (not text "TRUE")
- Try running with --debug to see which file enables dual emcee mode

**"Robot game awards not collecting"**
- Ensure "Robot Game Rank" column has sequential ranks (1, 2, 3...)
- Check "Max Robot Game Score" column has values
- Verify Team # and Team Name columns are populated

### Getting Help

1. **Check the log file** - Contains detailed error information
  - Tournament builder: `ojs_builder_YYYYMMDD_HHMMSS.log`
  - Ceremony generator: `ceremony_generator_YYYYMMDD_HHMMSS.log`
2. **Run with `--verbose` or `--debug`** - Shows step-by-step execution
3. **Use `--interactive`** - See validation summary before processing (builder only)
4. **Review error suggestions** - Scripts provide recovery steps for common issues

## Development

Comfortable editing Python? Clone the repo and extend MAESTRO or TOAST as needed. Use the module structure and templates as your starting point.
