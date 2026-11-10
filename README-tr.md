# yemek-com-mcp 🇹🇷

**Yemek.com** için gayriresmî, **salt-okunur** MCP sunucusu — Türkiye'nin tarif sitesi: tarif arama, tam tarif detayları (malzemeler, adımlar, süreler, porsiyon, puan), öne çıkan kategoriler, günün "Bugün Ne Pişirsem?" seçimleri, videolu tarifler ve en popüler tarifler.

> "Türkiye MCP fabrikası" parçası (Sepehr tarzı pipeline). Yemek.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemcinize ekleyin (stdio):

```json
{
  "mcpServers": {
    "yemek-com": {
      "command": "uvx",
      "args": ["yemek-com-mcp==0.1.0"]
    }
  }
}
```

## Araçlar

| Araç | Açıklama |
|------|----------|
| `yemek_search_recipes` | Yemek/malzeme ile tarif ara — `query`, `limit` (1..30). Sitenin herkese açık arama JSON'unu kullanır |
| `yemek_get_recipe` | Tam tarif — `slug` (örn. `mercimek-corbasi`) veya tam yemek.com/tarif/... URL'si |
| `yemek_list_categories` | Öne çıkan tarif kategorileri + tarif sayıları |
| `yemek_list_trending` | Günün "Bugün Ne Pişirsem?" seçimleri (15 tarif) |
| `yemek_list_videos` | Videolu tarifler ("Videolu Tarifler") |
| `yemek_list_popular` | En popüler tarifler ("Popüler Yemek Tarifleri") |

Örnek (`yemek_search_recipes` / "mercimek"): 533 tarif bulundu; ilk sonuç "Lokanta Usulünde: 4 Kişilik Mercimek Çorbası" (hazırlık 15dk). Örnek (`yemek_get_recipe` / "mercimek-corbasi"): 6 kişilik, toplam 60dk, puan 4.3 (230 oy), 12 malzeme, 8 adım.

Notlar:
- Arama sonuçları istek başına 3 tarif döner — sunucu otomatik sayfalar.
- Süreler ISO 8601 (`PT60M`) veya Türkçe kısaltma (`15dk`); porsiyon Türkçe (`6 kişilik`).
- Veri: yemek.com herkese açık sayfalar + arama JSON'u — giriş yok, API anahtarı yok, salt-okunur.

## Kurallar

Gayriresmî ve salt-okunur — giriş yok, API anahtarı yok, yazma yok. Testler: çevrimdışı fixture + canlı testler (20/20 yeşil).
