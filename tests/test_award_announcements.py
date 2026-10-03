import unittest
from modules.ceremony_data_collector import CeremonyDataCollector, AwardWinner

class AwardAnnouncementTests(unittest.TestCase):
    def test_division_and_reverse_place_order(self):
        collector = CeremonyDataCollector({})
        winners = [AwardWinner(1, 'First', '1st Place', 296),
                   AwardWinner(2, 'Second', '2nd Place', 295)]
        html = collector.format_winners_as_html(winners, True, 'Division 2')
        self.assertIn('Division 2 1st Place: Team 1, First with a score of 296', html)
        self.assertLess(html.index('2nd Place'), html.index('1st Place'))

    def test_judges_and_parade_have_no_division(self):
        collector = CeremonyDataCollector({})
        html = collector.format_winners_as_html([AwardWinner(3, 'Third', 'Judges 1')])
        self.assertIn('Judges 1: Team 3, Third', html)
        self.assertNotIn('Division', html)
        self.assertEqual(collector.format_team_list_as_html([(3, 'Third')]),
                         '<p>Team 3, Third</p>')

    def test_division_text_is_escaped(self):
        html = CeremonyDataCollector({}).format_winners_as_html(
            [AwardWinner(1, 'A & B', 'Champions 1st Place')], division='Division <1>')
        self.assertIn('Division &lt;1&gt; Champions 1st Place', html)
        self.assertIn('A &amp; B', html)
