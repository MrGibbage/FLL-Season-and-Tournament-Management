import unittest

import pandas as pd

from modules.worksheet_setup import validate_award_labels


class AwardLabelValidationTests(unittest.TestCase):
    def setUp(self):
        self.tournaments = pd.DataFrame([{
            "Short Name": "Manassas_1", "Div": "D1", "J_AWD_Judges": 4, "ADV": 8,
        }])
        self.definitions = pd.DataFrame([{
            "ColumnName": "J_AWD_Judges", "Name": "Judges",
            **{f"Label{i}": f"Judges {i}" for i in range(1, 5)},
        }])

    def test_four_labels_pass_and_advancement_is_excluded(self):
        self.assertEqual(validate_award_labels(self.tournaments, self.definitions), [])

    def test_missing_fourth_label(self):
        errors = validate_award_labels(self.tournaments, self.definitions.drop(columns="Label4"))
        self.assertEqual(errors, [
            "Manassas_1 D1: Judges has 4 awards allocated, but Label4 is missing or blank"
        ])

    def test_blank_and_zero_labels_fail(self):
        for value in (None, float("nan"), "  ", 0, "0"):
            with self.subTest(value=value):
                definitions = self.definitions.copy()
                definitions["Label4"] = value
                self.assertIn("Label4 is missing or blank",
                              validate_award_labels(self.tournaments, definitions)[0])

    def test_duplicate_labels_fail_after_trimming(self):
        self.definitions["Label4"] = " Judges 1 "
        self.assertIn("duplicate allocated label",
                      validate_award_labels(self.tournaments, self.definitions)[0])

    def test_missing_or_duplicate_definition_fails(self):
        for definitions in (self.definitions.iloc[:0], pd.concat([self.definitions] * 2)):
            self.assertIn("exactly one matching AwardDef row",
                          validate_award_labels(self.tournaments, definitions)[0])

    def test_robot_game_labels_are_checked(self):
        tournaments = self.tournaments.rename(columns={"J_AWD_Judges": "P_AWD_RG"})
        definitions = self.definitions.replace({"J_AWD_Judges": "P_AWD_RG"}).drop(columns="Label4")
        self.assertIn("Label4 is missing or blank",
                      validate_award_labels(tournaments, definitions)[0])

    def test_unused_labels_do_not_block(self):
        self.tournaments["J_AWD_Judges"] = 0
        self.assertEqual(validate_award_labels(self.tournaments, self.definitions.iloc[:0]), [])


if __name__ == "__main__":
    unittest.main()
