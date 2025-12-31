"""TOAST - Tournament OJS And Script Toolkit

Generate closing ceremony scripts from OJS files for FIRST LEGO League tournaments.

Run notes:
- Run from inside a tournament folder so `tournament_config.json` and OJS files are discovered in the working directory.
- Outputs (script and summary) are written to the working directory; logs stay beside this script.
- Use `--verbose` or `--debug` for more detail.

Usage:
    python fll-toast.py [--verbose] [--debug]
"""

import os
import sys
import json
import logging
import warnings
import argparse
from colorama import init, Fore, Style

# Application version. Override at build/run via TOAST_VERSION environment variable.
__version__ = "0.9.1"

# Suppress openpyxl warnings about conditional formatting
warnings.simplefilter(action="ignore", category=UserWarning)

# Add modules directory to path
sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setup_logger, print_error
from modules.ceremony_validator import OJSValidator
from modules.ceremony_data_collector import CeremonyDataCollector
from modules.ceremony_renderer import CeremonyRenderer

# Initialize colorama
init()


def print_splash():
    """Print TOAST splash screen."""
    print(f"\n{Fore.YELLOW}{'█' * 72}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}█{Style.RESET_ALL}{'  ' * 35}{Fore.YELLOW}█{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}█{Style.RESET_ALL}                           {Fore.CYAN}╔╦╗╔═╗╔═╗╔═╗╔╦╗{Style.RESET_ALL}                            {Fore.YELLOW}█{Style.RESET_ALL}"
    )
    print(
        f"{Fore.YELLOW}█{Style.RESET_ALL}                           {Fore.CYAN} ║ ║ ║╠═╣╚═╗ ║ {Style.RESET_ALL}                            {Fore.YELLOW}█{Style.RESET_ALL}"
    )
    print(
        f"{Fore.YELLOW}█{Style.RESET_ALL}                           {Fore.CYAN} ╩ ╚═╝╩ ╩╚═╝ ╩ {Style.RESET_ALL}                            {Fore.YELLOW}█{Style.RESET_ALL}"
    )
    print(f"{Fore.YELLOW}█{Style.RESET_ALL}{'  ' * 35}{Fore.YELLOW}█{Style.RESET_ALL}")
    print(
        f"{Fore.YELLOW}█{Style.RESET_ALL}       {Fore.WHITE}Tournament OJS And Script Toolkit for FIRST LEGO League{Style.RESET_ALL}        {Fore.YELLOW}█{Style.RESET_ALL}"
    )
    print(f"{Fore.YELLOW}█{Style.RESET_ALL}{'  ' * 35}{Fore.YELLOW}█{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'█' * 72}{Style.RESET_ALL}\n")


def resolve_version() -> str:
    """Return the runtime version string."""
    env_version = os.environ.get("TOAST_VERSION", "").strip()
    if env_version:
        return env_version
    return __version__


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(70)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")


def print_error_msg(text: str):
    """Print an error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def load_config(config_path: str) -> dict:
    """Load tournament configuration file."""
    logger.info(f"Loading configuration from: {config_path}")

    if not os.path.exists(config_path):
        print_error(logger, f"Configuration file not found: {config_path}")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("✓ Configuration loaded successfully")
        return config
    except json.JSONDecodeError as e:
        print_error(logger, f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        print_error(logger, f"Error loading configuration: {e}")
    return None


def generate_output_filename(ojs_files: list, suffix: str = "closing-ceremony") -> str:
    """Generate output filename based on the first OJS filename."""
    first = ojs_files[0]
    filename = first["filename"] if isinstance(first, dict) else str(first)
    base_name = os.path.splitext(os.path.basename(filename))[0]
    output_name = f"{base_name}-{suffix}.html"
    logger.debug(f"Generated output filename: {output_name}")
    return output_name


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TOAST - Tournament OJS And Script Toolkit: Generate closing ceremony scripts"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (INFO level)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging (DEBUG level, implies --verbose)",
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()

    version = resolve_version()

    if args.debug:
        log_debug = True
    elif args.verbose:
        log_debug = False  # INFO level
    else:
        log_debug = False  # Default (WARNING level in setup_logger when debug=False)

    print_splash()
    print(f"{Fore.CYAN}TOAST version:{Style.RESET_ALL} {version}")

    if getattr(sys, "frozen", False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    cwd_dir = os.getcwd()
    if os.path.exists(os.path.join(cwd_dir, "tournament_config.json")):
        base_dir = cwd_dir
        base_note = "working directory"
    else:
        base_dir = script_dir
        base_note = "script directory"

    global logger
    logger = setup_logger("ceremony_generator", debug=log_debug, log_dir=script_dir)
    logger.info(f"TOAST version: {version}")

    if args.debug:
        logger.info("Debug logging enabled")
    elif args.verbose:
        logger.info("Verbose logging enabled")

    logger.info(f"Script location: {script_dir}")
    logger.info(f"Asset base: {base_dir} ({base_note})")

    config_path = os.path.join(base_dir, "tournament_config.json")
    config = load_config(config_path)

    if not config:
        print_error(logger, "Unable to load configuration; exiting.")
        sys.exit(1)

    required_config_keys = ["INFO", "AWARDS"]
    missing_config = [key for key in required_config_keys if key not in config]
    if missing_config:
        print_error(logger, f"Missing required config section(s): {', '.join(missing_config)}")
        sys.exit(1)

    info = config["INFO"]

    required_info_keys = ["using_divisions", "ojs_files", "tournament_long_name"]
    missing_info = [key for key in required_info_keys if key not in info]
    if missing_info:
        print_error(logger, f"Missing required INFO key(s): {', '.join(missing_info)}")
        sys.exit(1)

    using_divisions = info["using_divisions"]

    def normalize_ojs_files(raw_list):
        normalized = []
        if not isinstance(raw_list, list):
            print_error(
                logger, "INFO.ojs_files must be a list of objects with filename and division"
            )
        for idx, entry in enumerate(raw_list):
            if isinstance(entry, dict):
                filename = entry.get("filename")
                division = entry.get("division") or entry.get("div") or ""
            else:
                filename = str(entry)
                division = f"D{idx + 1}" if using_divisions else ""

            if not filename:
                print_error(logger, f"INFO.ojs_files[{idx}] is missing a filename")

            div_str = "" if division is None else str(division).strip()
            if div_str:
                div_str = div_str.upper()
                if not div_str.startswith("D"):
                    div_str = f"D{div_str}"

            normalized.append({"division": div_str, "filename": filename})

        if not normalized:
            print_error(logger, "INFO.ojs_files is empty")
        return normalized

    ojs_files = normalize_ojs_files(info["ojs_files"])

    # Derive dual emcee highlighting from Team and Program Information!F2 in any OJS
    dual_emcee = False
    for entry in ojs_files:
        ojs_file = entry["filename"]
        ojs_path = os.path.join(base_dir, ojs_file)
        if os.path.exists(ojs_path):
            try:
                from openpyxl import load_workbook

                wb = load_workbook(ojs_path, data_only=True)
                ws = wb["Team and Program Information"]
                dual_emcee_value = ws["F2"].value
                wb.close()

                if isinstance(dual_emcee_value, bool):
                    if dual_emcee_value:
                        dual_emcee = True
                        logger.debug(f"Dual emcee enabled from {ojs_file}")
                        break
                elif isinstance(dual_emcee_value, str):
                    if dual_emcee_value.upper() in ["TRUE", "YES", "1"]:
                        dual_emcee = True
                        logger.debug(f"Dual emcee enabled from {ojs_file}")
                        break
                elif isinstance(dual_emcee_value, (int, float)):
                    if dual_emcee_value:
                        dual_emcee = True
                        logger.debug(f"Dual emcee enabled from {ojs_file}")
                        break
            except Exception as e:
                logger.debug(f"Could not read dual_emcee from {ojs_file}: {e}")

    print(f"{Fore.CYAN}Tournament:{Style.RESET_ALL} {info['tournament_long_name']}")
    print(f"{Fore.CYAN}Using divisions:{Style.RESET_ALL} {using_divisions}")
    print(f"{Fore.CYAN}OJS files:{Style.RESET_ALL} {len(ojs_files)}")
    print(f"{Fore.CYAN}Dual emcee:{Style.RESET_ALL} {dual_emcee}")

    print_header("VALIDATING OJS FILES")
    for entry in ojs_files:
        ojs_file = entry["filename"]
        ojs_path = os.path.join(base_dir, ojs_file)
        if os.path.exists(ojs_path):
            print_success(f"Found: {ojs_file}")
        else:
            print_error(logger, f"OJS file not found: {ojs_file}")

    print_header("VALIDATING OJS DATA")
    validator = OJSValidator()
    for idx, entry in enumerate(ojs_files):
        ojs_file = entry["filename"]
        division_label = entry.get("division") or f"Division {idx + 1}" if using_divisions else ""
        ojs_path = os.path.join(base_dir, ojs_file)
        print(
            f"\n{Fore.YELLOW}Validating {ojs_file} ({division_label or 'No Division'})...{Style.RESET_ALL}"
        )
        validator.validate_all_sheets(ojs_path, division_label)

    if validator.has_errors():
        print(f"\n{Fore.RED}{'═' * 70}{Style.RESET_ALL}")
        print(f"{Fore.RED}VALIDATION FAILED{Style.RESET_ALL}".center(78))
        print(f"{Fore.RED}{'═' * 70}{Style.RESET_ALL}\n")
        print(f"{Fore.RED}Errors found:{Style.RESET_ALL}")
        for error in validator.errors:
            print(f"  {error}")
        if validator.warnings:
            print(f"\n{Fore.YELLOW}Warnings:{Style.RESET_ALL}")
            for warning in validator.warnings:
                print(f"  {warning}")
        print(f"\n{Fore.RED}Please fix the errors above and run the script again.{Style.RESET_ALL}")
        input("\nPress ENTER to exit...")
        sys.exit(1)

    if validator.warnings:
        print(f"\n{Fore.YELLOW}Warnings found:{Style.RESET_ALL}")
        for warning in validator.warnings:
            print(f"  {warning}")
        response = (
            input(f"\n{Fore.YELLOW}Continue despite warnings? [Y/n]: {Style.RESET_ALL}")
            .strip()
            .lower()
        )
        if response and response not in ["y", "yes"]:
            print("Operation cancelled by user")
            sys.exit(0)

    print_success("All validations passed!")

    print_header("COLLECTING AWARD DATA")
    collector = CeremonyDataCollector(config, dual_emcee=dual_emcee)
    template_data = {}
    template_data["tournament_name"] = info["tournament_long_name"]
    template_data["using_divisions"] = 1 if using_divisions else 0
    template_data["dual_emcee"] = dual_emcee
    template_data["awards_config"] = config["AWARDS"]

    division_entries = []
    for idx, entry in enumerate(ojs_files):
        code = entry.get("division") or (f"D{idx + 1}" if using_divisions else "")
        code = code.upper() if code else ""
        if code and not code.startswith("D"):
            code = f"D{code}"
        label = ""
        if using_divisions:
            if code:
                label = f"Division {code[1:]}" if code.startswith("D") else f"Division {code}"
            else:
                label = f"Division {idx + 1}"
        else:
            label = "Tournament"

        division_entries.append(
            {
                "code": code,
                "label": label,
                "filename": entry["filename"],
                "path": os.path.join(base_dir, entry["filename"]),
            }
        )

    print("Collecting team lists...")
    if using_divisions:
        for entry in division_entries:
            teams = collector.collect_team_list(entry["path"], entry["label"])
            if entry["code"] == "D1":
                template_data["div1_list"] = collector.format_team_list_as_html(teams)
            elif entry["code"] == "D2":
                template_data["div2_list"] = collector.format_team_list_as_html(teams)
    else:
        all_teams = collector.collect_team_list(division_entries[0]["path"])
        template_data["team_list"] = collector.format_team_list_as_html(all_teams)

    print("Collecting advancing teams...")
    if using_divisions:
        for entry in division_entries:
            adv = collector.collect_advancing_teams(entry["path"], entry["label"])
            if entry["code"] == "D1":
                template_data["ADV_D1"] = collector.format_team_list_as_html(adv)
            elif entry["code"] == "D2":
                template_data["ADV_D2"] = collector.format_team_list_as_html(adv)
    else:
        adv_teams = collector.collect_advancing_teams(division_entries[0]["path"])
        template_data["ADV"] = collector.format_team_list_as_html(adv_teams)

    print("Collecting award winners...")
    for award in config["AWARDS"]:
        award_id = award["ID"]
        award_name = award["Name"]
        is_div_award = award["DivAwd"]
        print(f"  Processing {award_name}...")

        if award_id == "P_AWD_RG":
            if using_divisions and is_div_award:
                for entry in division_entries:
                    count_field = f"{entry['code']}_count" if entry["code"] else ""
                    count = int(award.get(count_field, 0)) if count_field else 0
                    if count > 0:
                        rg = collector.collect_robot_game_awards(
                            entry["path"], count, entry["label"]
                        )
                        tag_field = f"ScriptTag{entry['code']}" if entry["code"] else ""
                        tag = award.get(tag_field, "") if tag_field else ""
                        if tag:
                            template_data[tag] = collector.format_winners_as_html(
                                rg, include_score=True
                            )
            else:
                tourn_count = int(award.get("TournCount", 0))
                if tourn_count > 0:
                    rg_winners = collector.collect_robot_game_awards(
                        division_entries[0]["path"], tourn_count, ""
                    )
                    tag = award.get("ScriptTagNoDiv", "")
                    if tag:
                        template_data[tag] = collector.format_winners_as_html(
                            rg_winners, include_score=True
                        )
        else:
            if using_divisions and is_div_award:
                labels = award.get("Labels", [])

                for entry in division_entries:
                    count_field = f"{entry['code']}_count" if entry["code"] else ""
                    count = int(award.get(count_field, 0)) if count_field else 0
                    if count <= 0:
                        continue

                    division_labels = labels[:count]
                    winners = collector.collect_judged_awards(
                        entry["path"], award, division_labels, entry["label"], entry["filename"]
                    )
                    tag_field = f"ScriptTag{entry['code']}" if entry["code"] else ""
                    tag = award.get(tag_field, "") if tag_field else ""
                    if tag:
                        template_data[tag] = collector.format_winners_as_html(winners)

                    if award_id == "J_AWD_IP" and "ip_this_these" not in template_data:
                        template_data["ip_this_these"] = (
                            "this team" if len(winners) == 1 else "these teams"
                        )
                    elif award_id == "J_AWD_RD" and "rd_this_these" not in template_data:
                        template_data["rd_this_these"] = (
                            "this team" if len(winners) == 1 else "these teams"
                        )
            else:
                tourn_count = int(award.get("TournCount", 0))
                labels = award.get("Labels", [])

                if tourn_count > 0:
                    all_winners = []
                    for entry in division_entries:
                        winners = collector.collect_judged_awards(
                            entry["path"], award, labels, "", entry["filename"]
                        )
                        all_winners.extend(winners)

                    if len(all_winners) < tourn_count:
                        missing_count = tourn_count - len(all_winners)
                        collector.warnings.append(
                            f"{award_name} tournament award: {len(all_winners)} selected, {tourn_count} allocated ({missing_count} under-allocated)"
                        )
                    elif len(all_winners) > tourn_count:
                        extra_count = len(all_winners) - tourn_count
                        collector.warnings.append(
                            f"{award_name} tournament award: {len(all_winners)} selected, {tourn_count} allocated ({extra_count} OVER-allocated)"
                        )

                    tag = award.get("ScriptTagNoDiv", "")
                    if tag:
                        template_data[tag] = collector.format_winners_as_html(all_winners)

                    if award_id == "J_AWD_Judges":
                        template_data["ja_count"] = len(all_winners)
                        template_data["ja_go_goes"] = (
                            "The judges award goes to:"
                            if len(all_winners) == 1
                            else "The judges awards go to:"
                        )

    # Pre-seed optional template variables so missing tags render as empty strings
    expected_vars = [
        "div1_list",
        "div2_list",
        "team_list",
        "ADV_D1",
        "ADV_D2",
        "ip_this_these",
        "rd_this_these",
        "ja_go_goes",
    ]
    for var in expected_vars:
        if var not in template_data:
            template_data[var] = ""

    # Set ja_count to 0 if not already set (must be int for template comparison)
    if "ja_count" not in template_data:
        template_data["ja_count"] = 0

    print_success(f"Collected data for {len(template_data)} template variables")

    if collector.warnings:
        print(f"\n{Fore.YELLOW}Data collection warnings:{Style.RESET_ALL}")
        for warning in collector.warnings:
            print(f"  {warning}")

    print_header("RENDERING CEREMONY OUTPUTS")

    renderer = CeremonyRenderer(base_dir)
    all_success = True
    output_files = []

    print(f"{Fore.CYAN}Rendering ceremony script...{Style.RESET_ALL}")

    # Get script template filename from config, with fallback to default
    script_template_file = info.get("script_template", "script_template.html.jinja")
    logger.debug(f"Using script template: {script_template_file}")

    # Determine critical variables based on actual divisions present
    if using_divisions:
        division_codes = {entry["code"] for entry in division_entries if entry["code"]}
        has_d1 = "D1" in division_codes
        has_d2 = "D2" in division_codes

        critical_vars = set()
        if has_d1:
            critical_vars.update({"J_AWD_CHAMP_D1", "ADV_D1"})
        if has_d2:
            critical_vars.update({"J_AWD_CHAMP_D2", "ADV_D2"})

        if has_d1 and has_d2:
            logger.info("Both divisions present - D1 and D2 variables required")
        elif has_d1:
            logger.info("Single-division tournament detected - only D1 variables required")
            print(
                f"{Fore.CYAN}Note: Only Division 1 present - D2 variables optional{Style.RESET_ALL}"
            )
        elif has_d2:
            logger.info("Single-division tournament detected - only D2 variables required")
            print(
                f"{Fore.CYAN}Note: Only Division 2 present - D1 variables optional{Style.RESET_ALL}"
            )
        else:
            logger.info("Division tournament configured but no D1/D2 codes found in ojs_files")
    else:
        critical_vars = set()  # Non-division tournaments have no critical division vars

    errors, warnings = renderer.validate_template_variables(
        script_template_file, template_data, critical_vars
    )

    if errors:
        print(f"{Fore.RED}Missing critical template variables:{Style.RESET_ALL}")
        for err in errors:
            print(f"  {err}")
        print(
            f"\n{Fore.RED}Cannot generate ceremony script with missing critical variables.{Style.RESET_ALL}"
        )
        input("\nPress ENTER to exit...")
        sys.exit(1)

    if warnings:
        print(f"{Fore.YELLOW}Missing script template variables (will be empty):{Style.RESET_ALL}")
        for warn in warnings:
            print(f"  {warn}")

    script_filename = generate_output_filename(ojs_files, "closing-ceremony")
    script_path = os.path.join(base_dir, script_filename)

    if renderer.render(script_template_file, template_data, script_path):
        print_success(f"Ceremony script: {script_filename}")
        output_files.append(script_path)
    else:
        print_error_msg("Failed to render ceremony script")
        all_success = False

    print(f"\n{Fore.CYAN}Rendering ceremony summary...{Style.RESET_ALL}")

    # Get summary template filename from config, with fallback to default
    summary_template_file = info.get("summary_template", "summary_template.html.jinja")
    logger.debug(f"Using summary template: {summary_template_file}")

    errors, warnings = renderer.validate_template_variables(
        summary_template_file, template_data, set()
    )

    if warnings:
        print(f"{Fore.YELLOW}Missing summary template variables (will be empty):{Style.RESET_ALL}")
        for warn in warnings:
            print(f"  {warn}")

    summary_filename = generate_output_filename(ojs_files, "summary")
    summary_path = os.path.join(base_dir, summary_filename)

    if renderer.render(summary_template_file, template_data, summary_path):
        print_success(f"Ceremony summary: {summary_filename}")
        output_files.append(summary_path)
    else:
        print_error_msg("Failed to render ceremony summary")
        all_success = False

    if all_success:
        print(f"\n{Fore.GREEN}{'═' * 70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}SUCCESS!{Style.RESET_ALL}".center(78))
        print(f"{Fore.GREEN}{'═' * 70}{Style.RESET_ALL}\n")
        print(f"{Fore.GREEN}Generated {len(output_files)} file(s):{Style.RESET_ALL}")
        for output_path in output_files:
            print(f"  {output_path}")
        print()

        has_warnings = (
            (validator.warnings and len(validator.warnings) > 0)
            or (collector.warnings and len(collector.warnings) > 0)
            or (warnings and len(warnings) > 0)
        )

        if has_warnings:
            print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠ WARNINGS DETECTED{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'─' * 70}{Style.RESET_ALL}")
            print(
                f"{Fore.YELLOW}Files generated but there are warnings you should review.{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}Scroll up to review the warnings and carefully review the outputs.{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}Make changes to the OJS if needed and re-run the script generator.{Style.RESET_ALL}\n"
            )
            input(f"{Fore.YELLOW}Press ENTER to exit...{Style.RESET_ALL}")
        else:
            input("Press ENTER to exit...")
    else:
        print_error(logger, "Failed to render one or more ceremony outputs")


if __name__ == "__main__":
    main()
