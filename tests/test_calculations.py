import unittest

from business_performance_agent.tools.calculations import (
    absolute_change,
    additive_contribution,
    closure_check,
    coverage,
    evaluate_formula,
    rank_effects,
    relative_change,
    symmetric_two_factor_decomposition,
)


class CalculationTests(unittest.TestCase):
    def test_zero_denominator(self):
        self.assertIsNone(relative_change(2, 0))
        self.assertIsNone(evaluate_formula("a / b", {"a": 1, "b": 0}.__getitem__))
        self.assertEqual(absolute_change(8, 10), -2)

    def test_symmetric_closure(self):
        for a0, a1, b0, b1 in [
            (10, 9, 100, 98),
            (0, 2, 3, 4),
            (3, 1, 2, 7),
            (-2, 3, 8, 1),
        ]:
            effects = symmetric_two_factor_decomposition(a0, a1, b0, b1)
            self.assertTrue(closure_check(a1 * b1 - a0 * b0, effects)["closed"])

    def test_offsets_ranking_coverage(self):
        values = rank_effects(
            -10, [{"id": "offset", "effect": 5}, {"id": "driver", "effect": -15}]
        )
        self.assertEqual(values[0]["id"], "driver")
        self.assertEqual(values[0]["aligned_share"], 1)
        self.assertEqual(values[1]["role"], "offset")
        self.assertEqual(coverage(values), 1)

    def test_additive_negative_coefficient(self):
        self.assertEqual(additive_contribution(10, 15, -1), -5)

    def test_formula_rejects_execution(self):
        with self.assertRaises(ValueError):
            evaluate_formula("__import__('os')", lambda _: 0)
