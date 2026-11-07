"""Domain logic: parse Yemek.com pages + search JSON into compact dicts.

Data sources (all public, no login, no key):
- search:   GET /ara/sonuclar/?q=... — JSON {Data: {Recipe, Posts, ...}}
- recipe:   /tarif/<slug>/ — full schema.org Recipe JSON-LD
- home:     / — "En Yeniler" cards + "Öne Çıkan Tarif Kategorileri"
- trending: /bugun-ne-pisirsem/ — "Bugün Ne Pişirsem?" article, 15 recipes
- listing:  /tarif/?q=... — server-rendered recipe cards
Stdlib parsing only (re / json / html).
"""
from __future__ import annotations

import html as _html
import json
import re

_TR_MAP = str.maketrans(
    {
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u", "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
    }
)


def slugify(text: str) -> str:
    """Turkish-aware slug: 'Mercimek Çorbası' -> 'mercimek-corbasi'."""
    s = text.strip().translate(_TR_MAP).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def slug_from_url(url: str) -> str:
    """'https://yemek.com/tarif/mercimek-corbasi/' -> 'mercimek-corbasi'."""
    return url.rstrip("/").rsplit("/", 1)[-1]


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", _html.unescape(str(text))).strip()


def _ld_json(html: str, want_type: str) -> dict | None:
    """First application/ld+json block whose @type matches (or contains it)."""
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            if want_type in types:
                return item
    return None


def _instructions(raw) -> list[str]:
    """Recipe instructions: strings, or HowToStep dicts, or a single text."""
    out: list[str] = []
    if isinstance(raw, str):
        parts = [p.strip() for p in re.split(r"\n+", raw) if p.strip()]
        return [_clean(p) for p in parts]
    if isinstance(raw, list):
        for step in raw:
            if isinstance(step, str):
                out.append(_clean(step))
            elif isinstance(step, dict):
                out.append(_clean(step.get("text") or step.get("name") or ""))
    return [s for s in out if s]


def parse_search_json(payload: str | dict) -> dict:
    """Parse /ara/sonuclar/ JSON -> {total_recipes, total_posts, recipes, posts}."""
    data = json.loads(payload) if isinstance(payload, str) else payload
    d = data.get("Data") or {}
    recipes = []
    for r in d.get("Recipe") or []:
        link = r.get("Permalink") or ""
        img = ((r.get("FeaturedImage") or {}).get("MediaData") or {})
        image = (
            (img.get("ymk-medium") or {}).get("Path")
            or (img.get("ymk-thumbnail") or {}).get("Path")
            or ""
        )
        recipes.append(
            {
                "title": _clean(r.get("Title")),
                "slug": slug_from_url(link),
                "url": link,
                "prep_time": _clean(
                    r.get("RecipePrepTimeText") or r.get("RecipeOrderTimeText")
                ),
                "rating": r.get("RecipeRatingOrderPoint"),
                "has_video": bool(r.get("HasVideo")),
                "category": _clean(r.get("Label")),
                "category_url": r.get("LabelLink") or "",
                "author": _clean(r.get("AuthorDisplayName")),
                "image": image,
            }
        )
    posts = [
        {
            "title": _clean(p.get("TitleCustomized") or p.get("Title")),
            "url": p.get("Permalink") or "",
            "author": _clean(p.get("AuthorDisplayName")),
        }
        for p in (d.get("Posts") or [])
    ]
    return {
        "total_recipes": d.get("RecipesTotal"),
        "total_posts": d.get("PostsTotal"),
        "recipes": recipes,
        "posts": posts,
    }


def parse_recipe_page(html: str) -> dict:
    """Parse a /tarif/<slug>/ page via its Recipe JSON-LD."""
    ld = _ld_json(html, "Recipe")
    if ld is None:
        raise ValueError("no Recipe structured data found on this page")
    rating = ld.get("aggregateRating") or {}
    nutrition = ld.get("nutrition") or {}
    video = ld.get("video") or {}
    if isinstance(video, list):
        video = video[0] if video else {}
    author = ld.get("author")
    if isinstance(author, dict):
        author = author.get("name") or ""
    return {
        "name": _clean(ld.get("name")),
        "url": ld.get("url") or "",
        "description": _clean(ld.get("description")),
        "category": _clean(ld.get("recipeCategory")),
        "cuisine": _clean(ld.get("recipeCuisine")),
        "keywords": _clean(ld.get("keywords")),
        "prep_time": ld.get("prepTime") or "",
        "cook_time": ld.get("cookTime") or "",
        "total_time": ld.get("totalTime") or "",
        "servings": _clean(ld.get("recipeYield")),
        "ingredients": [_clean(x) for x in (ld.get("recipeIngredient") or [])],
        "instructions": _instructions(ld.get("recipeInstructions")),
        "calories": _clean(nutrition.get("calories")),
        "rating": rating.get("ratingValue"),
        "rating_count": rating.get("ratingCount"),
        "review_count": rating.get("reviewCount"),
        "has_video": bool(video),
        "video_name": _clean(video.get("name")),
        "author": _clean(author),
        "date_published": ld.get("datePublished") or "",
    }


def parse_recipe_cards(html: str) -> list[dict]:
    """Server-rendered recipe cards: title anchors (class text-lg text-heading).

    Works on /tarif/?q=... listings and the homepage "En Yeniler" grid.
    """
    out, seen = [], set()
    for href, title in re.findall(
        r'<a href="(https://yemek\.com/tarif/[^"/]+/)" class="text-lg text-heading[^"]*">(.*?)</a>',
        html,
        re.S,
    ):
        slug = slug_from_url(href)
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"title": _clean(title), "slug": slug, "url": href})
    return out


def _section(html: str, name: str) -> str:
    i = html.find(f'data-section-name="{name}"')
    if i < 0:
        return ""
    nxt = html.find("data-section-name=", i + 10)
    end = nxt if nxt > 0 else i + 60000
    j = html.rfind("<h2", 0, i)
    return html[j if j >= 0 else i: end]


def parse_home_section(html: str, name: str) -> list[dict]:
    """Recipe cards inside one homepage section (e.g. 'Videolu Tarifler',
    'Popüler Yemek Tarifleri', 'En Yeniler')."""
    seg = _section(html, name)
    if not seg:
        return []
    return parse_recipe_cards(seg)


def parse_categories(html: str) -> list[dict]:
    """Homepage 'Öne Çıkan Tarif Kategorileri' cards: name, url, recipe count."""
    seg = _section(html, "Öne Çıkan Tarif Kategorileri")
    if not seg:
        return []
    out, seen = [], set()
    for href, title in re.findall(
        r'href="https://yemek\.com(/tarif/[^"/]+/)" title="([^"]+)"', seg
    ):
        if href in seen:
            continue
        seen.add(href)
        m = re.search(
            re.escape(href) + r'.*?<span[^>]*>\s*([\d.,]+)\s*tarif\s*</span>',
            seg,
            re.S,
        )
        out.append(
            {
                "name": _clean(title.replace(" Tarifleri", "")),
                "slug": href.strip("/").split("/")[-1],
                "url": f"https://yemek.com{href}",
                "recipe_count": int(m.group(1).replace(".", "").replace(",", ""))
                if m
                else None,
            }
        )
    return out


def parse_bugun(html: str) -> list[dict]:
    """'Bugün Ne Pişirsem?' article: the 15 '... tarifi' detail links."""
    out, seen = [], set()
    for href, title in re.findall(
        r'<a href="(https://yemek\.com/tarif/[^"/]+/)"[^>]*title="([^"]*tarifi)"',
        html,
    ):
        slug = slug_from_url(href)
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"title": _clean(title), "slug": slug, "url": href})
    return out
