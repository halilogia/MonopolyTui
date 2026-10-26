"""24-bit TrueColor tahta çizimi, ısı haritası görselleştirmesi ve sayfa üreticileri."""
import sys

import colors as C
from board_data import GROUP_RGB, GROUP_TILES, TILES, Group, Kind
from monte_carlo import group_roi, roi_table

CELL_W, CELL_H = 10, 3
GRID = 11
BOARD_W, BOARD_H = CELL_W * GRID, CELL_H * GRID  # 110 x 33
CENTER_W, CENTER_H = CELL_W * 9, CELL_H * 9  # 90 x 27

PLAYER_RGB = [(255, 95, 95), (90, 200, 255), (120, 230, 120), (255, 205, 60)]
TILE_BG = (26, 29, 38)
TILE_HI = (58, 64, 96)
TEXT = (225, 228, 240)
MUTED = (140, 146, 165)
PANEL_BG = (16, 18, 26)

KIND_STYLE = {
    Kind.GO: ("BAŞLA ►", (60, 190, 90)),
    Kind.CHANCE: ("? ŞANS ?", (255, 150, 30)),
    Kind.CHEST: ("▣ SANDIK", (80, 160, 240)),
    Kind.TAX: ("$ VERGİ $", (190, 190, 200)),
    Kind.JAIL: ("║ KODES ║", (255, 130, 40)),
    Kind.FREE_PARKING: ("OTOPARK", (90, 210, 190)),
    Kind.GO_TO_JAIL: ("► KODESE", (235, 70, 70)),
    Kind.RAILROAD: ("İSTASYON", GROUP_RGB[Group.RAILROAD]),
    Kind.UTILITY: ("HİZMET", GROUP_RGB[Group.UTILITY]),
}


def grid_pos(idx):
    """Kare numarası -> (satır, sütun); 0 sağ-alt, saat yönünün tersine ilerler."""
    if idx <= 10:
        return GRID - 1, GRID - 1 - idx
    if idx <= 20:
        return GRID - 1 - (idx - 10), 0
    if idx <= 30:
        return 0, idx - 20
    return idx - 30, GRID - 1


def _center(text, width=CELL_W):
    return C.pad(text, width, "center")


# --- Kare hücreleri ----------------------------------------------------------
def _band(tile):
    """1. satır: renk bandı + (evler/otel)."""
    return GROUP_RGB.get(tile.group) if tile.group else None


def game_cell(idx, game, active_idx=None):
    tile = TILES[idx]
    bgc = TILE_HI if idx == active_idx else TILE_BG
    band = _band(tile)
    if tile.kind is Kind.PROPERTY:
        h = game.houses[idx]
        mark = "OTEL" if h == 5 else "■" * h
        top = C.paint(_center(mark), (0, 0, 0), band, bold=True)
    elif tile.kind in (Kind.RAILROAD, Kind.UTILITY):
        top = C.paint(_center(KIND_STYLE[tile.kind][0]), (0, 0, 0), band, bold=True)
    else:
        label, col = KIND_STYLE[tile.kind]
        top = C.paint(_center(label), col, bgc, bold=True)
    mid = C.paint(_center(tile.short), TEXT, bgc)
    toks = "".join(C.paint(f" {p.token + 1}", (0, 0, 0), PLAYER_RGB[p.token], bold=True)
                   for p in game.players if p.pos == idx and not p.bankrupt)
    owner = game.owner.get(idx)
    if owner is not None:
        dot = C.paint("◌" if idx in game.mortgaged else "●", PLAYER_RGB[owner.token], bgc, bold=True)
        gap = C.paint(" " * (CELL_W - C.visible_len(toks) - 1), back=bgc)
        bot = toks + gap + dot
    elif tile.ownable and not toks:
        bot = C.paint(_center(f"${tile.price}"), MUTED, bgc)
    else:
        bot = toks + C.paint(" " * (CELL_W - C.visible_len(toks)), back=bgc)
    return [top, mid, bot]


def heat_norm(probs):
    """Kodes (ölçek dışı) ve Kodese-Git (0) hariç min..max aralığına normalize eder."""
    rest = [p for i, p in enumerate(probs) if i != 30]
    props = [p for i, p in enumerate(probs) if i not in (10, 30)]
    lo, hi = min(rest), max(props)
    span = (hi - lo) or 1.0
    return lambda p: max(0.0, min(1.0, (p - lo) / span)), lo, hi


def heat_cell(idx, probs, norm, rank):
    tile = TILES[idx]
    col = C.heat_color(norm(probs[idx]))
    fore = C.contrast_fg(col)
    band = _band(tile)
    rank_txt = f"#{rank}"
    if band:
        top = C.paint("  ", back=band) + C.paint(C.pad(rank_txt, CELL_W - 4, "center"), fore, col, bold=True) \
            + C.paint("  ", back=band)
    else:
        top = C.paint(_center(rank_txt), fore, col, bold=True)
    mid = C.paint(_center(tile.short), fore, col)
    bot = C.paint(_center(f"{probs[idx] * 100:.2f}%"), fore, col, bold=True)
    return [top, mid, bot]


# --- Tahta birleştirme -------------------------------------------------------
def _on_panel(line, width):
    """Panel arka planını RESET'lerden sonra da koruyarak satırı doldurur."""
    line = C.pad(line, width)
    back = C.bg(*PANEL_BG)
    return back + line.replace(C.RESET, C.RESET + back) + C.RESET


def compose_board(cell_fn, center_lines):
    out = []
    cells = {i: cell_fn(i) for i in range(40)}
    center = [_on_panel(l, CENTER_W) for l in (center_lines + [""] * CENTER_H)[:CENTER_H]]
    for r in range(GRID):
        for sub in range(CELL_H):
            parts = []
            for c in range(GRID):
                if r in (0, GRID - 1) or c in (0, GRID - 1):
                    idx = next(i for i in range(40) if grid_pos(i) == (r, c))
                    parts.append(cells[idx][sub])
                elif c == 1:
                    parts.append(center[(r - 1) * CELL_H + sub])
            out.append("".join(parts))
    return out


def draw(lines):
    """Tüm kareyi tek yazımda çizer (titreşimsiz)."""
    buf = C.HOME + "".join(l + "\x1b[K\n" for l in lines) + "\x1b[J"
    sys.stdout.write(buf)
    sys.stdout.flush()


# --- Zar ---------------------------------------------------------------------
_PIPS = {1: "....#....", 2: "#.......#", 3: "#...#...#", 4: "#.#...#.#", 5: "#.#.#.#.#", 6: "#.##.##.#"}


def dice_art(value, color=(240, 240, 250)):
    """9x5 zar yüzü (5 satır)."""
    pips = _PIPS[value]
    rows = [C.paint("┌───────┐", color)]
    for r in range(3):
        cells = " ".join("●" if pips[r * 3 + c] == "#" else " " for c in range(3))
        rows.append(C.paint("│ ", color) + C.paint(cells, (255, 80, 80), bold=True) + C.paint(" │", color))
    rows.append(C.paint("└───────┘", color))
    return rows


def dice_pair(d1, d2):
    a, b = dice_art(d1), dice_art(d2)
    return [x + "  " + y for x, y in zip(a, b)]


# --- Oyun ekranı -------------------------------------------------------------
def player_rows(game, current):
    rows = [C.paint(" Oyuncu          Nakit    Konum               Mülk  Servet  Durum", MUTED)]
    for p in game.players:
        col = PLAYER_RGB[p.token]
        arrow = "►" if p is current and not p.bankrupt else " "
        status = "İFLAS" if p.bankrupt else ("KODESTE" if p.in_jail else "")
        name = f"{arrow}{p.token + 1} {p.name}"
        line = (f" {C.pad(name, 15)} {C.pad('$' + str(p.cash), 8, 'right')} "
                f"{C.pad(TILES[p.pos].name, 20)}{C.pad(str(len(game.props_of(p))), 4, 'right')}"
                f"{C.pad('$' + str(game.net_worth(p)), 8, 'right')}  {status}")
        rows.append(C.paint(line, col if not p.bankrupt else MUTED, bold=p is current))
    return rows


def game_center(game, current, dice=None, prompt="", log_lines=9):
    L = [C.paint(C.pad(" ◆ MONOPOLY TUI ◆   Tur " + str(game.round_no), CENTER_W, "center"),
                 (255, 215, 90), bold=True), ""]
    L += player_rows(game, current)
    L.append("")
    if dice:
        art = dice_pair(*dice)
        side = [C.paint(f"  Zar: {dice[0]} + {dice[1]} = {sum(dice)}", TEXT, bold=True)]
        if dice[0] == dice[1]:
            side.append(C.paint("  ÇİFT ZAR! (tekrar atılır)", (255, 215, 90), bold=True))
        for i, a in enumerate(art):
            L.append("  " + a + (side[i - 1] if 1 <= i <= len(side) else ""))
    else:
        L += [""] * 5
    L.append("")
    L.append(C.paint(" Olay günlüğü", MUTED))
    for t in game.log[-log_lines:]:
        L.append(C.paint(" " + t, TEXT))
    while len(L) < CENTER_H - 1:
        L.append("")
    L = L[:CENTER_H - 1]
    L.append(C.paint(" " + prompt, (120, 255, 200), bold=True))
    return L


def game_frame(game, current, dice=None, prompt=""):
    cell = lambda i: game_cell(i, game, current.pos if current else None)
    board = compose_board(cell, game_center(game, current, dice, prompt))
    head = C.paint(C.pad("  MONOPOLY TUI  ·  İnsan vs AI", BOARD_W), (255, 215, 90), bold=True)
    foot = C.paint(C.pad("  ● mülk sahibi (◌ ipotekli)   ■ ev   1-4 piyonlar", BOARD_W), MUTED)
    return [head] + board + [foot]


# --- Isı haritası ekranı -----------------------------------------------------
def heat_center(result):
    probs = result.probs
    norm, lo, hi = heat_norm(probs)
    L = [C.paint(C.pad(" ◆ ISI HARİTASI — İNİŞ OLASILIĞI ◆", CENTER_W, "center"), (255, 215, 90), bold=True),
         C.paint(C.pad(f"{result.games:,} oyun · {result.rolls:,} atış · {result.elapsed:.1f} sn · "
                       f"{result.workers} çekirdek", CENTER_W, "center"), MUTED), ""]
    L.append(C.paint(" Sıra Kare                      Olasılık   Grup", MUTED))
    for n, (i, p) in enumerate(result.top(10), 1):
        t = TILES[i]
        col = C.heat_color(norm(p))
        grp = t.group.value if t.group else "-"
        bar = "█" * max(1, int(p * 100 * 6))
        L.append(" " + C.paint(f"{n:>3}. ", MUTED) + C.paint(C.pad(f"{t.name} ({i})", 27), TEXT)
                 + C.paint(f"{p * 100:6.2f}%  ", col, bold=True) + C.paint(C.pad(grp, 11), MUTED)
                 + C.paint(bar[:26], col))
    L += ["", " " + C.gradient_bar(40, f"{lo * 100:.2f}%", f"{hi * 100:.2f}%+")]
    L.append(C.paint(" Koyu Mavi → Siyan → Sarı → Alev Kırmızı  (Kodes ölçek dışı, kırpılır)", MUTED))
    L.append(C.paint(" Kodese-Git (30) %0: oraya inen piyon doğrudan Kodes'e gönderilir.", MUTED))
    L += ["", C.paint(" [H] Harita  [R] ROI tablosu  [A] Matematiksel analiz  [N] Yeni sim  [Q] Menü", (120, 255, 200))]
    return L


def heat_frame(result):
    probs = result.probs
    norm, _, _ = heat_norm(probs)
    order = sorted(range(40), key=lambda i: -probs[i])
    rank = {i: n for n, i in enumerate(order, 1)}
    board = compose_board(lambda i: heat_cell(i, probs, norm, rank[i]), heat_center(result))
    head = C.paint(C.pad("  MONOPOLY TUI  ·  Monte Carlo Isı Haritası", BOARD_W), (255, 215, 90), bold=True)
    foot = C.paint(C.pad("  Hücre: #sıra · kısa ad · iniş %   Üst bant köşeleri: renk grubu", BOARD_W), MUTED)
    return [head] + board + [foot]


# --- Metin sayfaları ---------------------------------------------------------
def roi_lines(result, houses=3, opponents=3, top=14):
    rows = sorted(roi_table(result, houses, opponents), key=lambda r: -r.roi_pct)
    hi, lo = rows[0].roi_pct, rows[-1].roi_pct
    L = [C.paint(f" YATIRIM GERİ DÖNÜŞ (ROI) — {houses} ev, {opponents} rakip · gelir = P(iniş) × kira × rakip",
                 (255, 215, 90), bold=True),
         C.paint(" Sıra Mülk                  Grup        P(iniş)  Yatırım   Kira  Gelir/tur  ROI/tur  Geri ödeme", MUTED)]
    for n, r in enumerate(rows[:top], 1):
        col = C.heat_color((r.roi_pct - lo) / ((hi - lo) or 1))
        L.append(f" {n:>3}. {C.pad(r.name, 21)} {C.pad(r.group.value, 11)} {r.prob * 100:6.2f}% "
                 f"{'$' + str(r.invest):>8} {'$' + str(r.rent):>6} {r.income_per_turn:9.1f}$ "
                 + C.paint(f"{r.roi_pct:6.2f}%", col, bold=True) + f"  {r.payback:6.1f} tur")
    L += ["", C.paint(" GRUP SIRALAMASI (toplam gelir / toplam yatırım)", (255, 215, 90), bold=True),
          C.paint(" Sıra Grup         Yatırım   Gelir/tur   ROI/tur   Geri ödeme", MUTED)]
    groups = group_roi(result, houses, opponents)
    ghi, glo = groups[0][3], groups[-1][3]
    for n, (g, income, invest, roi, payback) in enumerate(groups, 1):
        col = C.heat_color((roi - glo) / ((ghi - glo) or 1))
        L.append(f" {n:>3}. " + C.paint("■ ", GROUP_RGB[g]) + f"{C.pad(g.value, 11)} {'$' + str(invest):>8} "
                 f"{income:10.1f}$ " + C.paint(f"{roi:8.2f}%", col, bold=True) + f"  {payback:6.1f} tur")
    L += ["", C.paint(" Not: İstasyon 2 adet sahipken (50$), Hizmet 2 adet sahipken (10×ort. zar 7) varsayılır.", MUTED),
          C.paint(" [H] Harita  [R] ROI  [A] Analiz  [Q] Menü", (120, 255, 200))]
    return L


def analysis_lines(result):
    probs = result.probs
    ok = lambda b: C.paint("[DOĞRULANDI]", (90, 230, 120), bold=True) if b else C.paint("[SAPMA]", (255, 90, 90), bold=True)
    jail_rank = result.rank_of(10)
    prop = [(i, p) for i, p in result.top(40) if TILES[i].kind is Kind.PROPERTY]
    ill_rank = [i for i, _ in prop].index(24) + 1
    best_prop = prop[0]
    all_own = result.top(1, only_ownable=True)[0]
    groups = group_roi(result)
    singles = sorted(roi_table(result), key=lambda r: -r.roi_pct)
    ny_rank = [r.idx for r in singles].index(19) + 1
    orange = [r for r in singles if r.group is Group.ORANGE]
    ny_best_orange = orange[0].idx == 19
    entry_rate = result.jail_entries / result.rolls * 100
    avg = 100 / 40
    H = lambda s: C.paint(s, (255, 215, 90), bold=True)
    L = [H(" MATEMATİKSEL GERÇEK DOĞRULAMASI"),
         C.paint(f" Örneklem: {result.total_landings:,} iniş · eşit dağılım taban değeri %{avg:.2f}", MUTED), "",
         f" 1) Kodes en çok gelinen kare mi?  Kodes %{probs[10] * 100:.2f}, sıra #{jail_rank}  " + ok(jail_rank == 1),
         C.paint(f"    Neden: Kodese giriş atışların %{entry_rate:.2f}'inde olur (Kodese-Git karesi, 3 çift, 2 kart);", TEXT),
         C.paint("    tüm girişler 30 yerine 10'a yığılır: normal ziyaret (%2.5) + giriş yığılması = taban değerin ~2.5 katı.", TEXT), "",
         f" 2) Illinois Ave (24) en çok gelinen mülk mü?  %{probs[24] * 100:.2f}, mülkler arası #{ill_rank}  "
         + ok(best_prop[0] == 24 and all_own[0] == 24),
         C.paint("    Neden: Kodesten çıkan piyon 12-22 bandına dağılır (ortalama 7 adım); bu bandı geçenler", TEXT),
         C.paint("    Kırmızı grubun sonunda toplanır ve Şans'ın 'Illinois'e git' kartı 24'e ek ağırlık verir.", TEXT),
         C.paint("    İstasyonlar (Reading, B&O) 'en yakın istasyon' kartlarıyla hemen arkasından gelir.", TEXT), "",
         f" 3) New York Ave tekil ROI sırası #{ny_rank} (%{singles[ny_rank - 1].roi_pct:.2f}/tur, "
         f"{singles[ny_rank - 1].payback:.1f} tur); Turuncu içinde #1  " + ok(ny_rank <= 3 and ny_best_orange),
         C.paint(f"    Lider: {singles[0].name} (%{singles[0].roi_pct:.2f}); ancak mülk başına ${singles[0].invest} yatırım ister"
                 f" ve grupta yalnızca 2 kare vardır.", TEXT),
         f" 4) En yüksek ROI'li grup: {groups[0][0].value} (%{groups[0][3]:.2f}/tur); 2.: {groups[1][0].value}"
         f"; 3.: {groups[2][0].value}  " + ok(groups[0][0] is Group.ORANGE),
         C.paint("    Neden: Kodes çıkışı 12-22 bandını şişirir (Turuncu 16-19 tam bu bantta, Kırmızı 21-24", TEXT),
         C.paint("    hemen yanında); kiralar 3 evde ~550-750$ iken yatırım yalnızca 480-670$.", TEXT),
         C.paint("    Kahverengi/İstasyon/Hizmet düşük kira yüzünden sona kalır.", TEXT), "",
         f" 5) Kodese-Git (30) iniş olasılığı %{probs[30] * 100:.2f} (her iniş Kodes'e yönlenir)  " + ok(probs[30] == 0),
         f" 6) Toplam olasılık = %{sum(probs) * 100:.4f}  " + ok(abs(sum(probs) - 1) < 1e-9), "",
         C.paint(" [H] Harita  [R] ROI  [A] Analiz  [Q] Menü", (120, 255, 200))]
    return L
