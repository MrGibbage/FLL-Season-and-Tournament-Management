"""Generate independent Python validation expectations for browser mutations."""
import contextlib
import io
import logging
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.ceremony_workbooks import CeremonyWorkbooks
from modules.ceremony_validator import OJSValidator
from modules.tournament_assets import discover_embedded_config


def scenarios(directory=None):
    directory = Path(directory) if directory else ROOT / 'tournaments/Dunford'
    cache = CeremonyWorkbooks()
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    cases = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            config = discover_embedded_config(directory, cache)[0]
        paths = [str(directory / e['filename']) for e in config['INFO']['ojs_files']]
        book = cache.workbook(paths[0])
        table_sheets = {name: ws.title for ws in book for name in ws.tables}
        # Cover every editable numeric score field, not just one representative.
        score_tables = [
            ('RobotGameScores', [f'Robot Game {i} Score' for i in range(1, 4)], [None, -1, 531, 2.5, True, 'bad', '', '#VALUE!']),
            ('InnovationProjectResults', ['Identify - Define','Identify - Research (CV)','Design - Plan','Design - Teamwork (CV)','Create - Innovation (CV)','Create - Model','Iterate - Sharing','Iterate - Improvement','Communicate - Impact (CV)','Communicate - Fun (CV)'], [None, -1, 5, 2.5, True, 'bad']),
            ('RobotDesignResults', ['Identify - Strategy','Identify - Research (CV)','Design - Ideas (CV)','Design - Building/Coding','Create - Attachments','Create - Code/ Sensors','Iterate - Testing','Iterate - Improvements (CV)','Communicate - Impact (CV)','Communicate - Fun (CV)'], [None, -1, 5, 2.5, True, 'bad']),
            ('CoreValuesResults', [f'Gracious Professionalism {i}' for i in range(1, 4)], [None, -1, 1, 5, 2.5, True, 'bad']),
        ]
        def run(table, column, value, row=0, index=0):
            path = paths[index]
            df = cache.table(path, table_sheets[table], table)
            # Object dtype allows deliberate type errors without pandas coercion.
            df = df.astype(object)
            df.iloc[row, df.columns.get_loc(column)] = value
            key = (str(Path(path).absolute()), table_sheets[table], table)
            original = cache.tables[key]
            cache.tables[key] = df
            try:
                validator = OJSValidator(cache, config['INFO'].get('robot_game_max_score', 530))
                for p in paths:
                    labels = next((set(a['Labels']) for a in config['AWARDS'] if a['ID']=='J_AWD_Judges'), set())
                    validator.validate_all_sheets(p, judges_labels=labels)
                # Run the complete independent validator, including saved ranks.
                validator.validate_tournament(config, str(directory))
                cases.append({'name': f'{table}.{column} = {value!r}', 'table': table, 'column': column, 'row': row, 'book': index, 'value': value,
                              'blocked': bool(validator.errors), 'missing': bool(validator.missing_awards), 'warning': bool(validator.warnings)})
            finally:
                cache.tables[key] = original
        for table, columns, values in score_tables:
            for col in columns:
                for value in values:
                    run(table, col, value)
        # Each saved derived column has a separate stale-cache regression case.
        for table, columns in [
            ('TournamentData', ['Max Robot Game Score','Robot Game Rank','Core Values Rank','Innovation Project Rank','Robot Design Rank',"Champion's Score","Champion's Rank"]),
            ('InnovationProjectResults', ['Innovation Project Score','Innovation Project Rank']),
            ('RobotDesignResults', ['Robot Design Score','Robot Design Rank']),
            ('CoreValuesResults', ['Core Values Score','Core Values Rank','Gracious Professionalism Total','Gracious Professionalism Score']),
        ]:
            for col in columns:
                for v in [None, 99999]:
                    run(table, col, v)
        for value in ['Maybe', None, 'No', 'Yes', 'Alt', True]:
            run('TournamentData', 'Advance?', value)
        run('TournamentData', 'Award', None)
        run('TournamentData', 'Award', 'Unknown Award')
        run('TournamentData', 'Award', 'Champions 1st Place', row=1)
        run('OfficialTeamList', 'Team #', -1)
        run('OfficialTeamList', 'Team #', None)
        run('OfficialTeamList', 'Team Name', None)
        return cases
    finally:
        cache.close()
        logging.disable(previous)


if __name__ == '__main__':
    import json
    print(json.dumps(scenarios(), indent=2))
