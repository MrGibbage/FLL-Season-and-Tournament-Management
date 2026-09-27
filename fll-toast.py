"""TOAST - Tournament OJS And Script Toolkit

Generate closing ceremony scripts from OJS files for FIRST LEGO League tournaments.

Run notes:
- Run from inside a tournament folder so `tournament_config.json` and OJS files are discovered in the working directory.
- Use --tournament-dir to test from the project directory and --output-dir for isolated outputs/logs.
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


# Application version. Edit manually as needed.
TOAST_VERSION = "1.00.01"

# Suppress openpyxl warnings about conditional formatting
warnings.simplefilter(action="ignore", category=UserWarning)

# Add modules directory to path
sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setup_logger, print_error
from modules.ceremony_validator import OJSValidator
from modules.ceremony_data_collector import CeremonyDataCollector
from modules.ceremony_renderer import CeremonyRenderer
from modules.ceremony_workbooks import CeremonyWorkbooks

# Initialize colorama
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")
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
    return TOAST_VERSION


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

    parser.add_argument(
        "--tournament-dir",
        metavar="PATH",
        help="Read tournament configuration, OJS files, and templates from this folder",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        help="Write HTML and logs to a separate folder (useful for local testing)",
    )
    return parser.parse_args()


def main(workbooks=None):
    if workbooks is None:
        cache = CeremonyWorkbooks()
        try:
            return main(cache)
        except Exception as exc:
            logging.getLogger("ceremony_generator").exception("TOAST stopped: %s", exc)
            print_error_msg(str(exc))
            input("Press ENTER to exit...")
            sys.exit(1)
        finally:
            cache.close()
    """Main execution function."""
    args = parse_arguments()

    version = resolve_version()

    if args.debug:
        log_debug = True
    elif args.verbose:
        log_debug = False  # INFO level
    else:
        log_debug = False  # Default (WARNING level in setup_logger when debug=False)

    # Show version before the splash (matches Maestro behavior)
    print(f"{Fore.CYAN}TOAST version:{Style.RESET_ALL} {version}")

    print_splash()

    if getattr(sys, "frozen", False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    cwd_dir = os.getcwd()
    if args.tournament_dir:
        base_dir = os.path.abspath(args.tournament_dir)
        base_note = "--tournament-dir"
    elif os.path.exists(os.path.join(cwd_dir, "tournament_config.json")):
        base_dir = cwd_dir
        base_note = "working directory"
    else:
        base_dir = script_dir
        base_note = "script directory"

    output_dir = os.path.abspath(args.output_dir) if args.output_dir else base_dir
    if args.output_dir:
        os.makedirs(output_dir, exist_ok=True)

    global logger
    logger = setup_logger(
        "ceremony_generator", debug=log_debug,
        log_dir=output_dir if args.output_dir else script_dir,
    )

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
    if not isinstance(using_divisions, bool):
        raise ValueError("INFO.using_divisions must be true or false")
    if not isinstance(config['AWARDS'], list):
        raise ValueError('AWARDS must be a list')
    award_ids = set()
    for award in config['AWARDS']:
        if award['ID'] in award_ids:
            raise ValueError(f"Duplicate award ID: {award['ID']}")
        award_ids.add(award['ID'])
        if not isinstance(award['DivAwd'], bool):
            raise ValueError(f"{award['Name']}: DivAwd must be true or false")
        fields = [('D1_count', 'ScriptTagD1'), ('D2_count', 'ScriptTagD2')] if using_divisions and award['DivAwd'] else [('TournCount', 'ScriptTagNoDiv')]
        for count_key, tag_key in fields:
            count = award.get(count_key, 0)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"{award['Name']}: {count_key} must be a nonnegative integer")
            if count and not award.get(tag_key):
                raise ValueError(f"{award['Name']}: missing {tag_key}")
            if award['ID'] != 'P_AWD_RG':
                labels = award.get('Labels', [])
                if (not isinstance(labels, list) or len(labels) < count
                        or any(not isinstance(label, str) or not label.strip() for label in labels[:count])
                        or len(set(labels[:count])) != count):
                    raise ValueError(f"{award['Name']}: provide a distinct nonempty label for each allocated award")

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
    info["ojs_files"] = ojs_files
    if using_divisions and (any(e["division"] not in {"D1", "D2"} for e in ojs_files) or len({e["division"] for e in ojs_files}) != len(ojs_files)):
        raise ValueError("Use distinct D1/D2 entries in INFO.ojs_files")
    if not using_divisions and len(ojs_files) != 1:
        raise ValueError("Non-division tournaments must have one OJS file")

    # Derive dual emcee highlighting from Team and Program Information!F2 in any OJS
    dual_emcee = False
    for entry in ojs_files:
        ojs_file = entry["filename"]
        ojs_path = os.path.join(base_dir, ojs_file)
        if os.path.exists(ojs_path):
            try:
                from openpyxl import load_workbook

                wb = workbooks.workbook(ojs_path)
                ws = wb["Team and Program Information"]
                dual_emcee_value = ws["F2"].value


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
    for entry in ojs_files:
        div_label = entry.get("division") or ""
        div_display = f" ({div_label})" if div_label else ""
        print(f"  - {entry['filename']}{div_display}")
    print(f"{Fore.CYAN}Dual emcee:{Style.RESET_ALL} {dual_emcee}")

    input(f"{Fore.CYAN}Press ENTER to continue, or Ctrl+C to abort...{Style.RESET_ALL}")

    print_header("VALIDATING OJS FILES")
    for entry in ojs_files:
        ojs_file = entry["filename"]
        ojs_path = os.path.join(base_dir, ojs_file)
        # Detect Excel lock/temp file indicating the OJS is open (~$filename.xlsm)
        lock_name = f"~${os.path.basename(ojs_file)}"
        lock_path = os.path.join(base_dir, lock_name)

        if os.path.exists(lock_path):
            print_error(logger, f"OJS appears to be open (lock file found): {lock_name}")
            sys.exit(1)

        if os.path.exists(ojs_path):
            print_success(f"Found: {ojs_file}")
        else:
            print_error(logger, f"OJS file not found: {ojs_file}")

    print_header("VALIDATING OJS DATA")
    maximum = info.get("robot_game_max_score", 530)
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
        raise ValueError("INFO.robot_game_max_score must be a positive integer")
    validator = OJSValidator(workbooks, maximum)
    for idx, entry in enumerate(ojs_files):
        ojs_file = entry["filename"]
        division_label = entry.get("division") or f"Division {idx + 1}" if using_divisions else ""
        ojs_path = os.path.join(base_dir, ojs_file)
        print(
            f"\n{Fore.CYAN}Validating {ojs_file} ({division_label or 'No Division'})...{Style.RESET_ALL}"
        )
        validator.validate_all_sheets(ojs_path, division_label)

    if not validator.has_errors():
        validator.validate_tournament(config, base_dir)

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
    collector = CeremonyDataCollector(config, dual_emcee=dual_emcee, workbooks=workbooks)
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
                template_data["team_list_D1"] = template_data["div1_list"]
            elif entry["code"] == "D2":
                template_data["div2_list"] = collector.format_team_list_as_html(teams)
                template_data["team_list_D2"] = template_data["div2_list"]
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
                            entry["path"], award, labels[:tourn_count], "", entry["filename"]
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
        "team_list_D1",
        "team_list_D2",
        "div1_list",
        "div2_list",
        "team_list",
        "ADV_D1",
        "ADV_D2",
        "ADV",
        "ip_this_these",
        "rd_this_these",
        "ja_go_goes",
    ]
    for var in expected_vars:
        if var not in template_data:
            template_data[var] = ""

    # Zero allocations and absent divisions intentionally render no winners.
    for award in config['AWARDS']:
        for key in ['ScriptTagD1', 'ScriptTagD2', 'ScriptTagNoDiv']:
            if award.get(key):
                template_data.setdefault(award[key], '')

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
    outputs = []
    # Validate and render both templates before writing either output.
    for key, default, suffix in [
        ('script_template', 'script_template.html.jinja', 'closing-ceremony'),
        ('summary_template', 'summary_template.html.jinja', 'summary'),
    ]:
        filename = info.get(key, default)
        required = renderer.extract_template_variables(filename)
        errors, missing = renderer.validate_template_variables(filename, template_data, required)
        if errors or missing:
            raise ValueError(f'{filename}: missing template variables: {", ".join(errors + missing)}')
        content = renderer.render_text(filename, template_data)
        outputs.append((os.path.join(output_dir, generate_output_filename(ojs_files, suffix)), content))
    for path, content in outputs:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f'Generated: {path}')
    if validator.warnings or collector.warnings:
        print_warning('Review the warnings above before using the ceremony files.')
    input('Press ENTER to exit...')


if __name__ == "__main__":
    main()
