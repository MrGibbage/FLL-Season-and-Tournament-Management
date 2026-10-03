"""Shared access to the season name in season and tournament configuration."""


def program_season_name(config):
    """Return the required name, with a precise error for invalid configuration."""
    ceremony = config.get("ceremony")
    name = ceremony.get("program_season_name") if isinstance(ceremony, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise ValueError("ceremony.program_season_name must be a non-empty string")
    return name.strip()


def using_divisions(config):
    value = config.get("using_divisions")
    if not isinstance(value, bool):
        raise ValueError("using_divisions must be true or false in the season JSON")
    return value


def tournament_identity(tournament, config):
    """Derive names from JSON, never from cached Excel names or formulas."""
    from .constants import COL_SHORT_NAME, COL_DIVISION, COL_LONG_NAME, COL_OJS_FILENAME
    fields = {
        "short_name": str(tournament[COL_SHORT_NAME]),
        "season_year": str(config["season_yr"]),
        "program_season_name": program_season_name(config),
        "division": str(tournament[COL_DIVISION]) if using_divisions(config) else "",
    }
    name = config.get("tournament_name_format",
                      "{short_name} {season_year} {program_season_name} Tournament").format(**fields)
    filename = config.get("ojs_filename_format",
                          "{season_year}-fll-challenge-{program_season_name}-ojs-{short_name}{division}.xlsm").format(**fields)
    if not filename.lower().endswith(".xlsm") or any(c in filename for c in '<>:"/\\|?*'):
        raise ValueError(f"Invalid generated OJS filename: {filename!r}")
    return {COL_LONG_NAME: name, COL_OJS_FILENAME: filename}
