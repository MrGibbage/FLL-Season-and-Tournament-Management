try:
    from version import __version__
except ImportError:
    __version__ = "dev"

    print(f"{Fore.CYAN}MAESTRO version:{Style.RESET_ALL} {__version__}")
    logger = setup_logger("maestro_builder", debug=True)
    logger.info(f"MAESTRO version: {__version__}")

"""Utility to prepare per-tournament folders and populate OJS spreadsheets.

This script reads a season manifest (`season.json`) and a master
`TournamentList` (or `DivTournamentList`) workbook to create a folder for
each tournament, copy template files, and populate the OJS (Online Judge
System) spreadsheet tables with team/award/meta information.

Usage:
    python build-tournament-folders.py              # Interactive mode (default)
    python build-tournament-folders.py --verbose     # Maximum output with debug logging
"""

import os
import sys
import warnings
import argparse
from openpyxl import load_workbook
from colorama import init, Fore, Style
import pandas as pd
import json

# Import from modules
from modules.logger import setup_logger, print_error
from modules.constants import *
from modules.file_operations import (
    load_json_without_notes,
    create_folder,
    copy_files,
    generate_tournament_config,
)
from modules.excel_operations import read_table_as_df, read_table_as_dict, verify_workbooks_closed
from modules.worksheet_setup import (
    set_up_tapi_worksheet,
    set_up_award_worksheet,
    set_up_meta_worksheet,
    resize_worksheets,
    add_essential_conditional_formats,  # Changed from add_conditional_formats
    copy_award_def,
    protect_worksheets,
    hide_worksheets,
    remove_external_links,
    fix_named_ranges,
)
from modules.ceremony_renderer import CeremonyRenderer
from modules.user_feedback import (
    ValidationSummary,
    ProgressTracker,
    print_section_header,
    print_success,
    print_warning,
    print_info,
    confirm_action,
)

# Suppress openpyxl warnings
warnings.simplefilter(action="ignore", category=UserWarning)

# Initialize colorama
init()


def print_splash():
    """Print MAESTRO splash screen."""
    print(f"\n{Fore.CYAN}{'█' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}█{Style.RESET_ALL}{'  ' * 34}{Fore.CYAN}█{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}█{Style.RESET_ALL}                       {Fore.YELLOW}╔╦╗╔═╗╔═╗╔═╗╔╦╗╦═╗╔═╗{Style.RESET_ALL}                        {Fore.CYAN}█{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}█{Style.RESET_ALL}                       {Fore.YELLOW}║║║╠═╣║╣ ╚═╗ ║ ╠╦╝║ ║{Style.RESET_ALL}                        {Fore.CYAN}█{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}█{Style.RESET_ALL}                       {Fore.YELLOW}╩ ╩╩ ╩╚═╝╚═╝ ╩ ╩╚═╚═╝{Style.RESET_ALL}                        {Fore.CYAN}█{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}█{Style.RESET_ALL}{'  ' * 34}{Fore.CYAN}█{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}█{Style.RESET_ALL}           {Fore.WHITE}Managing All Event Seasons, Tournaments,{Style.RESET_ALL}                 {Fore.CYAN}█{Style.RESET_ALL}"
    )
    print(
        f"{Fore.CYAN}█{Style.RESET_ALL}           {Fore.WHITE}Rosters, and OJSs for FIRST LEGO League{Style.RESET_ALL}                  {Fore.CYAN}█{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}█{Style.RESET_ALL}{'  ' * 34}{Fore.CYAN}█{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'█' * 70}{Style.RESET_ALL}\n")


def find_season_config_files(directory: str) -> list[str]:
    """Find and validate season configuration JSON files in the given directory.

    Args:
        directory: Path to directory to scan

    Returns:
        List of valid config filenames (sorted alphabetically)
    """
    logger.debug(f"Scanning for season config files in: {directory}")

    # Required keys for a valid season config
    required_keys = {
        "season_yr",
        "season_name",
        "tournament_folder",
        "filename",
        "tournament_template",
    }

    valid_files = []
    json_files = [f for f in os.listdir(directory) if f.endswith(".json")]

    logger.debug(f"Found {len(json_files)} .json files: {json_files}")

    for filename in json_files:
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if all required keys are present
            if required_keys.issubset(data.keys()):
                valid_files.append(filename)
                logger.debug(f"✓ Valid season config: {filename}")
            else:
                missing = required_keys - data.keys()
                logger.debug(f"✗ Invalid config {filename}: missing keys {missing}")
        except json.JSONDecodeError as e:
            logger.debug(f"✗ Invalid JSON {filename}: {e}")
        except Exception as e:
            logger.debug(f"✗ Error reading {filename}: {e}")

    valid_files.sort()
    logger.info(f"Found {len(valid_files)} valid season configuration file(s)")
    return valid_files


def select_config_file(valid_files: list[str]) -> str:
    """Prompt user to select a configuration file from the list.

    Args:
        valid_files: List of valid config filenames

    Returns:
        Selected filename
    """
    print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  SEASON CONFIGURATION FILES  {Style.RESET_ALL}".center(70))
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}\n")

    for i, filename in enumerate(valid_files, 1):
        print(f"  {i}. {filename}")

    print()

    while True:
        try:
            choice = input(
                f"{Fore.YELLOW}Select configuration file (1-{len(valid_files)}): {Style.RESET_ALL}"
            )
            index = int(choice) - 1
            if 0 <= index < len(valid_files):
                selected = valid_files[index]
                logger.info(f"User selected: {selected}")
                return selected
            else:
                print(
                    f"{Fore.RED}Invalid selection. Please enter a number between 1 and {len(valid_files)}.{Style.RESET_ALL}"
                )
        except ValueError:
            print(f"{Fore.RED}Invalid input. Please enter a number.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)


def parse_arguments():
    """Parse command-line arguments.

    Returns:
        Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Build tournament folders and populate OJS spreadsheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run normally
  %(prog)s --verbose          Run with INFO-level logging
  %(prog)s --debug            Run with DEBUG-level logging (most detailed)
  %(prog)s --tournament ABC   Build only tournament with short name 'ABC'
        """,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose mode: enable INFO-level logging and detailed output",
    )

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Debug mode: enable DEBUG-level logging (implies --verbose)",
    )

    parser.add_argument(
        "--tournament",
        "-t",
        type=str,
        metavar="NAME",
        help="Process only the specified tournament (by short name)",
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip pre-flight validation checks (not recommended)",
    )

    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup of existing OJS and config files (not recommended)",
    )

    return parser.parse_args()


def validate_environment(
    dir_path: str,
    config: dict,
    tournament_file: str,
    template_file: str,
    common_files: list[dict],
    divisions_only_files: list[dict],
    no_divisions_only_files: list[dict],
) -> ValidationSummary:
    """Validate the environment before processing.

    Args:
        dir_path: Working directory
        config: Configuration dictionary
        tournament_file: Path to tournament file
        template_file: Path to template file
        common_files: List of {source, dest} dicts for common files
        divisions_only_files: List of {source, dest} dicts for division-specific files
        no_divisions_only_files: List of {source, dest} dicts for non-division-specific files

    Returns:
        ValidationSummary with results
    """
    summary = ValidationSummary()

    # Check configuration
    required_config_keys = [
        "filename",
        "tournament_template",
        "season_yr",
        "season_name",
        "tournament_folder",
    ]
    missing = [k for k in required_config_keys if k not in config]
    if missing:
        summary.add_error(f"Missing config keys: {', '.join(missing)}")
    else:
        summary.add_info(
            f"Configuration valid: {config.get('season_name')} {config.get('season_yr')}"
        )

    # Check that workbooks are closed
    try:
        verify_workbooks_closed(tournament_file, template_file)
        summary.add_info("Tournament and template files are closed")
    except RuntimeError as e:
        summary.add_error(str(e))

    # Check tournament file
    if not os.path.exists(tournament_file):
        summary.add_error(f"Tournament file not found: {tournament_file}")
    else:
        summary.add_info(f"Tournament file found: {os.path.basename(tournament_file)}")

    # Check template file
    if not os.path.exists(template_file):
        summary.add_error(f"Template file not found: {template_file}")
    else:
        summary.add_info(f"Template file found: {os.path.basename(template_file)}")

    # Check extra files - combine all file lists and extract source filenames
    all_files = common_files + divisions_only_files + no_divisions_only_files
    missing_files = []
    for file_mapping in all_files:
        source_file = file_mapping.get("source", "")
        if source_file and not os.path.exists(os.path.join(dir_path, source_file)):
            missing_files.append(source_file)

    if missing_files:
        summary.add_warning(f"Missing optional files: {', '.join(missing_files)}")
    else:
        summary.add_info(f"All {len(all_files)} extra files found")

    return summary


def cleanup_tournament_folders(tournament_folder: str, tournaments_to_process: list[str]) -> dict:
    """Remove existing OJS and config files from tournament folders.

    Args:
        tournament_folder: Base tournament folder path
        tournaments_to_process: List of tournament short names to clean

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info("Starting cleanup of existing tournament files")

    stats = {"ojs_deleted": 0, "config_deleted": 0, "folders_processed": 0, "deletion_failures": []}

    for tourn_name in tournaments_to_process:
        folder_path = os.path.join(tournament_folder, tourn_name)

        if not os.path.exists(folder_path):
            continue

        stats["folders_processed"] += 1

        # Delete OJS files (*.xlsm)
        for file in os.listdir(folder_path):
            if file.endswith(".xlsm"):
                file_path = os.path.join(folder_path, file)
                try:
                    os.remove(file_path)
                    stats["ojs_deleted"] += 1
                    logger.debug(f"Deleted OJS file: {file}")
                except PermissionError as e:
                    error_msg = f"{tourn_name}/{file} (file may be open in Excel)"
                    stats["deletion_failures"].append(error_msg)
                    logger.warning(f"Permission denied deleting {file}: {e}")
                except Exception as e:
                    error_msg = f"{tourn_name}/{file} ({str(e)})"
                    stats["deletion_failures"].append(error_msg)
                    logger.warning(f"Could not delete {file}: {e}")

        # Delete tournament_config.json
        config_file = os.path.join(folder_path, "tournament_config.json")
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
                stats["config_deleted"] += 1
                logger.debug(f"Deleted config: {tourn_name}/tournament_config.json")
            except PermissionError as e:
                error_msg = f"{tourn_name}/tournament_config.json (file may be open)"
                stats["deletion_failures"].append(error_msg)
                logger.warning(f"Permission denied deleting tournament_config.json: {e}")
            except Exception as e:
                error_msg = f"{tourn_name}/tournament_config.json ({str(e)})"
                stats["deletion_failures"].append(error_msg)
                logger.warning(f"Could not delete tournament_config.json: {e}")

    print_info(
        f"Cleanup: {stats['ojs_deleted']} OJS files, {stats['config_deleted']} config files removed"
    )
    if stats["deletion_failures"]:
        print_warning(
            f"Failed to delete {len(stats['deletion_failures'])} file(s) - they may be open"
        )

    logger.info(f"Cleanup complete: {stats}")
    return stats


def resolve_fillin_template_filename(
    config: dict,
    using_divisions: bool,
    default_divisions: str = "champ_fillin_template-with-divisions.html.jinja",
    default_no_divisions: str = "fillin_template.html.jinja",
) -> str:
    """Pick the fill-in template filename from season config, with sensible fallbacks."""
    # Prefer the explicit season-level fillin_template entry
    if config:
        cfg_value = config.get("fillin_template")
        if cfg_value:
            return cfg_value

    return default_divisions if using_divisions else default_no_divisions


def main():
    """Main execution function."""
    args = parse_arguments()

    # Print splash screen
    print_splash()

    # Always print version info
    print(f"{Fore.CYAN}MAESTRO version:{Style.RESET_ALL} {__version__}")

    # Determine script directory FIRST
    if getattr(sys, "frozen", False):
        dir_path = os.path.dirname(sys.executable)
    elif __file__:
        dir_path = os.path.dirname(__file__)

    # Determine logging level (debug implies verbose)
    log_debug = args.debug or args.verbose

    # Set up logger with script directory
    global logger
    logger = setup_logger("ojs_builder", debug=log_debug, log_dir=dir_path)

    if args.debug:
        logger.info("Debug logging enabled")
    elif args.verbose:
        logger.info("Verbose logging enabled")

    print_info(f"Working directory: {dir_path}")

    # Find valid season configuration files
    valid_config_files = find_season_config_files(dir_path)

    if not valid_config_files:
        print_error(
            logger,
            "No valid season configuration files found",
            error_type="missing_config",
            context={
                "directory": dir_path,
                "required_keys": "season_yr, season_name, tournament_folder, filename, tournament_template",
            },
        )
        input("\nPress ENTER to exit...")
        sys.exit(1)

    # Select configuration file
    if len(valid_config_files) == 1:
        config_filename = valid_config_files[0]
        print_success(f"Using configuration file: {config_filename}")
        logger.info(f"Auto-selected single config file: {config_filename}")
    else:
        config_filename = select_config_file(valid_config_files)
        print_success(f"Selected: {config_filename}")

    # Load configuration
    try:
        config = load_json_without_notes(os.path.join(dir_path, config_filename))
        print_success("Configuration loaded")
    except json.JSONDecodeError as e:
        print_error(
            logger,
            f"Invalid JSON syntax in '{config_filename}'",
            e,
            error_type="invalid_json",
            context={"filename": config_filename},
        )
        input("\nPress ENTER to exit...")
        sys.exit(1)
    except Exception as e:
        print_error(logger, f"Error loading configuration file '{config_filename}'", e)
        input("\nPress ENTER to exit...")
        sys.exit(1)

    tournament_file = os.path.join(dir_path, config["filename"])
    template_file = os.path.join(dir_path, config["tournament_template"])

    # Get file lists for copying to tournament folders
    common_files = config.get("copy_file_list_common", [])
    divisions_only_files = config.get("copy_file_list_divisions_only", [])
    no_divisions_only_files = config.get("copy_file_list_no_divisions_only", [])

    tournament_folder = config["tournament_folder"]

    # Ensure tournament folder exists
    if not os.path.exists(tournament_folder):
        try:
            os.makedirs(tournament_folder)
            logger.info(f"Created tournament folder: {tournament_folder}")
            print_success(f"Created tournament folder: {tournament_folder}")
        except Exception as e:
            print_error(
                logger,
                f"Could not create tournament folder: {tournament_folder}",
                e,
                error_type="permission_denied",
                context={"filename": tournament_folder},
            )
    else:
        logger.debug(f"Tournament folder exists: {tournament_folder}")

    # Run validation (unless skipped)
    if not args.skip_validation:
        print_section_header("PRE-FLIGHT VALIDATION")

        validation = validate_environment(
            dir_path,
            config,
            tournament_file,
            template_file,
            common_files,
            divisions_only_files,
            no_divisions_only_files,
        )

        validation.display()

        if validation.has_errors():
            print_error(
                logger,
                "Validation failed. Please fix the errors above and try again.",
                error_type="invalid_data",
                context={"location": "pre-flight validation"},
            )

        # Just log warnings but proceed automatically
        if validation.warnings:
            logger.warning(f"Validation completed with {len(validation.warnings)} warning(s)")

    # Load tournament data
    print_section_header("LOADING TOURNAMENT DATA")

    try:
        logger.info(f"Opening {os.path.basename(tournament_file)}...")
        _ = load_workbook(tournament_file, data_only=True)
        print_success("Tournament file opened successfully")
    except Exception as e:
        print_error(
            logger,
            f"Could not open tournament file: {tournament_file}",
            e,
            error_type="file_open",
            context={"filename": os.path.basename(tournament_file)},
        )

    # Read season info
    try:
        dictSeasonInfo = read_table_as_dict(tournament_file, "SeasonInfo", "SeasonInfo")
        divisions_value = dictSeasonInfo["Divisions"]

        # Convert to boolean (handle string, bool, int)
        if isinstance(divisions_value, bool):
            using_divisions = divisions_value
        elif isinstance(divisions_value, str):
            using_divisions = divisions_value.upper() in ["TRUE", "YES", "1"]
        elif isinstance(divisions_value, (int, float)):
            using_divisions = bool(divisions_value)
        else:
            using_divisions = False

        logger.info(f"Using divisions: {using_divisions} (from value: {divisions_value})")
    except Exception as e:
        print_error(logger, "Could not read the SeasonInfo table", e)

    # Read tournaments
    try:
        if using_divisions:
            dfTournaments = read_table_as_df(
                tournament_file, "DivTournaments", "DivTournamentList"
            ).fillna(0)
        else:
            dfTournaments = read_table_as_df(
                tournament_file, "Tournaments", "TournamentList"
            ).fillna(0)
        logger.info(f"Loaded {len(dfTournaments)} tournament(s)")
    except Exception as e:
        print_error(logger, "Could not read the tournament worksheet", e)

    # Read award definitions
    try:
        dfAwardDef = read_table_as_df(tournament_file, "AwardDef", "AwardDef").fillna(0)
        logger.info(f"Loaded {len(dfAwardDef)} award definitions")
    except Exception as e:
        print_error(logger, "Could not read the AwardDef worksheet", e)

    # Read assignments
    try:
        dfAssignments = read_table_as_df(tournament_file, "Assignments", "Assignments").fillna(0)
        tourn_array = dfTournaments[COL_SHORT_NAME].tolist()
        print_success(f"Loaded {len(dfAssignments)} team assignments")
    except Exception as e:
        print_error(
            logger,
            "Could not read the assignments worksheet",
            e,
            error_type="missing_sheet",
            context={
                "workbook": os.path.basename(tournament_file),
                "sheet_name": "Assignments",
                "available_sheets": [],
            },
        )

    # Tournament selection
    if args.tournament:
        # Use tournament from command line
        tourn = args.tournament
        if tourn in tourn_array:
            dfTournaments = dfTournaments.loc[dfTournaments[COL_SHORT_NAME] == tourn]
            logger.info(f"Building single tournament from --tournament arg: {tourn}")
            print_success(f"Building single tournament: {tourn}")
        else:
            print_error(
                logger,
                f"Tournament '{tourn}' not found",
                error_type="invalid_data",
                context={
                    "location": "tournament selection",
                    "expected": f"One of: {', '.join(tourn_array)}",
                    "found": tourn,
                },
            )
    else:
        print_section_header("TOURNAMENT SELECTION")

        if len(tourn_array) > 1:
            print_info(f"Available tournaments: {', '.join(tourn_array)}")

            tourn = input(
                f"{Fore.CYAN}Enter tournament short name, or press ENTER for all: {Style.RESET_ALL}"
            ).strip()
        else:
            print_info(f"Single tournament detected: {tourn_array[0]}")
            tourn = ""

        if tourn != "":
            if tourn in tourn_array:
                dfTournaments = dfTournaments.loc[dfTournaments[COL_SHORT_NAME] == tourn]
                print_success(f"Building single tournament: {tourn}")
            else:
                print_error(
                    logger,
                    f"Tournament '{tourn}' not found",
                    error_type="invalid_data",
                    context={
                        "location": "tournament selection",
                        "expected": f"One of: {', '.join(tourn_array)}",
                        "found": tourn,
                    },
                )

    # Cleanup existing files (unless skipped)
    if not args.no_cleanup:
        print_section_header("CLEANUP")
        print_info("Removing existing OJS and config files...")

        # Get list of tournaments to clean
        tournaments_to_clean = dfTournaments[COL_SHORT_NAME].unique().tolist()

        # Automatically proceed with cleanup
        logger.info(f"Automatic cleanup of {len(tournaments_to_clean)} tournaments")
        print_info(f"Cleaning up {len(tournaments_to_clean)} existing tournament folder(s)")

        cleanup_stats = cleanup_tournament_folders(tournament_folder, tournaments_to_clean)

        print_success(f"Cleanup complete: {cleanup_stats['folders_processed']} folders processed")

        # Display deletion failures if any
        if cleanup_stats["deletion_failures"]:
            print(
                f"\n{Fore.YELLOW}⚠ Could not delete {len(cleanup_stats['deletion_failures'])} file(s):{Style.RESET_ALL}"
            )
            for failure in cleanup_stats["deletion_failures"]:
                print(f"  • {failure}")
            print(
                f"\n{Fore.RED}ERROR: Close any open Excel files and try again.{Style.RESET_ALL}\n"
            )
            logger.error("Deletion failures detected - cannot proceed")
            sys.exit(1)
    else:
        logger.info("No existing files to clean up")

    # Process tournaments automatically
    print_section_header("PROCESSING TOURNAMENTS")

    # Track division mismatches and award count mismatches for final summary
    division_mismatches = []
    award_count_issues = {}  # tournament_name -> list of mismatch messages

    for index, row in dfTournaments.iterrows():
        tournament_name = f"{row[COL_SHORT_NAME]} {row.get(COL_DIVISION, '')}".strip()

        print(f"\n{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  {tournament_name}  {Style.RESET_ALL}".center(70))
        print(f"{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}\n")
        progress = ProgressTracker(10, f"Setting up {row[COL_SHORT_NAME]}")

        # Create folder
        newpath = os.path.join(tournament_folder, row[COL_SHORT_NAME])
        create_folder(newpath)
        progress.update("Folder created")

        # Copy files
        copy_files(
            row,
            dir_path,
            template_file,
            common_files,
            divisions_only_files,
            no_divisions_only_files,
            tournament_folder,
            using_divisions,
        )
        progress.update("Files copied")

        # Render fill-in awards form (paper backup) directly into the tournament folder
        try:
            # Use maestro root directory to find fill-in template (not copied to tournament folder)
            renderer = CeremonyRenderer(dir_path)

            # Select template based on divisions - this is an early/simple render
            # The more detailed render happens after tournament_config.json is created
            fillin_template_file = resolve_fillin_template_filename(
                config,
                using_divisions,
                default_divisions="champ_fillin_template-with-divisions.html.jinja",
                default_no_divisions="fillin_template.html.jinja",
            )

            fillin_output = os.path.join(newpath, "fillin_form.html")

            template_data = {
                "tournament_name": row.get(COL_LONG_NAME, row.get(COL_SHORT_NAME, "")),
                "awards_config": config.get("AWARDS", []),
            }

            errors, warnings = renderer.validate_template_variables(
                fillin_template_file, template_data, set()
            )
            if errors:
                logger.error(f"Fill-in template missing critical variables: {errors}")
            if warnings:
                print_warning(f"Fill-in form missing optional variables: {', '.join(warnings)}")

            if renderer.render(fillin_template_file, template_data, fillin_output):
                print_success("Fill-in awards form created")
            else:
                print_warning("Fill-in awards form could not be generated")
                logger.warning(f"Fill-in form render failed for {newpath}")
        except Exception as e:
            print_warning("Unable to generate fill-in awards form")
            logger.warning(f"Fill-in form generation failed for {newpath}: {e}")

        # Process OJS file
        ojs_name = row.get(COL_OJS_FILENAME)
        if ojs_name is None or (isinstance(ojs_name, float) and pd.isna(ojs_name)):
            print_warning(f"No OJS filename for {row[COL_SHORT_NAME]}, skipping")
            logger.warning(f"No OJS filename for {row[COL_SHORT_NAME]}, skipping")
            continue

        ojs_path = os.path.join(tournament_folder, row[COL_SHORT_NAME], ojs_name)

        ojs_book = load_workbook(ojs_path, read_only=False, keep_vba=True)

        # Check if there are teams assigned; skip if not
        has_teams = set_up_tapi_worksheet(row, ojs_book, dfAssignments, using_divisions)

        if not has_teams:
            ojs_book.close()
            # Delete the OJS file we just created since there are no teams
            if os.path.exists(ojs_path):
                os.remove(ojs_path)
            print_warning(f"No teams assigned to {tournament_name}, OJS file removed")
            logger.warning(f"Skipped {tournament_name} - no teams assigned")
            continue

        # Process the tournament (only reached if has_teams is True)
        try:
            progress.update("Team info added")

            set_up_award_worksheet(row, ojs_book, dfAwardDef, using_divisions)
            progress.update("Awards configured")

            set_up_meta_worksheet(row, ojs_book, config, tournament_folder, using_divisions)
            progress.update("Metadata added")

            # Skipping copy_award_def: AwardDef table is not used by downstream tools

            hide_worksheets(row, ojs_book)
            progress.update("Worksheets hidden")

            resize_worksheets(row, ojs_book, dfAssignments, using_divisions)
            progress.update("Tables resized")

            # Add essential conditional formatting AFTER resize
            add_essential_conditional_formats(
                ojs_book, len(dfAssignments[dfAssignments[COL_SHORT_NAME] == row[COL_SHORT_NAME]])
            )

            protect_worksheets(row, ojs_book)
            progress.update("Protection applied")

            # Fix named ranges (especially "Awards" range)
            fix_named_ranges(ojs_book)

            # Remove any external workbook links before saving
            remove_external_links(ojs_book)
            progress.update("Links removed")

        finally:
            ojs_book.save(ojs_path)
            ojs_book.close()

        # Generate tournament config file
        mismatch_detected, tourn_name, award_mismatches = generate_tournament_config(
            row, config, dfAwardDef, using_divisions, tournament_folder
        )

        if mismatch_detected:
            division_mismatches.append(tourn_name)

        if award_mismatches:
            award_count_issues[tourn_name] = award_mismatches

        # Render fill-in awards form (paper backup) into the tournament folder
        try:
            config_path = os.path.join(newpath, "tournament_config.json")
            if not os.path.exists(config_path):
                logger.warning(f"Fill-in form skipped; config not found: {config_path}")
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    tourn_config = json.load(f)

                # Use maestro root directory to find fill-in template (not copied to tournament folder)
                renderer = CeremonyRenderer(dir_path)

                # Prepare fill-in rows grouped by award type
                info_section = tourn_config.get("INFO", {})
                awards_cfg = tourn_config.get("AWARDS", [])
                using_divs = info_section.get("using_divisions", False)

                # Select template based on divisions, preferring filenames from config
                fillin_template_file = info_section.get("fillin_template")
                if not fillin_template_file:
                    fillin_template_file = resolve_fillin_template_filename(
                        config,
                        using_divs,
                        default_divisions="champ_fillin_template-with-divisions.html.jinja",
                        default_no_divisions="fillin_template.html.jinja",
                    )

                fillin_output = os.path.join(newpath, "fillin_form.html")

                def ordinal(n: int) -> str:
                    n = int(n)
                    mod100, mod10 = n % 100, n % 10
                    if mod100 in (11, 12, 13):
                        suffix = "th"
                    elif mod10 == 1:
                        suffix = "st"
                    elif mod10 == 2:
                        suffix = "nd"
                    elif mod10 == 3:
                        suffix = "rd"
                    else:
                        suffix = "th"
                    return f"{n}{suffix}"

                def build_label(base: str, idx: int, labels: list[str]) -> str:
                    # If a custom label exists, use it directly (labels already include award name)
                    if labels and len(labels) > idx and labels[idx]:
                        return labels[idx]
                    # Otherwise, construct default label with base name and ordinal
                    return f"{base}, {ordinal(idx + 1)} Place"

                def expand_award(award: dict) -> list[str]:
                    labels = award.get("Labels", [])
                    rows: list[str] = []
                    if using_divs and award.get("DivAwd", False):
                        d1 = int(award.get("D1_count", 0))
                        d2 = int(award.get("D2_count", 0))
                        for i in range(d1):
                            rows.append(
                                build_label(f"Division 1 {award.get('Name', '')}", i, labels)
                            )
                        for i in range(d2):
                            rows.append(
                                build_label(f"Division 2 {award.get('Name', '')}", i, labels)
                            )
                    else:
                        count = int(award.get("TournCount", 0))
                        for i in range(count):
                            rows.append(build_label(award.get("Name", ""), i, labels))
                    return rows

                # Group awards
                rows_robot: list[str] = []
                rows_core: list[str] = []  # IP / RD / CV
                rows_judges: list[str] = []  # J_AWD_Judges*
                rows_other: list[str] = []  # Other J_AWD_* (non-champ, non-core, non-judges)
                rows_champs: list[str] = []  # Champions

                for award in awards_cfg:
                    award_id = award.get("ID", "")
                    if not award_id:
                        continue

                    if award_id == "P_AWD_RG":
                        rows_robot.extend(expand_award(award))
                    elif award_id in {"J_AWD_IP", "J_AWD_RD", "J_AWD_CV"}:
                        rows_core.extend(expand_award(award))
                    elif award_id.startswith("J_AWD_Judges"):
                        rows_judges.extend(expand_award(award))
                    elif award_id.startswith("J_AWD_CHAMP"):
                        rows_champs.extend(expand_award(award))
                    elif award_id.startswith("J_AWD_"):
                        rows_other.extend(expand_award(award))

                template_data = {
                    "tournament_name": info_section.get("tournament_long_name", ""),
                    "rows_robot": rows_robot,
                    "rows_core": rows_core,
                    "rows_judges": rows_judges,
                    "rows_other": rows_other,
                    "rows_champs": rows_champs,
                    "adv_count": row.get(COL_ADVANCING, 0),
                    "division_label": row.get(COL_DIVISION, ""),
                    "using_divisions": using_divs,
                }

                errors, warnings = renderer.validate_template_variables(
                    fillin_template_file, template_data, set()
                )
                if errors:
                    logger.error(f"Fill-in template missing critical variables: {errors}")
                if warnings:
                    print_warning(f"Fill-in form missing optional variables: {', '.join(warnings)}")

                if renderer.render(fillin_template_file, template_data, fillin_output):
                    print_success("Fill-in awards form created")
                else:
                    print_warning("Fill-in awards form could not be generated")
                    logger.warning(f"Fill-in form render failed for {newpath}")
        except Exception as e:
            print_warning("Unable to generate fill-in awards form")
            logger.warning(f"Fill-in form generation failed for {newpath}: {e}")

        progress.complete(f"✓ {tournament_name} complete!")

    print(f"\n{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ALL TOURNAMENTS PROCESSED SUCCESSFULLY!  {Style.RESET_ALL}".center(70))
    print(f"{Fore.GREEN}{'═' * 60}{Style.RESET_ALL}\n")

    # Important note about VBA references
    print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}IMPORTANT:{Style.RESET_ALL}")
    print(f"If Excel shows 'Update Links' warnings when opening OJS files:")
    print(f"  1. Click 'Don't Update' or 'Break Links'")
    print(f"  2. Press Alt+F11, go to Tools → References")
    print(f"  3. Uncheck any MISSING references")
    print(f"  4. Save the file\n")
    print(f"To prevent this: Clean the template file's VBA references first.")
    print(f"{Fore.CYAN}{'─' * 60}{Style.RESET_ALL}\n")

    logger.info("All tournaments processed successfully")

    # Track if there were any warnings or issues
    has_warnings = bool(division_mismatches or award_count_issues)

    # Display division mismatch summary if any occurred
    if division_mismatches:
        logger.warning(f"Division mismatches detected in {len(division_mismatches)} tournament(s)")
        print(f"\n{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  ⚠ DIVISION MISMATCH SUMMARY  {Style.RESET_ALL}".center(70))
        print(f"{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}\n")
        print(
            f"{Fore.YELLOW}The following tournament(s) had division mismatch issues:{Style.RESET_ALL}"
        )
        for tourn in division_mismatches:
            print(f"  • {tourn}")
        print(
            f"\n{Fore.YELLOW}These tournaments had tournament_config.json with using_divisions=false,"
        )
        print(
            f"but appeared to use divisions. The setting has been changed to true.{Style.RESET_ALL}"
        )
        print(f"\n{Fore.RED}⚠ ACTION REQUIRED:{Style.RESET_ALL}")
        print(f"  Check season workbook settings before proceeding.")
        print(f"  OJS files may not work as expected if division settings are incorrect.\n")
        print(f"{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}\n")

    # Display award configuration warnings if any occurred
    if award_count_issues:
        logger.warning(
            f"Award configuration warnings detected in {len(award_count_issues)} tournament(s)"
        )
        print(f"\n{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  ⚠ AWARD CONFIGURATION WARNINGS  {Style.RESET_ALL}".center(70))
        print(f"{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}\n")
        print(
            f"{Fore.YELLOW}The following award configuration issues were detected:{Style.RESET_ALL}\n"
        )
        for tourn, mismatches in award_count_issues.items():
            print(f"{Fore.CYAN}{tourn}:{Style.RESET_ALL}")
            for mismatch in mismatches:
                print(f"  • {mismatch}")
            print()
        print(f"{Fore.RED}⚠ ACTION REQUIRED:{Style.RESET_ALL}")
        print(f"  Check the season workbook AwardDef and tournament tables.")
        print(f"  Verify DivAward settings match your template requirements.")
        print(f"  For division tournaments, awards typically need DivAwd=TRUE.\n")
        print(f"{Fore.YELLOW}{'═' * 60}{Style.RESET_ALL}\n")

    # Final exit message with warning reminder if needed
    if has_warnings:
        print(f"\n{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠ WARNINGS DETECTED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 60}{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Tournament files generated but there are warnings above.{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}Please review the warnings carefully before distributing OJS files.{Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}Check the season workbook and re-run if corrections are needed.{Style.RESET_ALL}\n"
        )
        input(f"{Fore.YELLOW}Press ENTER to exit...{Style.RESET_ALL}")
    else:
        input("\nPress ENTER to exit...")


if __name__ == "__main__":
    main()
