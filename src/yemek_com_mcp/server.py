"""MCP server: unofficial read-only access to Yemek.com recipes."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import recipes as _R

mcp = FastMCP("yemek-com-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for Yemek.com, Türkiye's recipe site \
(yemek.com) — search 500+ recipes per query via the site's public \
search JSON, full recipe details (ingredients, steps, times, \
servings, ratings) from schema.org Recipe data, featured categories, \
the daily "Bugün Ne Pişirsem?" picks, video recipes and the most \
popular recipes from the homepage. No login, no API key. Times are ISO 8601 \
durations (PT10M) or Turkish shorthand (15dk); servings are \
Turkish ("6 kişilik"). Read-only; transport uses Chrome TLS \
impersonation with a plain-requests fallback; requests are spaced \
~0.8s apart. Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey \
MCP factory.\
"""


def _err(e: Exception) -> str:
    return json.dumps({"error": str(e)}, ensure_ascii=False)


def _validate_limit(limit: int, lo: int = 1, hi: int = 30) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


@mcp.tool()
def yemek_search_recipes(query: str, limit: int = 10) -> str:
    """Search Yemek.com recipes by dish or ingredient.
    query: e.g. "mercimek", "tavuk", "sütlü tatlı". limit 1..30.
    Returns matching recipes (title, slug, url, prep time, rating,
    video flag, category, author) plus totals and related articles."""
    try:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        _validate_limit(limit)
        # Recipes page in 3s — paginate until `limit` or the well runs dry.
        recipes: list[dict] = []
        total_recipes = total_posts = None
        posts: list[dict] = []
        start = 0
        while len(recipes) < limit:
            page = _R.parse_search_json(
                _http.fetch_search_json(query.strip(), rows=12, recipes_start=start)
            )
            total_recipes = page["total_recipes"]
            total_posts = page["total_posts"]
            if start == 0:
                posts = page["posts"]
            if not page["recipes"]:
                break
            recipes.extend(page["recipes"])
            start += len(page["recipes"])
            if len(page["recipes"]) < 3:
                break
        data = {
            "total_recipes": total_recipes,
            "total_posts": total_posts,
            "recipes": recipes,
            "posts": posts,
        }
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    data["recipes"] = data["recipes"][:limit]
    return json.dumps({"query": query.strip(), **data}, ensure_ascii=False)


@mcp.tool()
def yemek_get_recipe(slug: str) -> str:
    """Full recipe detail: ingredients, steps, times, servings, rating.
    slug: e.g. "mercimek-corbasi" (or a full yemek.com/tarif/... URL)."""
    try:
        s = slug.strip()
        if "yemek.com/tarif/" in s:
            s = _R.slug_from_url(s)
        else:
            s = _R.slugify(s)
        if not s:
            raise ValueError("slug must not be empty")
        recipe = _R.parse_recipe_page(_http.fetch_recipe_page(s))
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    return json.dumps({"slug": s, **recipe}, ensure_ascii=False)


@mcp.tool()
def yemek_list_categories() -> str:
    """Featured recipe categories from the Yemek.com homepage
    (name, slug, url, recipe count per category)."""
    try:
        cats = _R.parse_categories(_http.fetch_home())
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    return json.dumps({"count": len(cats), "categories": cats}, ensure_ascii=False)


@mcp.tool()
def yemek_list_trending(limit: int = 15) -> str:
    """Today's "Bugün Ne Pişirsem?" picks — 15 recipes from Yemek.com's
    daily article. limit 1..15."""
    try:
        _validate_limit(limit, 1, 15)
        rows = _R.parse_bugun(_http.fetch_bugun())
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    return json.dumps(
        {"count": len(rows[:limit]), "recipes": rows[:limit]}, ensure_ascii=False
    )


@mcp.tool()
def yemek_list_videos(limit: int = 10) -> str:
    """Video recipes from the Yemek.com homepage ("Videolu Tarifler").
    limit 1..10."""
    try:
        _validate_limit(limit, 1, 10)
        rows = _R.parse_home_section(_http.fetch_home(), "Videolu Tarifler")
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    return json.dumps(
        {"count": len(rows[:limit]), "recipes": rows[:limit]}, ensure_ascii=False
    )


@mcp.tool()
def yemek_list_popular(limit: int = 10) -> str:
    """Most popular recipes from the Yemek.com homepage
    ("Popüler Yemek Tarifleri"). limit 1..10."""
    try:
        _validate_limit(limit, 1, 10)
        rows = _R.parse_home_section(_http.fetch_home(), "Popüler Yemek Tarifleri")
    except (ValueError, _http.YemekError) as e:
        return _err(e)
    return json.dumps(
        {"count": len(rows[:limit]), "recipes": rows[:limit]}, ensure_ascii=False
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    import sys

    sys.exit(main())
