# AGENTS

Bu depoda çalışan yapay zeka ajanları için kurallar (Triad: Mavi=Antigravity, Kırmızı=ChatGPT, Turuncu=Claude).

## Çalışma ilkeleri
- Cerrahi düzenleme: dosyayı baştan yazma, yalnızca değişen bloğu güncelle.
- Terse iletişim: kanıt (test çıktısı, diff özeti) bildir, dolgu yazma.
- Worktree/yan dal açma; mevcut dalda çalış.
- Commit mesajına AI/Co-Authored-By satırı ekleme. Test kırmızıysa push etme.

## Mimari kısıtlar
- Yalnızca Python 3 standart kütüphanesi; pip bağımlılığı ekleme.
- `board_data.py` saf veri kalır; `monopoly_game.py` ve `monte_carlo.py` TUI'yi import etmez.
- Kart/kural değişikliği `board_data.py`'de yapılır; simülatör kartları oradan türetir.
- Her doküman en çok 200 satır.

## Doğrulama
1. `python -m unittest test_monopoly` → 0 hata
2. `python main.py --sim 20000` → `[SAPMA]` içermemeli
3. Görsel değişiklikte gerçek Windows Terminal'de (125x38) ekrana bak

## Rol dağılımı
- Claude: mimari, oyun motoru, TUI
- Codex: ek birim testler, veri/CLI betikleri
- ChatGPT: kör nokta ve istatistik denetimi
