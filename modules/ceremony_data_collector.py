"""Collects data from OJS files for ceremony script generation."""

import logging
from typing import List, Tuple, Dict
from html import escape
from .ceremony_workbooks import CeremonyWorkbooks
from dataclasses import dataclass

from .constants import (
    SHEET_RESULTS, TABLE_TOURNAMENT_DATA,
    SHEET_TEAM_INFO, TABLE_TEAM_LIST,
    COL_TEAM_NUMBER, COL_TEAM_NAME
)

logger = logging.getLogger("ceremony_generator")


@dataclass
class AwardWinner:
    """Represents an award winner."""
    team_number: int
    team_name: str
    label: str = ""  # Optional label like "1st Place", "Winner", etc.
    score: int = None  # For robot game awards


class HighlightTracker:
    """Tracks alternating highlight classes for dual emcee mode."""
    
    def __init__(self, enabled: bool = True):
        """Initialize highlight tracker.
        
        Args:
            enabled: If True, wrap text in highlight spans. If False, return plain text.
        """
        self.enabled = enabled
        self.current = 0  # Start with highlight0
    
    def wrap(self, text: str) -> str:
        """Wrap text in highlight span and toggle state.
        
        Args:
            text: Text to wrap
            
        Returns:
            Text wrapped in <span class="highlightN"> if enabled, otherwise plain text
        """
        if not self.enabled:
            return text
        
        result = f'<span class="highlight{self.current}">{text}</span>'
        self.current = 1 - self.current  # Toggle 0<->1
        return result
    
    def wrap_paragraph(self, content: str) -> str:
        """Wrap content in <p> tag with highlight span.
        
        Args:
            content: Content to wrap
            
        Returns:
            Content wrapped in <p> and <span> tags
        """
        return f'<p>{self.wrap(content)}</p>'


class CeremonyDataCollector:
    """Collects award and team data from OJS files for ceremony script."""
    
    def __init__(self, config: dict, dual_emcee: bool = False, workbooks=None):
        """Initialize data collector.
        
        Args:
            config: Tournament configuration dictionary
            dual_emcee: Whether to enable dual emcee highlighting
        """
        self.workbooks = workbooks if workbooks is not None else CeremonyWorkbooks()
        self.config = config
        self.warnings = []
        
        # Initialize highlight tracker
        self.highlight_tracker = HighlightTracker(enabled=dual_emcee)
        
        logger.debug(f"Highlight tracker initialized (enabled={dual_emcee})")
    
    def collect_team_list(self, ojs_path, division=""):
        df = self.workbooks.table(ojs_path, SHEET_TEAM_INFO, TABLE_TEAM_LIST)
        return [(int(row[COL_TEAM_NUMBER]), str(row[COL_TEAM_NAME]))
                for _, row in df.iterrows()]

    def collect_advancing_teams(self, ojs_path, division=""):
        df = self.workbooks.table(ojs_path, SHEET_RESULTS, TABLE_TOURNAMENT_DATA)
        return [(int(row[COL_TEAM_NUMBER]), str(row[COL_TEAM_NAME]))
                for _, row in df[df['Advance?'] == 'Yes'].iterrows()]

    def collect_robot_game_awards(self, ojs_path, count, division=""):
        df = self.workbooks.table(ojs_path, SHEET_RESULTS, TABLE_TOURNAMENT_DATA)
        selected = df[df['Robot Game Rank'].between(1, count)].sort_values('Robot Game Rank')
        winners = []
        for _, row in selected.iterrows():
            rank = int(row['Robot Game Rank'])
            label = {1: '1st Place', 2: '2nd Place', 3: '3rd Place'}.get(rank, f'{rank}th Place')
            winners.append(AwardWinner(int(row[COL_TEAM_NUMBER]), str(row[COL_TEAM_NAME]),
                                       label, int(row['Max Robot Game Score'])))
        return winners

    def collect_judged_awards(self, ojs_path, award, labels, division, ojs_filename):
        df = self.workbooks.table(ojs_path, SHEET_RESULTS, TABLE_TOURNAMENT_DATA)
        winners = []
        for label in labels:
            selected = df[df['Award'] == label]
            if len(selected) > 1:
                raise ValueError(f"{ojs_filename}: duplicate award {label}")
            for _, row in selected.iterrows():
                winners.append(AwardWinner(int(row[COL_TEAM_NUMBER]), str(row[COL_TEAM_NAME]), label))
        return winners

    def format_team_list_as_html(self, teams: List[Tuple[int, str]]) -> str:
        """Format team list as HTML paragraphs with highlighting.
        
        Args:
            teams: List of (team_number, team_name) tuples
            
        Returns:
            HTML string with team list
        """
        if not teams:
            return ""
        
        html_lines = []
        for team_num, team_name in teams:
            line = f"Team {team_num}, {escape(team_name)}"
            html_line = self.highlight_tracker.wrap_paragraph(line)
            html_lines.append(html_line)
        
        return "\n".join(html_lines)
    
    def format_winners_as_html(self, winners: List[AwardWinner], include_score: bool = False) -> str:
        """Format award winners as HTML paragraphs with highlighting.
        
        Args:
            winners: List of AwardWinner objects
            include_score: If True, include robot game score in output
            
        Returns:
            HTML string with formatted winners
        """
        if not winners:
            return ""

        html_lines = []
        # Present awards in reverse ranking order (e.g., 3rd → 2nd → 1st)
        for winner in reversed(winners):
            parts = []

            # Add label if present
            if winner.label:
                parts.append(f"{escape(winner.label)}:")

            # Add team info
            parts.append(f"Team {winner.team_number}, {escape(winner.team_name)}")

            # Add score if requested
            if include_score and winner.score is not None:
                parts.append(f"with a score of {winner.score}")

            line = " ".join(parts)
            html_line = self.highlight_tracker.wrap_paragraph(line)
            html_lines.append(html_line)

        return "\n".join(html_lines)
