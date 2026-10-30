import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import engine_diff  # noqa: E402
import peec_credits  # noqa: E402
import render_table  # noqa: E402
from solve import ENGINES, fit_plan, load, solve, solve_tool  # noqa: E402


class DataTest(unittest.TestCase):
    def test_engine_ids_are_known(self):
        for tool in load():
            ids = set(tool.get("enterprise", []))
            for plan in tool["plans"]:
                for key in ("included", "pool", "addon"):
                    ids |= set(plan.get(key, []))
            self.assertLessEqual(ids, ENGINES.keys(), tool["id"])

    def test_choose_needs_a_pool(self):
        for tool in load():
            for plan in tool["plans"]:
                if plan.get("choose"):
                    self.assertGreaterEqual(len(plan["pool"]), plan["choose"], tool["id"])


class FitTest(unittest.TestCase):
    pick3 = {"name": "P", "price": 100, "prompts": 50, "choose": 3,
             "pool": ["chatgpt", "gemini", "perplexity", "aio"]}

    def test_pick_within_limit(self):
        r = fit_plan(self.pick3, {"chatgpt", "gemini", "perplexity"}, 50)
        self.assertTrue(r["ok"])
        self.assertEqual(r["cost"], 100)

    def test_pick_over_limit_without_addon_fails(self):
        r = fit_plan(self.pick3, {"chatgpt", "gemini", "perplexity", "aio"}, 10)
        self.assertFalse(r["ok"])

    def test_pick_over_limit_with_unpriced_addon(self):
        plan = dict(self.pick3, addon=self.pick3["pool"], addon_price=None)
        r = fit_plan(plan, {"chatgpt", "gemini", "perplexity", "aio"}, 10)
        self.assertTrue(r["ok"])
        self.assertIsNone(r["cost"])
        self.assertEqual(len(r["addons"]), 1)

    def test_prompt_cap(self):
        self.assertFalse(fit_plan(self.pick3, {"chatgpt"}, 51)["ok"])

    def test_addon_bundle_cap(self):
        plan = {"name": "B", "price": 129, "prompts": None,
                "addon": ["chatgpt", "perplexity", "gemini", "copilot", "aio", "ai_mode"],
                "addon_price": 199, "addon_bundle": 699}
        self.assertEqual(fit_plan(plan, {"chatgpt"}, 1)["cost"], 328)
        self.assertEqual(fit_plan(plan, set(plan["addon"]), 1)["cost"], 828)

    def test_blocked_is_intersection_across_plans(self):
        tool = {"name": "T", "id": "t", "currency": "USD", "enterprise": ["claude"],
                "plans": [{"name": "A", "price": 1, "prompts": 10, "included": ["chatgpt"]},
                          {"name": "B", "price": 2, "prompts": 10, "included": ["chatgpt", "perplexity"]}]}
        r = solve_tool(tool, {"chatgpt", "perplexity", "claude"}, 5)
        self.assertEqual(r["enterprise"], ["claude"])
        self.assertEqual(r["absent"], [])

    def test_peec_cannot_track_claude_self_serve(self):
        peec = next(r for r in solve(load(), {"claude"}, 10) if r["id"] == "peec")
        self.assertFalse(peec["ok"])
        self.assertEqual(peec["enterprise"], ["claude"])


class CreditTest(unittest.TestCase):
    def test_allocation_and_floor(self):
        self.assertEqual(peec_credits.allocation(10, 3), 900)
        self.assertEqual(peec_credits.allocation(5, 3), 900)
        self.assertEqual(peec_credits.allocation(100, 3), 9000)

    def test_pool_choice(self):
        self.assertEqual(peec_credits.smallest_pool(10_000)[0], "Essential")
        self.assertEqual(peec_credits.smallest_pool(10_001)[0], "Growth")
        self.assertIsNone(peec_credits.smallest_pool(65_001))


class DiffTest(unittest.TestCase):
    def test_jaccard(self):
        self.assertEqual(engine_diff.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        self.assertEqual(engine_diff.jaccard(set(), set()), 1.0)

    def test_sample_drops_the_planted_twins(self):
        data = engine_diff.read_checks(ROOT / "examples" / "manual-checks.example.csv")
        chosen, mirrored = engine_diff.pick(data, engine_diff.similarity(data), 0.7)
        self.assertEqual(sorted(chosen), ["chatgpt", "claude", "gemini", "perplexity"])
        self.assertEqual(mirrored, {"aio": "gemini", "copilot": "chatgpt"})


class ReadmeTest(unittest.TestCase):
    def test_readme_matches_data(self):
        current = render_table.README.read_text(encoding="utf-8")
        self.assertEqual(current, render_table.apply(current, render_table.blocks()))


if __name__ == "__main__":
    unittest.main()
