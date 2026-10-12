import unittest
from pathlib import Path
from modules.ceremony_renderer import CeremonyRenderer, ceremony_context

ROOT = Path(__file__).resolve().parents[1]

class CeremonyTemplateTests(unittest.TestCase):
    def render(self, suffix, info, advancing=''):
        renderer = CeremonyRenderer(str(ROOT))
        name = f'script_template-{suffix}.html.jinja'
        data = dict.fromkeys(renderer.extract_template_variables(name), '')
        data.update(ceremony_context(info))
        data.update(ja_count=0, judges_missing_count=0, ADV=advancing, ADV_D1=advancing, ADV_D2='',
                    tournament_name='Test Tournament')
        data.pop('bg_color_0', None)
        data.pop('bg_color_1', None)
        return renderer.render_text(name, data)

    def test_season_and_optional_announcements(self):
        for suffix in ['with-divisions', 'without-divisions']:
            with self.subTest(suffix=suffix):
                html = self.render(suffix, {'ceremony': {'program_season_name': 'Bioglow'}})
                self.assertIn('Bioglow', html)
                for stale in ['UNEARTHED', 'FIRST AGE', 'archeology', 'January 10',
                              'Foobar', '8th grade', '<h2>Advancing Teams</h2>',
                              '<h2>Breakthrough Award</h2>']:
                    self.assertNotIn(stale, html)
                html = self.render(suffix, {'ceremony': {
                    'program_season_name': 'Future & New',
                    'sponsor_acknowledgement': 'Thanks A & B',
                    'coach_nomination_announcement': 'Nominate here',
                    'advancement_announcement': 'Finals on March 5 at Example Hall',
                    'rubric_instructions': 'by email',
                    'program_website': 'example.org',
                }}, '<p>Team 123</p>')
                for expected in ['Future &amp; New', 'Thanks A &amp; B',
                                 'Nominate here', 'Finals on March 5 at Example Hall',
                                 'by email', 'example.org', '<p>Team 123</p>']:
                    self.assertIn(expected, html)

    def test_volunteer_and_coach_script(self):
        for suffix in ['with-divisions', 'without-divisions']:
            with self.subTest(suffix=suffix):
                html = self.render(suffix, {'ceremony': {
                    'program_season_name': 'Bioglow',
                    'sponsor_acknowledgement': 'Virginia and DC sponsor: JMU & friends',
                    'coach_nomination_announcement': 'Apply at va-dcfll.org',
                }})
                self.assertEqual(html.count('<h2>Volunteers</h2>'), 1)
                self.assertEqual(html.count('<h2>Coach Recognition</h2>'), 1)
                self.assertLess(html.index('<h2>Volunteers</h2>'),
                                html.index('<h2>Coach Recognition</h2>'))
                self.assertIn('Virginia and DC sponsor: JMU &amp; friends', html)
                self.assertIn('keep things running like a well-programmed robot', html)
                self.assertIn('Tournament Director awards the Volunteer Award', html)
                self.assertIn('Apply at va-dcfll.org', html)
                self.assertNotIn('go-to', html)
                self.assertNotIn('Gracious Professionalism?', html)

    def test_unawarded_judges_place_is_visible(self):
        for suffix in ['with-divisions', 'without-divisions']:
            with self.subTest(suffix=suffix):
                renderer = CeremonyRenderer(str(ROOT))
                name = f'script_template-{suffix}.html.jinja'
                data = dict.fromkeys(renderer.extract_template_variables(name), '')
                data.update(ceremony_context({'ceremony': {}}))
                data.update(ja_count=0, judges_missing_count=1,
                            J_AWD_Judges='<p>Judges Award: NONE</p>',
                            ADV='', ADV_D1='', ADV_D2='', tournament_name='Test')
                data.pop('bg_color_0', None)
                data.pop('bg_color_1', None)
                html = renderer.render_text(name, data)
                self.assertIn('Judges Award: NONE', html)

    def test_summary_optional_sections(self):
        renderer = CeremonyRenderer(str(ROOT))
        for suffix in ['with-divisions', 'without-divisions']:
            name = f'summary_template-{suffix}.html.jinja'
            data = dict.fromkeys(renderer.extract_template_variables(name), '')
            html = renderer.render_text(name, data)
            self.assertNotIn('<h2>Advancing Teams</h2>', html)
            self.assertNotIn("<h2>Judge's Award</h2>", html)
            self.assertNotIn('Foobar Award', html)
            data.update(ADV='<p>Team 123</p>', ADV_D1='<p>Team 123</p>',
                        J_AWD_Judges='<p>Team 456</p>')
            html = renderer.render_text(name, data)
            self.assertIn('<p>Team 123</p>', html)
            self.assertIn('<p>Team 456</p>', html)

    def test_division_advancement_without_combined_tag(self):
        renderer = CeremonyRenderer(str(ROOT))
        name = 'script_template-with-divisions.html.jinja'
        data = dict.fromkeys(renderer.extract_template_variables(name), '')
        data.update(ceremony_context({}))
        data.update(ja_count=0, judges_missing_count=0, ADV='', ADV_D1='',
                    ADV_D2='<p>Team 123</p>', tournament_name='Test')
        data.pop('bg_color_0', None)
        data.pop('bg_color_1', None)
        html = renderer.render_text(name, data)
        self.assertIn('<h2>Advancing Teams</h2>', html)
        self.assertIn('<p>Team 123</p>', html)

    def test_legacy_config(self):
        self.assertIn('current season', self.render('without-divisions', {}))
        self.assertIn('Legacy', self.render('without-divisions', {'season_name': 'Legacy'}))

if __name__ == '__main__':
    unittest.main()
