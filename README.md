# OJS Tournament Builder & Ceremony Script Generator

Automated tools to prepare per-tournament folders, including population of OJS (Official Judging Spreadsheet) workbooks, data vailidation and generate closing ceremony scripts for FIRST LEGO League tournaments.
Includes two tools for tournament management:
- **MAESTRO**: Managing All Event Seasons, Tournaments, Rosters, and OJSs for FIRST LEGO League. This tool will be used by regional leadership to create tournament folders (including improved OJS files which support automation) for each of the individual tournaments within that region. Think of this tool archestrating and coordinating all regional tournaments.
- **TOAST**: Tournament OJS And Script Toolkit for FIRST LEGO League. This tool is used by individual tournament directors and judge advisors to validate OJS entries and generate a closing ceremony script. Think of this tool as the entry point to the celebration after the tournament.

## Maestro Features

- **Tournament Folder Builder**: Automatically creates tournament folders (select one or all tournaments at once) and populates OJS spreadsheets with team assignments
- **Comprehensive Validation**: Checks tournament assignments, award definitions and allocations before building tournament folders
- **Custom awards**: Supports addition of any custom awards as needed
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
- **Custom awards**: Supports addition of any custom awards as needed
- **Other outputs**: Generates simplified HTML summaries
- **Supports all tournament types**: Division tournaments (such as VA-DC) and non-division tournaments


## Installation

As a regional tournament manager, or program delivery partner, simply copy the files from this repo into a folder of your choice. Most testing has been done on Windows, but executables are included for MacOS. As a tournament director or judge advisor for a single tournament, you will be given a link to download your ready-to-use OJS(s) and TOAST software

## Usage

### Tournament Folder Builder (MAESTRO)

Once you have downloaded the files in this repo, you will have some editing to do.  
See the configuration section below to edit the season.json file.  
Edit the tournament excel spreadsheet (file name is configured in the season.json file). There are several important worksheets that will need updating to suit your region's needs. There are instructions on the worksheets which should help you get started.  
You will also want to edit the jinja template files using any text editor such as Notepad, Notepad++, or VS Code. The closing ceremony script is probably the most important one, so make sure it has the verbiage you need. If you have any custom awards, you will want to include them here.  
Once you have everything edited and saved (be sure to exit out of the workbook), you can run fll-maestro.exe from the same folder. Type in the name of a single tournament, or press enter to build all tournaments. Pay attention for any warnings or errors.  
If everything built correctly and you have no changes to make, move the folders to some cloud-based file sharing platform such as OneDrive, Google Drive or Dropbox. Get a sharing link to the folders and share the link with your tournament directors and judge advisors.  

### OJS usage

Review the included toast-instructions.pdf for detailed instructions for each worksheet. Two important details: 1) You must use the desktop version of Excel. There will be significant feature reduction if using the cloud version of Excel. 2) enable macros when opening spreadsheet.  
When you are done entering scores and choosing awards/advancing teams, save and close the workbook. You can now run fll-toast.exe.  

### Closing Ceremony Script Generator (TOAST)

Running fll-toast.exe does several important things. First it will validate the entries on all of the worksheets. Did you miss a cell and leave it blank? Or enter a number that doesn't make sense (like a 6 in judging cell). Did you forget to assign an award that was allocated for your tournament? If any of these are found in the validation, a warning message will appear or if the error is severe, the program will exit and you will have to fix the error before proceeding. Warnings will generally continue with execution, but serve as a reminder to double-check the entries and results.  
If everything is ok and no errors were found, you should have a couple of new html files. The first one is the closing ceremony script. You can email it to the emcees where they could perhaps read it off a tablet or cell phone, or you can open it on a laptop that you will take to the ceremony.  
If you have two emcees, you might want to try the highlighting feature which will color every-other-row in the script to make it easier for them to follow along. Look for the cell on the Team and Program Information worksheet to enable highlighting.

## Configuration

Edit `season.json` to configure:

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
    {"source": "script_template-with-divisions.html.jinja", "dest": "script_template.html.jinja"},
    {"source": "summary_template-with-divisions.html.jinja", "dest": "summary_template.html.jinja"}
  ],
  "copy_file_list_no_divisions_only": [
    {"source": "script_template.html.jinja", "dest": "script_template.html.jinja"},
    {"source": "summary_template.html.jinja", "dest": "summary_template.html.jinja"}
  ]
}
```

### Configuration Keys

- `season_yr`: Tournament season year
- `season_name`: FLL season theme name
- `filename`: Excel file with tournament list and assignments
- `tournament_template`: OJS template file to copy
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
- `copy_file_list_no_divisions_only`: Files only copied when `using_divisions=False`
  - Typically includes non-division templates (e.g., `script_template.html.jinja`)
  - Allows TOAST to always use the same filenames regardless of division setting
  - ⚠️ **Don't use backslashes** `\` - they require escaping in JSON as `\\`
- `copy_file_list`: Additional files to copy to each tournament folder

## Logs

Log files are automatically created with timestamps in the script directory:

### Tournament Builder Logs
- **Format**: `tournament_builder_YYYYMMDD_HHMMSS.log`
- **Location**: Repository directory (beside the scripts)
- **Contents**: Full debug information (even in quiet mode)

### Ceremony Generator Logs
- **Format**: `ceremony_generator_YYYYMMDD_HHMMSS.log`
- **Location**: Repository directory (TOAST always logs next to `fll-toast.py`)
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
   - Tournament builder: `tournament_builder_YYYYMMDD_HHMMSS.log`
   - Ceremony generator: `ceremony_generator_YYYYMMDD_HHMMSS.log`
2. **Run with `--verbose` or `--debug`** - Shows step-by-step execution
3. **Use `--interactive`** - See validation summary before processing (builder only)
4. **Review error suggestions** - Scripts provide recovery steps for common issues

## Development

Are you comfortable editing python programs? If so, and you feel like there is some functionality missing from MAESTRO or TOAST, then feel free to clone this repo and make your own changes. We have a page here with some more details about what's going on behind the scenes.
