"""MonopolyTui ana menü ve TUI döngüsü.

Kullanım:  python main.py            -> etkileşimli menü
           python main.py --sim [N]  -> N oyunluk simülasyon, ısı haritasını yazdırıp çıkar
"""
import os
import random
import shutil
import sys
import time

import colors as C
import renderer as R
from monopoly_game import Game, NullUI
from monte_carlo import DEFAULT_GAMES, run_simulation
from board_data import TILES

try:
    import msvcrt
except ImportError:  # Windows dışı: satır tabanlı yedek giriş
    msvcrt = None

GOLD, GREEN, MUTED = (255, 215, 90), (120, 255, 200), R.MUTED
MIN_COLS, MIN_ROWS = R.BOARD_W + 2, R.BOARD_H + 3


class QuitToMenu(Exception):
    pass


def read_key():
    """Tek tuş okur (küçük harfe çevrilmiş). ESC -> 'esc', Enter -> 'enter'."""
    if msvcrt is None:
        s = input().strip().lower()
        return s[:1] or "enter"
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        msvcrt.getwch()
        return "special"
    return {"\r": "enter", "\x1b": "esc", " ": "space", "\x03": "esc"}.get(ch, ch.lower())


def wait_keys(valid):
    while True:
        k = read_key()
        if k == "esc":
            raise QuitToMenu
        if k in valid:
            return k


def fast_mode():
    return bool(os.environ.get("MONOPOLY_FAST"))


# --- Oyun arayüzü -------------------------------------------------------------
class TuiUI(NullUI):
    def __init__(self):
        self.prompt = ""
        self.dice = None
        self.fast = fast_mode()

    def nap(self, secs):
        if not self.fast:
            time.sleep(secs)

    def show(self, game, player=None, prompt=None):
        player = player or game.players[game.current]
        R.draw(R.game_frame(game, player, self.dice, self.prompt if prompt is None else prompt))

    def on_turn_start(self, game, player):
        self.dice = None
        self.prompt = f"{player.name} oynuyor..."
        self.show(game, player)
        self.nap(0.25)

    def on_dice(self, game, player, d1, d2):
        rng = random.Random()
        for _ in range(0 if self.fast else 7):
            self.dice = (rng.randint(1, 6), rng.randint(1, 6))
            self.show(game, player, "Zarlar atılıyor...")
            time.sleep(0.06)
        self.dice = (d1, d2)
        self.show(game, player, f"{player.name}: {d1}+{d2}={d1 + d2}")
        self.nap(0.4)

    def on_step(self, game, player):
        self.show(game, player, "")
        self.nap(0.05)

    def on_jump(self, game, player, old, new):
        self.show(game, player, "")
        self.nap(0.35)

    def on_event(self, game, text):
        self.show(game, game.players[game.current], text)
        self.nap(0.18)

    def ask(self, game, player, prompt, valid):
        self.show(game, player, prompt)
        k = wait_keys(valid | {"f"})
        while k == "f":
            self.fast = not self.fast
            k = wait_keys(valid | {"f"})
        return k

    def choose_buy(self, game, player, tile):
        k = self.ask(game, player, f"{tile.name} ${tile.price} satın alınsın mı?  [E] Evet  [H] Hayır",
                     {"e", "h", "enter"})
        return k in ("e", "enter")

    def choose_jail(self, game, player):
        opts, valid = ["[Z] Zar at (çift = çık)"], {"z", "enter"}
        if player.cash >= 50:
            opts.insert(0, "[O] 50$ öde")
            valid.add("o")
        if player.jail_cards:
            opts.insert(0, "[K] Kartı kullan")
            valid.add("k")
        k = self.ask(game, player, "KODESTESİN!  " + "  ".join(opts), valid)
        return {"o": "pay", "k": "card"}.get(k, "roll")

    def build_phase(self, game, player):
        while True:
            if game.over or player.bankrupt:
                return
            canb = game.buildable(player)
            mort = [i for i in game.props_of(player) if i in game.mortgaged]
            opts = ["[Enter] Zar at"]
            valid = {"enter", "space"}
            if canb:
                opts.insert(0, "[B] Ev/otel dik")
                valid.add("b")
            if mort:
                opts.insert(0, "[U] İpotek kaldır")
                valid.add("u")
            k = self.ask(game, player, f"Sıra sende ${player.cash}:  " + "  ".join(opts) + "  [F] Hız  [Esc] Menü", valid)
            if k in ("enter", "space"):
                return
            pool = canb if k == "b" else mort
            self.pick_property(game, player, pool, k)

    def pick_property(self, game, player, pool, mode):
        letters = "abcdefgh"
        pool = pool[:len(letters)]
        names = "  ".join(f"[{letters[n].upper()}] {TILES[i].short}" for n, i in enumerate(pool))
        k = self.ask(game, player, names + "  [X] İptal", set(letters[:len(pool)]) | {"x"})
        if k == "x":
            return
        i = pool[letters.index(k)]
        game.build(player, i) if mode == "b" else game.unmortgage(player, i)


def end_screen(game):
    ranking = sorted(game.players, key=lambda p: (not p.bankrupt, game.net_worth(p)), reverse=True)
    win = game.winner or ranking[0]
    lines = [C.paint("  OYUN BİTTİ", GOLD, bold=True), ""]
    lines.append(C.paint(f"  Kazanan: {win.name}  (servet ${game.net_worth(win)})", GREEN, bold=True))
    lines.append("")
    for n, p in enumerate(ranking, 1):
        state = "İFLAS" if p.bankrupt else f"${game.net_worth(p)}"
        lines.append(C.paint(f"  {n}. {p.name:<14} {state}", R.PLAYER_RGB[p.token]))
    lines += ["", C.paint("  Menüye dönmek için bir tuşa bas.", MUTED)]
    sys.stdout.write(C.CLEAR + "\n".join(lines) + "\n")
    sys.stdout.flush()
    read_key()


def play_game():
    sys.stdout.write(C.CLEAR + C.paint("\n  Kaç yapay zeka rakip? [1] [2] [3]   (Esc: geri)\n", GOLD, bold=True))
    k = wait_keys({"1", "2", "3"})
    names = ["Sen"] + [f"Bot {n}" for n in range(1, int(k) + 1)]
    ui = TuiUI()
    game = Game([(n, n == "Sen") for n in names], ui=ui)
    human = game.players[0]
    max_rounds = 250
    while not game.over and not human.bankrupt and game.round_no <= max_rounds:
        game.next_turn()
        if human.bankrupt:
            ui.show(game, human, "İFLAS ETTİN! Bir tuşa bas.")
            read_key()
    end_screen(game)


# --- Simülasyon arayüzü --------------------------------------------------------
def simulate_screen():
    sys.stdout.write(C.CLEAR)
    sys.stdout.write(C.paint("\n  MONTE CARLO SİMÜLASYONU\n\n", GOLD, bold=True))
    sys.stdout.write("  [1] 10.000 oyun\n  [2] 100.000 oyun (varsayılan)\n  [3] 500.000 oyun\n\n"
                     + C.paint("  Seçim (Enter = 100.000, Esc = geri)\n", MUTED))
    sys.stdout.flush()
    k = wait_keys({"1", "2", "3", "enter"})
    games = {"1": 10_000, "2": 100_000, "3": 500_000, "enter": DEFAULT_GAMES}[k]
    sys.stdout.write(C.paint(f"\n  {games:,} oyun simüle ediliyor...\n", GREEN))
    sys.stdout.flush()
    result = run_simulation(games, progress=lambda d, t: (
        sys.stdout.write(C.paint(f"\r  Parça {d}/{t} tamam", MUTED)), sys.stdout.flush()))
    show_results(result)


def show_results(result):
    page = "h"
    while True:
        if page == "h":
            R.draw(R.heat_frame(result))
        else:
            lines = R.roi_lines(result) if page == "r" else R.analysis_lines(result)
            R.draw([""] + lines)
        k = wait_keys({"h", "r", "a", "n", "q"})
        if k == "q":
            return
        if k == "n":
            return simulate_screen()
        page = k


# --- Ana menü ------------------------------------------------------------------
LOGO = ("███╗   ███╗ ██████╗ ███╗   ██╗ ██████╗ ██████╗  ██████╗ ██╗  ██╗   ██╗",
        "████╗ ████║██╔═══██╗████╗  ██║██╔═══██╗██╔══██╗██╔═══██╗██║  ╚██╗ ██╔╝",
        "██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║██████╔╝██║   ██║██║   ╚████╔╝ ",
        "██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║██╔═══╝ ██║   ██║██║    ╚██╔╝  ",
        "██║ ╚═╝ ██║╚██████╔╝██║ ╚████║╚██████╔╝██║     ╚██████╔╝███████╗██║   ",
        "╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝      ╚═════╝ ╚══════╝╚═╝   ")


def menu():
    cols, rows = shutil.get_terminal_size()
    warn = ""
    if cols < MIN_COLS or rows < MIN_ROWS:
        warn = C.paint(f"\n  Uyarı: terminal {cols}x{rows}; en az {MIN_COLS}x{MIN_ROWS} önerilir (run.bat kullan).", (255, 120, 80))
    lines = [""]
    for n, row in enumerate(LOGO):
        lines.append("  " + C.paint(row, C.heat_color(n / (len(LOGO) - 1))))
    lines += ["", C.paint("                      T  U  I   ·   24-bit TrueColor", MUTED), "",
              C.paint("   [1] Oyna        ", GREEN, bold=True) + "İnsan vs 1-3 AI bot",
              C.paint("   [2] Simülasyon  ", GREEN, bold=True) + "100.000 oyunluk Monte Carlo + ısı haritası",
              C.paint("   [Q] Çıkış", GREEN, bold=True), warn]
    sys.stdout.write(C.CLEAR + "\n".join(lines) + "\n")
    sys.stdout.flush()


def main_loop():
    while True:
        menu()
        k = read_key()
        try:
            if k == "1":
                play_game()
            elif k == "2":
                simulate_screen()
            elif k in ("q", "esc"):
                return
        except QuitToMenu:
            continue


def cli_sim(games):
    C.enable_vt()
    result = run_simulation(games)
    R.draw(R.heat_frame(result))
    print("\n".join(R.analysis_lines(result)))


def main(argv):
    if "--sim" in argv:
        i = argv.index("--sim")
        n = int(argv[i + 1]) if len(argv) > i + 1 and argv[i + 1].isdigit() else DEFAULT_GAMES
        return cli_sim(n)
    C.enable_vt()
    sys.stdout.write(C.ALT_SCREEN_ON + C.HIDE_CURSOR)
    try:
        main_loop()
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(C.SHOW_CURSOR + C.ALT_SCREEN_OFF + C.RESET)
        sys.stdout.flush()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    main(sys.argv[1:])
