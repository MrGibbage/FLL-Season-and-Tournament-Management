"""Validation logic for OJS spreadsheets in closing ceremony script generation."""

import logging
import pandas as pd
from openpyxl.workbook import Workbook
from typing import List, Tuple

from .constants import (
    SHEET_ROBOT_GAME,
    SHEET_INNOVATION,
    SHEET_ROBOT_DESIGN,
    SHEET_CORE_VALUES,
    SHEET_RESULTS,
    TABLE_ROBOT_GAME,
    TABLE_INNOVATION,
    TABLE_ROBOT_DESIGN,
    TABLE_CORE_VALUES,
    TABLE_TOURNAMENT_DATA,
    COL_TEAM_NUMBER,
)
from .ceremony_workbooks import CeremonyWorkbooks

logger = logging.getLogger("ceremony_generator")


class ValidationError:
    """Represents a validation error with context."""

    def __init__(self, severity: str, sheet: str, message: str):
        self.severity = severity  # "ERROR" or "WARNING"
        self.sheet = sheet
        self.message = message

    def __str__(self):
        return f"[{self.severity}] {self.sheet}: {self.message}"


class OJSValidator:
    """Validates OJS workbook data for ceremony script generation."""

    def __init__(self, workbooks=None, robot_game_max_score=530):
        self.workbooks = workbooks if workbooks is not None else CeremonyWorkbooks()
        self.robot_game_max_score = robot_game_max_score
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def add_error(self, sheet: str, message: str):
        """Add a validation error."""
        sheet = f"{self.context}: {sheet}" if getattr(self, "context", "") else sheet
        error = ValidationError("ERROR", sheet, message)
        self.errors.append(error)
        logger.error(str(error))

    def add_warning(self, sheet: str, message: str):
        """Add a validation warning."""
        warning = ValidationError("WARNING", sheet, message)
        self.warnings.append(warning)
        logger.warning(str(warning))

    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def _coerce_numeric_column(self, series: pd.Series, sheet: str, col: str) -> pd.Series:
        """Coerce a column to numeric, logging non-numeric entries as errors.

        Returns the coerced series (with non-numeric values as NaN).
        """

        coerced = pd.to_numeric(series, errors="coerce")
        invalid_mask = series.notna() & (coerced.isna() | series.map(lambda v: isinstance(v, bool)))
        invalid_count = invalid_mask.sum()
        if invalid_count > 0:
            self.add_error(sheet, f"{col} has {invalid_count} invalid non-numeric value(s)")
        return coerced

    def validate_robot_game_scores(self, ojs_path: str, division: str = "") -> bool:
        """Validate Robot Game scores are within valid range and no blanks.

        Args:
            ojs_path: Path to OJS workbook
            division: Division label for error messages

        Returns:
            True if validation passed, False otherwise
        """
        logger.info(f"Validating Robot Game scores{' for ' + division if division else ''}")

        try:
            df = self.workbooks.table(ojs_path, SHEET_ROBOT_GAME, TABLE_ROBOT_GAME)
        except Exception as e:
            self.add_error(SHEET_ROBOT_GAME, f"Could not read table: {e}")
            return False

        score_columns = ["Robot Game 1 Score", "Robot Game 2 Score", "Robot Game 3 Score"]

        for col in score_columns:
            if col not in df.columns:
                self.add_error(SHEET_ROBOT_GAME, f"Missing column: {col}")
                continue

            # Check for blanks
            blank_count = df[col].isna().sum()
            if blank_count > 0:
                self.add_error(SHEET_ROBOT_GAME, f"{col} has {blank_count} blank cell(s)")

            # Check range (0-445)
            numeric_scores = self._coerce_numeric_column(df[col], SHEET_ROBOT_GAME, col)
            valid_scores = numeric_scores.dropna()
            out_of_range = valid_scores[(valid_scores < 0) | (valid_scores > self.robot_game_max_score) | (valid_scores % 1 != 0)]
            if len(out_of_range) > 0:
                self.add_error(
                    SHEET_ROBOT_GAME,
                    f"{col} has {len(out_of_range)} score(s) outside valid integer range (0-{self.robot_game_max_score})",
                )

        return not self.has_errors()

    def validate_rubric_scores(
        self,
        ojs_path: str,
        sheet_name: str,
        table_name: str,
        columns: List[str],
        division: str = "",
    ) -> bool:
        """Validate rubric scores are 0-4 and no blanks.

        Args:
            ojs_path: Path to OJS workbook
            sheet_name: Name of worksheet
            table_name: Name of table
            columns: List of column names to validate
            division: Division label for error messages

        Returns:
            True if validation passed, False otherwise
        """
        logger.info(f"Validating {sheet_name} scores{' for ' + division if division else ''}")

        try:
            df = self.workbooks.table(ojs_path, sheet_name, table_name)
        except Exception as e:
            self.add_error(sheet_name, f"Could not read table: {e}")
            return False

        for col in columns:
            if col not in df.columns:
                self.add_error(sheet_name, f"Missing column: {col}")
                continue

            # Check for blanks
            blank_count = df[col].isna().sum()
            if blank_count > 0:
                self.add_error(sheet_name, f"{col} has {blank_count} blank cell(s)")

            # Check range (0-4)
            numeric_scores = self._coerce_numeric_column(df[col], sheet_name, col)
            valid_scores = numeric_scores.dropna()
            out_of_range = valid_scores[(valid_scores < 0) | (valid_scores > 4) | (valid_scores % 1 != 0)]
            if len(out_of_range) > 0:
                self.add_error(
                    sheet_name, f"{col} has {len(out_of_range)} score(s) outside valid range (0-4)"
                )

        return not self.has_errors()

    def validate_core_values_scores(self, ojs_path: str, division: str = "") -> bool:
        """Validate Core Values scores are in [0, 2, 3, 4] and no blanks.

        Args:
            ojs_path: Path to OJS workbook
            division: Division label for error messages

        Returns:
            True if validation passed, False otherwise
        """
        logger.info(f"Validating Core Values scores{' for ' + division if division else ''}")

        try:
            df = self.workbooks.table(ojs_path, SHEET_CORE_VALUES, TABLE_CORE_VALUES)
        except Exception as e:
            self.add_error(SHEET_CORE_VALUES, f"Could not read table: {e}")
            return False

        cv_columns = [
            "Gracious Professionalism 1",
            "Gracious Professionalism 2",
            "Gracious Professionalism 3",
        ]

        valid_values = {0, 2, 3, 4}

        for col in cv_columns:
            if col not in df.columns:
                self.add_error(SHEET_CORE_VALUES, f"Missing column: {col}")
                continue

            # Check for blanks
            blank_count = df[col].isna().sum()
            if blank_count > 0:
                self.add_error(SHEET_CORE_VALUES, f"{col} has {blank_count} blank cell(s)")

            # Check valid values
            numeric_scores = self._coerce_numeric_column(df[col], SHEET_CORE_VALUES, col)
            scores = numeric_scores.dropna()
            invalid = scores[~scores.isin(valid_values)]
            if len(invalid) > 0:
                self.add_error(
                    SHEET_CORE_VALUES,
                    f"{col} has {len(invalid)} invalid score(s). Must be one of: {sorted(valid_values)}",
                )

        return not self.has_errors()

    def validate_award_duplicates(self, ojs_path: str, division: str = "") -> bool:
        """Validate that awards are not assigned to more than one team.

        Args:
            ojs_path: Path to OJS workbook
            division: Division label for error messages

        Returns:
            True if validation passed, False otherwise
        """
        logger.info(
            f"Validating award uniqueness{' for ' + division if division else ''} on Tournament and Program Info"
        )

        try:
            df = self.workbooks.table(ojs_path, SHEET_RESULTS, TABLE_TOURNAMENT_DATA)
        except Exception as e:
            self.add_error(SHEET_RESULTS, f"Could not read table: {e}")
            return False

        if "Award" not in df.columns:
            self.add_error(SHEET_RESULTS, "Missing column: Award")
            return False

        awards = df["Award"].dropna().astype(str).str.strip()
        awards = awards[awards != ""]
        duplicates = awards[awards.duplicated(keep=False)]
        if not duplicates.empty:
            for award_value in sorted(set(duplicates)):
                dup_count = (awards == award_value).sum()
                self.add_error(
                    SHEET_RESULTS,
                    f"Award '{award_value}' is assigned to multiple teams (count={dup_count})",
                )

        return not self.has_errors()

    def validate_tournament(self, config, base_dir):
        """Check identities, saved calculations, allocations, and selections."""
        import os
        import math
        self.context = ''
        info = config['INFO']
        results = []
        all_ids = set()
        for entry in info['ojs_files']:
            path = os.path.join(base_dir, entry['filename'])
            context = entry['filename']
            try:
                roster = self.workbooks.table(path, 'Team and Program Information', 'OfficialTeamList')
                ids = pd.to_numeric(roster['Team #'], errors='coerce')
                if roster.empty or ids.isna().any() or (ids <= 0).any() or (ids % 1 != 0).any() or ids.duplicated().any():
                    raise ValueError('Roster must have unique positive integer team numbers')
                if roster['Team Name'].isna().any():
                    raise ValueError('Missing team names')
                if set(ids) & all_ids:
                    raise ValueError('Team appears in more than one division')
                all_ids.update(ids)
                tables = {}
                for sheet, table in [(SHEET_RESULTS, TABLE_TOURNAMENT_DATA),
                                     (SHEET_INNOVATION, TABLE_INNOVATION),
                                     (SHEET_ROBOT_DESIGN, TABLE_ROBOT_DESIGN),
                                     (SHEET_CORE_VALUES, TABLE_CORE_VALUES),
                                     (SHEET_ROBOT_GAME, TABLE_ROBOT_GAME)]:
                    df = self.workbooks.table(path, sheet, table)
                    if df['Team #'].duplicated().any() or set(df['Team #']) != set(ids):
                        raise ValueError(f'{sheet}: team numbers do not match the roster')
                    tables[sheet] = df.set_index('Team #').loc[list(ids)]
                rr = tables[SHEET_RESULTS]
                cv = tables[SHEET_CORE_VALUES]
                ip = tables[SHEET_INNOVATION]
                rd = tables[SHEET_ROBOT_DESIGN]
                rg = tables[SHEET_ROBOT_GAME]
                ip_scores = ip.iloc[:, 2:12].apply(pd.to_numeric, errors='raise').sum(axis=1)
                rd_scores = rd.iloc[:, 2:12].apply(pd.to_numeric, errors='raise').sum(axis=1)
                gp = cv[['Gracious Professionalism 1', 'Gracious Professionalism 2', 'Gracious Professionalism 3']].sum(axis=1)
                cv_scores = ip[[c for c in ip if '(CV)' in c]].sum(axis=1) + rd[[c for c in rd if '(CV)' in c]].sum(axis=1) + gp
                robot = rg[['Robot Game 1 Score', 'Robot Game 2 Score', 'Robot Game 3 Score']].apply(
                    lambda row: sum(x * scale for x, scale in zip(sorted(row, reverse=True), [1, .0001, .0000001])), axis=1)
                expected = [('Innovation Project', ip, ip_scores), ('Robot Design', rd, rd_scores), ('Core Values', cv, cv_scores)]
                checks = [(cv, 'Gracious Professionalism Total', gp), (cv, 'Gracious Professionalism Score', gp),
                          (rr, 'Max Robot Game Score', robot), (rr, 'Robot Game Rank', robot.rank(method='min', ascending=False))]
                champ = robot.rank(method='min', ascending=False)
                for name, df, scores in expected:
                    ranks = scores.rank(method='min', ascending=False)
                    checks.extend([(df, name+' Score', scores), (df, name+' Rank', ranks), (rr, name+' Rank', ranks)])
                    champ = champ + ranks
                checks.extend([(rr, "Champion's Score", champ), (rr, "Champion's Rank", champ.rank(method='min'))])
                for df, col, values in checks:
                    actual = pd.to_numeric(df[col], errors='coerce')
                    if any(pd.isna(a) or not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-8) for a,b in zip(actual,values)):
                        self.add_error(context, f'{col}: saved calculation is missing or incorrect. Recalculate and save in Excel; check workbook formulas.')
                code = entry.get('division', '')
                key = 'advancing_count_' + code.lower() if info['using_divisions'] else 'advancing_count'
                allocated = info.get(key)
                selections = rr['Advance?'].fillna('')
                if not selections.isin(['', 'Yes', 'No', 'Alt']).all():
                    self.add_error(context, 'Advance? must be Yes, No, Alt, or blank')
                if allocated is None:
                    self.add_error(context, f'Missing allocation INFO.{key}; regenerate tournament configuration')
                elif isinstance(allocated, bool) or not isinstance(allocated, int) or allocated < 0 or allocated > len(rr):
                    self.add_error(context, f'Invalid advancement allocation: {allocated}')
                elif (selections == 'Yes').sum() != allocated:
                    self.add_error(context, f'Advancing teams: {(selections == "Yes").sum()} selected, {allocated} allocated')
                if (selections == 'Alt').sum() > 1:
                    self.add_error(context, 'More than one alternate selected')
                elif allocated and not (selections == 'Alt').any():
                    self.add_warning(context, 'No alternate advancing team selected')
                results.append((code, rr))
            except Exception as exc:
                self.add_error(context, str(exc))
        known = {code: set() for code, _ in results}
        for award in config['AWARDS']:
            if award['ID'] == 'P_AWD_RG':
                if info['using_divisions'] and not award['DivAwd'] and award.get('TournCount', 0):
                    self.add_error('Configuration', 'Robot Game awards must be allocated per division in a division tournament')
                    continue
                for code, rr in results:
                    count = int(award.get(code+'_count', 0) if info['using_divisions'] and award['DivAwd'] else award.get('TournCount', 0))
                    ranks = pd.to_numeric(rr['Robot Game Rank'], errors='coerce')
                    if count > len(rr) or len(ranks[ranks.between(1,count)]) != count or ranks[ranks.between(1,count)].duplicated().any():
                        self.add_error(code or 'Tournament', 'Robot Game awards have missing places or tied ranks; resolve before generating the ceremony')
                continue
            labels = award.get('Labels', [])
            groups = [(code, [rr], int(award.get(code+'_count', 0))) for code,rr in results] if info['using_divisions'] and award['DivAwd'] else [('Tournament', [rr for _,rr in results], int(award.get('TournCount',0)))]
            for code, frames, count in groups:
                if count < 0 or len(labels) < count:
                    self.add_error(code, f'{award["Name"]}: invalid allocation or too few labels')
                    continue
                selected = [v for df in frames for v in df['Award'].dropna()]
                for label in labels[:count]:
                    for division, frame in results:
                        if any(frame is df for df in frames):
                            known[division].add(label)
                    if selected.count(label) != 1:
                        self.add_error(code, f'{label}: expected one winner, found {selected.count(label)}')
        for code, rr in results:
            for label in set(rr['Award'].dropna()) - known[code]:
                self.add_error(code or 'Tournament', f'Unknown or unallocated award: {label}')

    def validate_all_sheets(self, ojs_path: str, division: str = "") -> bool:
        """Run all validations on an OJS workbook.

        Args:
            ojs_path: Path to OJS workbook
            division: Division label for error messages

        Returns:
            True if all validations passed, False otherwise
        """
        self.context = division
        logger.info(f"Starting complete validation{' for ' + division if division else ''}")

        # Robot Game
        self.validate_robot_game_scores(ojs_path, division)

        # Innovation Project
        ip_columns = [
            "Identify - Define",
            "Identify - Research (CV)",
            "Design - Plan",
            "Design - Teamwork (CV)",
            "Create - Innovation (CV)",
            "Create - Model",
            "Iterate - Sharing",
            "Iterate - Improvement",
            "Communicate - Impact (CV)",
            "Communicate - Fun (CV)",
        ]
        self.validate_rubric_scores(
            ojs_path, SHEET_INNOVATION, TABLE_INNOVATION, ip_columns, division
        )

        # Robot Design
        rd_columns = [
            "Identify - Strategy",
            "Identify - Research (CV)",
            "Design - Ideas (CV)",
            "Design - Building/Coding",
            "Create - Attachments",
            "Create - Code/ Sensors",
            "Iterate - Testing",
            "Iterate - Improvements (CV)",
            "Communicate - Impact (CV)",
            "Communicate - Fun (CV)",
        ]
        self.validate_rubric_scores(
            ojs_path, SHEET_ROBOT_DESIGN, TABLE_ROBOT_DESIGN, rd_columns, division
        )

        # Core Values
        self.validate_core_values_scores(ojs_path, division)

        # Awards uniqueness (Tournament and Program Info)
        self.validate_award_duplicates(ojs_path, division)

        return not self.has_errors()
