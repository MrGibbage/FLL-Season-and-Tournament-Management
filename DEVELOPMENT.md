### Using uv (Recommended)

```bash
# Install uv if you haven't already
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install all dependencies
cd FLL-Season-and-Tournament-Management
uv sync
```

The `uv sync` command creates the virtual environment, installs all dependencies from `pyproject.toml`, and sets up the project in editable mode - all in one step!

### Using pip (Alternative)

```bash
cd 2025-all
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
pip install -e .
```
#### Quick Start (Default - Quiet Mode)

```bash
# Activate environment (if using uv)
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Run the builder
python fll-maestro.py
```

You'll be prompted to select a tournament or press ENTER to build all.

#### Command-Line Options

```bash
# Interactive mode (with prompts and validation summary)
python fll-maestro.py --interactive

# Verbose/debug mode
python fll-maestro.py --verbose

# Process specific tournament without prompts
python fll-maestro.py --tournament "Manassas_1"

# Combine options
python fll-maestro.py --verbose --tournament "ABC"

# Show help
python fll-maestro.py --help
```

#### Available Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--interactive` | `-i` | Show prompts, validation summary, and confirmations |
| `--verbose` | `-v` | Enable debug logging to console and file |
| `--tournament NAME` | `-t NAME` | Process only the specified tournament |
| `--skip-validation` | | Skip pre-flight checks (not recommended) |

#### Command-Line Options

| Flag | Short | Description |
|------|-------|-------------|
| `--verbose` | `-v` | Enable verbose logging (INFO level) |
| `--debug` | `-d` | Enable debug logging (DEBUG level, implies --verbose) |

## Modes

### Quiet Mode (Default)
- Minimal console output
- Logs everything to file
- Always prompts for tournament selection
- Best for regular use

### Interactive Mode (`--interactive`)
- Full validation summary display
- Confirmation prompts
- Progress indicators with status messages
- Best for troubleshooting or first-time setup

### Verbose Mode (`--verbose`)
- Debug-level logging to console and file
- Detailed operation information
- Shows table operations, file copies, etc.
- Best for debugging issues

## Project Structure

```
FLL-Season-and-Tournament-Management/
├── fll-maestro.py                       # Tournament folder builder
├── fll-toast.py                         # Ceremony script generator
├── modules/
│   ├── __init__.py
│   ├── constants.py                     # Configuration constants
│   ├── logger.py                        # Logging setup
│   ├── file_operations.py               # File/folder operations & tournament config
│   ├── excel_operations.py              # Excel table read/write
│   ├── worksheet_setup.py               # OJS worksheet configuration & conditional formatting
│   ├── user_feedback.py                 # Progress tracking and validation
│   ├── ceremony_validator.py            # OJS data validation for ceremony scripts
│   ├── ceremony_data_collector.py       # Extract team/award data from OJS files
│   └── ceremony_renderer.py             # Jinja2 template rendering
├── script_template.html.jinja           # Ceremony script template
├── season.json                          # Season configuration
├── pyproject.toml                       # Project dependencies
└── [tournament_folder]/                 # Output location (specified in season.json)
    └── [tournament_name]/
        ├── [ojs_file].xlsm              # OJS spreadsheet with teams and scores
        ├── tournament_config.json        # Generated tournament configuration
        ├── [ceremony_script].html        # Generated ceremony script (after running generator)
        ├── script_template.html.jinja    # Ceremony template (copied here)
        ├── script_maker-win.exe
        ├── script_maker-mac
        └── ...
```

## Template File Handling

### How Template Filenames Work

MAESTRO and TOAST use a dynamic template filename system that allows different template files for division vs non-division tournaments:

1. **Season Config (qualifiers.json / championship.json)**:
   - In the `copy_file_list_divisions_only` and `copy_file_list_no_divisions_only` arrays, add a `"type"` field to template files:
     ```json
     {
       "type": "script_template",
       "source": "champ_script_template-with-divisions.html.jinja",
       "dest": "champ_script_template.html.jinja"
     }
     ```
   - Valid type values: `"script_template"`, `"summary_template"`, `"fillin_template"`

2. **MAESTRO Processing**:
   - Reads the copy file lists and extracts entries with a `"type"` field
   - Writes the destination filename to `tournament_config.json` INFO section
   - Example: `"script_template": "champ_script_template.html.jinja"`

3. **TOAST Processing**:
   - Reads template filenames from `tournament_config.json` INFO section
   - **Fallback behavior**: If keys are missing, defaults to:
     - `script_template.html.jinja` for ceremony scripts
     - `summary_template.html.jinja` for ceremony summaries
   - This ensures backward compatibility and graceful degradation

### Example Flow

```
championship.json (divisions_only):
  {"type": "script_template", "source": "champ_script-div.html.jinja", "dest": "champ_script.html.jinja"}
          ↓ MAESTRO copies file and writes config
tournament_config.json (INFO):
  "script_template": "champ_script.html.jinja"
          ↓ TOAST reads config
Uses: champ_script.html.jinja (or falls back to script_template.html.jinja if not found)
```

To create a windows executable file, 
first install pyinstaller, with
pip install pyinstaller
then run
.venv\Scripts\pyinstaller.exe -F fll-toast.py
.venv\Scripts\pyinstaller.exe -F fll-maestro.py
Then copy the .exe file(s) from dist to the project root. Be sure to include fll-toast.exe in the files to be copied entries in the season json config file.
