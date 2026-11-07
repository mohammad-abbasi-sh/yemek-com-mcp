# yemek-com-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/yemek-com-mcp

Unofficial **read-only** MCP server for **Yemek.com** — Türkiye's recipe site: search recipes, full recipe details (ingredients, steps, times, servings, ratings), featured categories, the daily "Bugün Ne Pişirsem?" picks, video recipes and the most popular recipes.

> Part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with Yemek.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "yemek-com": {
      "command": "uvx",
      "args": ["yemek-com-mcp"]
    }
  }
}
```

Or run locally: `python -m yemek_com_mcp.server` (needs `mcp<2`, `curl-cffi`, `requests`).

## Tools

| Tool | Description |
|------|-------------|
| `yemek_search_recipes` | Search recipes by dish/ingredient — `query`, `limit` (1..30). Uses the site's public search JSON |
| `yemek_get_recipe` | Full recipe — `slug` (e.g. `mercimek-corbasi`) or a full yemek.com/tarif/... URL |
| `yemek_list_categories` | Featured recipe categories + recipe counts |
| `yemek_list_trending` | Today's "Bugün Ne Pişirsem?" picks (15 recipes) |
| `yemek_list_videos` | Video recipes from the homepage ("Videolu Tarifler") |
| `yemek_list_popular` | Most popular recipes ("Popüler Yemek Tarifleri") |

Example output (`yemek_search_recipes` / "mercimek"):

```json
{"query": "mercimek", "total_recipes": 533, "total_posts": 822,
 "recipes": [{"title": "Lokanta Usulünde: 4 Kişilik Mercimek Çorbası",
   "slug": "4-kisilik-mercimek-corbasi", "prep_time": "15dk",
   "category": "ÇORBA", "author": "filizssweetbakery"}]}
```

Example output (`yemek_get_recipe` / "mercimek-corbasi"):

```json
{"name": "Mercimek Çorbası (Lokanta Usulü)", "servings": "6 kişilik",
 "total_time": "PT60M", "rating": 4.3, "rating_count": 230,
 "ingredients": ["3 yemek kaşığı ayçiçek yağı", "1,5 su bardağı kırmızı ya da sarı mercimek", "..."],
 "instructions": ["Mercimek çorbası için derin bir tencereye ...", "..."]}
```

Notes:
- Search results page in 3 recipes per request — the server paginates automatically.
- Times are ISO 8601 durations (`PT60M`) or Turkish shorthand (`15dk`); servings are Turkish (`6 kişilik`).
- Data: yemek.com public pages + public search JSON (`/ara/sonuclar/`) — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" curl-cffi requests pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_recipes.py` — offline, parses real captured fixtures
- `tests/test_live.py` — 5 cautious live requests against yemek.com

## License

MIT
