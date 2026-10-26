# TASKS

## Tamamlandı
- [x] colors.py: 24-bit renk ve ısı gradyanı
- [x] board_data.py: 40 kare, gruplar, kartlar
- [x] monopoly_game.py: kurallar, AI, iflas
- [x] monte_carlo.py: simülatör, ROI
- [x] renderer.py: tahta, ısı haritası, sayfalar
- [x] main.py: menü, oyun/simülasyon döngüleri
- [x] test_monopoly.py: 50 test, 0 hata
- [x] run.bat / run.ps1 / LICENSE / 8 çekirdek doküman

## Açık
- [ ] Gerçek Windows Terminal'de elle görsel doğrulama (125x38) ve ekran görüntüsü
- [ ] Açık artırma ve takas (ROADMAP v0.2)
- [ ] Linux/macOS tek tuş girişi

## Doğrulama komutları
- `python -m unittest test_monopoly` → `OK` (50 test)
- `python main.py --sim 100000` → ısı haritası + `[DOĞRULANDI]` satırları
