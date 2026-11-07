"""Offline tests — parse real captured Yemek.com fixtures, no network."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from yemek_com_mcp import recipes as R

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


class TestSearchJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = R.parse_search_json((FIX / "search.json").read_text(encoding="utf-8"))

    def test_totals(self):
        self.assertEqual(self.data["total_recipes"], 533)
        self.assertEqual(self.data["total_posts"], 822)

    def test_first_recipe(self):
        r = self.data["recipes"][0]
        self.assertEqual(r["slug"], "4-kisilik-mercimek-corbasi")
        self.assertIn("Mercimek", r["title"])
        self.assertTrue(r["url"].startswith("https://yemek.com/tarif/"))
        self.assertEqual(r["prep_time"], "15dk")

    def test_video_flag_and_rating(self):
        rs = {r["slug"]: r for r in self.data["recipes"]}
        self.assertTrue(rs["citir-mercimekli-marine-pancar-salatasi"]["has_video"])
        self.assertFalse(rs["4-kisilik-mercimek-corbasi"]["has_video"])
        self.assertEqual(rs["sutlu-mercimek-corbasi"]["rating"], 5)

    def test_posts_present(self):
        self.assertGreaterEqual(len(self.data["posts"]), 1)
        self.assertTrue(self.data["posts"][0]["url"])


class TestRecipePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = R.parse_recipe_page((FIX / "recipe.html").read_text(encoding="utf-8"))

    def test_meta(self):
        self.assertEqual(self.r["name"], "Mercimek Çorbası (Lokanta Usulü)")
        self.assertEqual(self.r["category"], "Pratik Tarifler")
        self.assertEqual(self.r["cuisine"], "Türk")
        self.assertEqual(self.r["servings"], "6 kişilik")
        self.assertEqual(self.r["total_time"], "PT60M")
        self.assertEqual(self.r["prep_time"], "PT10M")
        self.assertEqual(self.r["cook_time"], "PT50M")

    def test_ingredients_and_steps(self):
        self.assertEqual(len(self.r["ingredients"]), 12)
        self.assertIn("1,5 su bardağı kırmızı ya da sarı mercimek", self.r["ingredients"])
        self.assertEqual(len(self.r["instructions"]), 8)
        self.assertTrue(self.r["instructions"][0].startswith("Mercimek çorbası için"))

    def test_rating_and_nutrition(self):
        self.assertEqual(self.r["rating"], 4.3)
        self.assertEqual(self.r["rating_count"], 230)
        self.assertEqual(self.r["calories"], "290 kalori")

    def test_no_recipe_ld_raises(self):
        with self.assertRaises(ValueError):
            R.parse_recipe_page("<html><body>no ld here</body></html>")


class TestCardsAndSections(unittest.TestCase):
    def test_search_cards(self):
        rows = R.parse_recipe_cards((FIX / "search.html").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["slug"], "4-kisilik-mercimek-corbasi")

    def test_videos(self):
        rows = R.parse_home_section(
            (FIX / "home.html").read_text(encoding="utf-8"), "Videolu Tarifler"
        )
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["slug"], "acili-mayonez-soslu-ton-bonfile-salatasi")

    def test_popular(self):
        rows = R.parse_home_section(
            (FIX / "home.html").read_text(encoding="utf-8"), "Popüler Yemek Tarifleri"
        )
        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["slug"], "chester")

    def test_categories(self):
        cats = R.parse_categories((FIX / "home.html").read_text(encoding="utf-8"))
        self.assertEqual(len(cats), 12)
        self.assertEqual(cats[0]["name"], "Atıştırmalık")
        self.assertEqual(cats[0]["recipe_count"], 2662)
        self.assertEqual(cats[1]["slug"], "balik")

    def test_bugun(self):
        rows = R.parse_bugun((FIX / "bugun.html").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0]["slug"], "kremasiz-brokoli-corbasi")

    def test_missing_section_is_empty(self):
        self.assertEqual(
            R.parse_home_section((FIX / "home.html").read_text(encoding="utf-8"), "Yok"),
            [],
        )

    def test_slugify(self):
        self.assertEqual(R.slugify("Mercimek Çorbası"), "mercimek-corbasi")
        self.assertEqual(R.slugify("Sütlü İrmik Tatlısı"), "sutlu-irmik-tatlisi")
        self.assertEqual(
            R.slug_from_url("https://yemek.com/tarif/mercimek-corbasi/"),
            "mercimek-corbasi",
        )


if __name__ == "__main__":
    unittest.main()
