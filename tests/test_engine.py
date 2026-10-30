"""Offline checks of original rule behavior with illustrative garments."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import forward_chaining as engine


class RuleEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((ROOT / 'normalization.json').read_text())
        cls.garments = json.loads((ROOT / 'examples/wardrobe.json').read_text())

    def test_temperature_boundaries(self):
        for temperature, band in [
            (5, 'very_cold'),
            (6, 'cold'),
            (12, 'cold'),
            (13, 'mild'),
            (18, 'mild'),
            (19, 'warm'),
            (26, 'warm'),
            (27, 'hot'),
        ]:
            with self.subTest(temperature=temperature):
                facts = engine.forward_chain({f'temperature:{temperature}'}, self.rules)
                self.assertIn(f'temp_band:{band}', facts)

    def test_winter_excludes_summer_items(self):
        context = dict(temperature=0, season='winter', formality='casual', occasion='travel')
        facts = engine.forward_chain(engine.build_user_facts(context), self.rules)
        summer_items = [
            g for g in self.garments if g['normalized_attributes']['season'] == 'summer'
        ]
        self.assertTrue(summer_items)
        for item in summer_items:
            self.assertFalse(engine.is_garment_safe(item, facts, 'winter'))

    def test_work_excludes_sport_style(self):
        facts = engine.forward_chain({'occasion:work'}, self.rules)
        sport_items = [g for g in self.garments if g['normalized_attributes']['style'] == 'sport']
        for item in sport_items:
            self.assertFalse(engine.is_garment_safe(item, facts, 'spring'))

    def test_fallback_is_used_when_strict_shoes_are_missing(self):
        context = dict(
            temperature=18, season='spring', formality='business_casual', occasion='work'
        )
        facts = engine.forward_chain(engine.build_user_facts(context), self.rules)
        result = engine.recommend_outfit_forward_chaining(context, self.garments, self.rules)
        self.assertIsNotNone(result['shoes'])
        self.assertFalse(engine.is_garment_strict_match(result['shoes'], facts))
        self.assertTrue(engine.is_garment_safe(result['shoes'], facts, 'spring'))

    def test_empty_wardrobe_leaves_slots_open(self):
        result = engine.recommend_outfit_forward_chaining({'temperature': 18}, [], self.rules)
        self.assertEqual(result, {'top': None, 'bottom': None, 'shoes': None, 'extra': []})


if __name__ == '__main__':
    unittest.main()
