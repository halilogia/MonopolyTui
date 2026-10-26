# MonopolyTui

Windows Terminal ve modern terminaller için **24-bit TrueColor** Monopoly: yapay zekaya karşı oyna
ya da **100.000 oyunluk Monte Carlo** ile hangi karelere en çok gelindiğini ısı haritasında gör.
Saf Python 3 standart kütüphanesi, **0 pip bağımlılığı**.

## Hızlı başlangıç
```
run.bat            # Windows Terminal, 125x38 yeni pencere (wt yoksa mevcut konsol)
.\run.ps1          # aynısı, PowerShell
python main.py     # doğrudan menü
python main.py --sim 100000   # menüsüz: ısı haritası + analiz yazdır
python -m unittest test_monopoly   # 50 birim test
```
Gereksinim: Python 3.10+, en az 112x36 terminal (önerilen 125x38).

## Modlar
| Mod | Ne yapar |
|---|---|
| [1] Oyna | İnsan vs 1-3 AI. Satın alma, ev/otel, kira, iflas, kartlar, animasyonlu zar ve piyon |
| [2] Simülasyon | 100.000 oyun (~5,8 milyon atış) çok çekirdekte ~1-3 sn; ısı haritası, Top-10, ROI, doğrulama |

Oyun tuşları: `Enter` zar, `E/H` al/pas, `B` ev dik, `U` ipotek kaldır, `O/K/Z` kodes seçenekleri,
`F` hızlı mod, `Esc` menü. Simülasyon sonucu: `H` harita, `R` ROI, `A` analiz, `N` yeni, `Q` menü.

## Simülasyon sonuçları (100.000 oyun x 50 tur, tohum 2026)
| # | Kare | İniş % |
|---|---|---|
| 1 | Kodes (10) | 6,26 |
| 2 | Illinois Ave (24) | 3,17 |
| 3 | Reading RR (5) | 3,07 |
| 4 | B&O RR (25) | 3,05 |
| 5 | New York Ave (19) | 3,01 |
| 6 | GO (0) | 3,00 |
| 7 | Tennessee Ave (18) | 2,99 |
| 8 | Free Parking (20) | 2,98 |
| 9 | Pennsylvania RR (15) | 2,89 |
| 10 | St. James Place (16) | 2,86 |

ROI (3 ev, 3 rakip): **Turuncu %10,32/tur (9,7 tur geri ödeme)** > Kırmızı %9,20 > Koyu Mavi %9,03 > Sarı %8,91.
Tekil mülkte Boardwalk ile New York Ave başa baş (~%10,7) yarışır; New York Ave Turuncu'nun en iyisidir.
Kahverengi, Hizmet ve İstasyonlar sona kalır. Rakamlar tohuma göre binde birler düzeyinde oynar.

## Dosyalar
`main.py` menü/TUI · `board_data.py` tahta+kartlar · `monopoly_game.py` oyun · `monte_carlo.py` simülatör ·
`renderer.py` çizim · `colors.py` renkler · `test_monopoly.py` testler. Ayrıntı: ARCHITECTURE.md.

## Lisans
GPL-3.0 (bkz. LICENSE).
