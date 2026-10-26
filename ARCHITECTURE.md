# ARCHITECTURE

## Katmanlar (bağımlılık yönü yukarıdan aşağıya)
```
main.py ─────────► renderer.py ──► colors.py
   │                   │
   ├──► monopoly_game.py ──► board_data.py
   └──► monte_carlo.py   ──► board_data.py
```
- `board_data.py` (saf veri, bağımlılık yok): `Tile`, `Kind`, `Group`, kira tabloları, `NEXT_RAILROAD`/`NEXT_UTILITY`,
  16'şar Şans ve Sandık kartı (`Card(text, action, arg)`).
- `monopoly_game.py`: `Game`, `Player`, `NullUI`. Sunum bilmez; arayüze kancalarla (`on_dice`, `on_step`,
  `on_jump`, `on_event`, `choose_buy`, `choose_jail`, `build_phase`) konuşur.
- `monte_carlo.py`: oyun motorundan bağımsız, tamsayı kodlu hızlı döngü (`simulate_chunk`), `SimResult`,
  `roi_table`, `group_roi`. Kartları `board_data`'dan türetir, böylece kural tek kaynaktan gelir.
- `colors.py`: ANSI 24-bit yardımcılar, `heat_color(t)` gradyanı, görünür uzunluk/pad/clip, `enable_vt()` (ctypes).
- `renderer.py`: 110x33 tahta (11x11 hücre, hücre 10x3), orta panel 90x27; `compose_board`, oyun/ısı hücreleri,
  zar çizimi, ROI ve analiz sayfaları. Tek yazımda çizer (`HOME` + satırlar + `\x1b[J`).
- `main.py`: menü, `TuiUI` (animasyon + insan kararları), simülasyon ekranı, `--sim` CLI.

## Simülatör tasarımı
- "Oyun" = tek piyonun `turns` (varsayılan 50) tur oynadığı bağımsız koşu; desteler her oyunda karışır.
- Olay = her atış sonunda durulan kare (kart ve Kodese-Git sonrası). Kodeste bekleyen başarısız atış sayılmaz.
- Kodes stratejisi: çift at, 3. turda 50$ öde; kart varsa kullan. 3 çift = Kodes.
- Paralellik: `multiprocessing.Pool`, tohum = taban + parça no; başarısızlıkta seri yedek.
- Hız: ~5,8 M atış; 8 çekirdekte ~1,3 sn, tek çekirdekte ~3 sn.

## Çizim
- Isı normalizasyonu: Kodes ve Kodese-Git hariç min..max; Kodes kırpılıp alev kırmızısı olur.
- Gradyan durakları: (12,24,110) → (0,215,230) → (255,230,40) → (235,40,15) (Koyu Mavi→Siyan→Sarı→Kırmızı).
- Kare yerleşimi `grid_pos(idx)`: 0 sağ-alt, saat yönünün tersi; 20 sol-üst; 30 sağ-üst.

## PMA notu
Proje tek dosyalı küçük çekirdektir; `core` (board_data, monopoly_game, monte_carlo), `shared` (colors) ve
sunum (renderer, main) ayrımı dosya bazında korunur. Çekirdek TUI'yi import etmez.
