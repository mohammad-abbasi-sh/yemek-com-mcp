"""Live tests — hit the real yemek.com. Cautious: a few requests, then stop.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set YEMEK_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import time
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from yemek_com_mcp import http as _http
from yemek_com_mcp import recipes as _R

pytestmark = pytest.mark.live
SKIP = os.environ.get("YEMEK_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="YEMEK_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_search_json_is_real(self):
        # Recipes page in 3s — fetch two pages and combine.
        p1 = _R.parse_search_json(_http.fetch_search_json("mercimek", rows=12))
        p2 = _R.parse_search_json(
            _http.fetch_search_json("mercimek", rows=12, recipes_start=3)
        )
        recipes = p1["recipes"] + p2["recipes"]
        self.assertGreater(p1["total_recipes"], 100)
        self.assertGreaterEqual(len(recipes), 5)
        self.assertTrue(all(r["slug"] and r["url"] for r in recipes))
        print(f"\nLIVE search 'mercimek': {p1['total_recipes']} recipes, "
              f"first = {recipes[0]['title']}")
        time.sleep(1)

    def test_recipe_page_is_real(self):
        r = _R.parse_recipe_page(_http.fetch_recipe_page("mercimek-corbasi"))
        self.assertIn("Mercimek", r["name"])
        self.assertGreaterEqual(len(r["ingredients"]), 5)
        self.assertGreaterEqual(len(r["instructions"]), 3)
        print(f"\nLIVE recipe: {r['name']} — {len(r['ingredients'])} ingredients, "
              f"{len(r['instructions'])} steps, rating {r['rating']}")
        time.sleep(1)

    def test_home_sections_are_real(self):
        home = _http.fetch_home()
        cats = _R.parse_categories(home)
        videos = _R.parse_home_section(home, "Videolu Tarifler")
        popular = _R.parse_home_section(home, "Popüler Yemek Tarifleri")
        self.assertGreaterEqual(len(cats), 10)
        self.assertGreaterEqual(len(videos), 5)
        self.assertGreaterEqual(len(popular), 5)
        print(f"\nLIVE home: {len(cats)} categories, {len(videos)} videos, "
              f"{len(popular)} popular")
        time.sleep(1)

    def test_bugun_is_real(self):
        rows = _R.parse_bugun(_http.fetch_bugun())
        self.assertGreaterEqual(len(rows), 10)
        print(f"\nLIVE bugun: {len(rows)} recipes, first = {rows[0]['title']}")
        time.sleep(1)

    def test_unknown_recipe_404s(self):
        with self.assertRaises(_http.YemekError):
            _http.fetch_recipe_page("boyle-bir-tarif-yok-xyz123")
