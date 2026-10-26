"""Yüksek hızlı Monte Carlo simülatörü: kare iniş olasılıkları, sıralama ve ROI analizi.

Model: her "oyun", tek piyonun `turns` tur oynadığı bağımsız bir koşudur (desteler her
oyunda karıştırılır). Sayılan olay = her zar atışının SONUNDA piyonun durduğu kare
(kart/Kodese-Git yönlendirmeleri uygulanmış halde). Yani "iniş" = bir karede durma
olayı; Kodese-Git karesi yerine Kodes sayılır, Kodeste bekleyen başarısız atışlar sayılmaz.
Kodes stratejisi: çift at, 3. turda 50$ öde; elde Kodesten Çık kartı varsa hemen kullan.
"""
import os
import random
import time
from dataclasses import dataclass, field

from board_data import (
    CHANCE_CARDS, CHANCE_TILES, CHEST_CARDS, CHEST_TILES, GROUP_TILES, NEXT_RAILROAD,
    NEXT_UTILITY, TILES, Group, Kind,
)

DEFAULT_GAMES = 100_000
DEFAULT_TURNS = 50

# Kart kodları (hızlı döngü için tam sayı)
_NONE, _GOTO, _JAIL, _BACK3, _RR, _UTIL, _FREE = range(7)


def _encode(cards):
    out = []
    for c in cards:
        if c.action == "goto":
            out.append((_GOTO, c.arg))
        elif c.action == "jail":
            out.append((_JAIL, 0))
        elif c.action == "back":
            out.append((_BACK3, c.arg))
        elif c.action == "rr":
            out.append((_RR, 0))
        elif c.action == "util":
            out.append((_UTIL, 0))
        elif c.action == "jailfree":
            out.append((_FREE, 0))
        else:  # para kartları konumu değiştirmez
            out.append((_NONE, 0))
    return tuple(out)


_CHANCE = _encode(CHANCE_CARDS)
_CHEST = _encode(CHEST_CARDS)


def simulate_chunk(args):
    """(games, turns, seed) -> (counts[40], rolls, jail_entries). Saf, çoklu süreçte çalışabilir."""
    games, turns, seed = args
    rng = random.Random(seed)
    rand, shuffle = rng.random, rng.shuffle
    counts = [0] * 40
    rolls = jail_entries = 0
    chance_set, chest_set = set(CHANCE_TILES), set(CHEST_TILES)
    nrr, nut = NEXT_RAILROAD, NEXT_UTILITY
    chance_n, chest_n = len(_CHANCE), len(_CHEST)

    for _ in range(games):
        chance = list(_CHANCE)
        chest = list(_CHEST)
        shuffle(chance)
        shuffle(chest)
        ci = hi = 0  # deste imleçleri (kartlar sırayla döner)
        held_chance = held_chest = 0  # elde tutulan Kodesten Çık kartları
        pos = 0
        in_jail = False
        jail_turns = 0
        for _t in range(turns):
            doubles = 0
            while True:
                r = int(rand() * 36)
                d1, d2 = r // 6 + 1, r % 6 + 1
                is_double = d1 == d2
                rolls += 1
                if in_jail and (held_chance or held_chest):  # kartı kullan, normal at
                    if held_chance:
                        held_chance -= 1
                        chance.append((_FREE, 0))
                    else:
                        held_chest -= 1
                        chest.append((_FREE, 0))
                    in_jail = False
                if in_jail:
                    if is_double:
                        in_jail = False
                        jail_turns = 0
                        extra = False
                    else:
                        jail_turns += 1
                        if jail_turns >= 3:
                            in_jail = False
                            jail_turns = 0
                            extra = False
                        else:
                            break  # Kodeste kalma bir "iniş" değildir, sayılmaz
                else:
                    extra = is_double
                    if is_double:
                        doubles += 1
                        if doubles == 3:
                            pos = 10
                            in_jail = True
                            jail_turns = 0
                            jail_entries += 1
                            counts[10] += 1
                            break
                pos = (pos + d1 + d2) % 40
                # kare çözümü (kart zincirleri için döngü)
                while True:
                    if pos == 30:
                        pos = 10
                        in_jail = True
                        jail_turns = 0
                        jail_entries += 1
                        break
                    if pos in chance_set or pos in chest_set:
                        if pos in chance_set:
                            kind, arg = chance.pop(0)
                            deck = chance
                        else:
                            kind, arg = chest.pop(0)
                            deck = chest
                        if kind == _FREE:
                            if deck is chance:
                                held_chance += 1
                            else:
                                held_chest += 1
                            break
                        deck.append((kind, arg))
                        if kind == _GOTO:
                            pos = arg
                        elif kind == _BACK3:
                            pos = (pos - 3) % 40
                        elif kind == _RR:
                            pos = nrr[pos]
                        elif kind == _UTIL:
                            pos = nut[pos]
                        elif kind == _JAIL:
                            pos = 10
                            in_jail = True
                            jail_turns = 0
                            jail_entries += 1
                            break
                        else:
                            break
                        continue
                    break
                counts[pos] += 1
                if in_jail or not extra:
                    break
    return counts, rolls, jail_entries


@dataclass
class SimResult:
    counts: list
    games: int
    turns: int
    rolls: int
    jail_entries: int
    elapsed: float = 0.0
    workers: int = 1
    probs: list = field(init=False)

    def __post_init__(self):
        total = sum(self.counts) or 1
        self.probs = [c / total for c in self.counts]

    @property
    def total_landings(self):
        return sum(self.counts)

    def top(self, n=10, only_ownable=False):
        rows = [(i, self.probs[i]) for i in range(40) if not only_ownable or TILES[i].ownable]
        return sorted(rows, key=lambda r: -r[1])[:n]

    def rank_of(self, idx):
        return 1 + sum(1 for p in self.probs if p > self.probs[idx])

    def group_probability(self, group):
        return sum(self.probs[i] for i in GROUP_TILES[group])


def run_simulation(games=DEFAULT_GAMES, turns=DEFAULT_TURNS, seed=None, workers=None, progress=None):
    """Simülasyonu (mümkünse çok çekirdekli) çalıştırır ve SimResult döndürür."""
    start = time.perf_counter()
    base = seed if seed is not None else random.SystemRandom().randrange(1 << 30)
    workers = workers if workers is not None else min(os.cpu_count() or 1, 8)
    workers = max(1, min(workers, games))
    chunks = []
    per, extra = divmod(games, workers)
    for w in range(workers):
        chunks.append((per + (1 if w < extra else 0), turns, base + w))
    results = None
    if workers > 1:
        try:
            import multiprocessing as mp

            with mp.Pool(workers) as pool:
                results = []
                for r in pool.imap_unordered(simulate_chunk, chunks):
                    results.append(r)
                    if progress:
                        progress(len(results), len(chunks))
        except Exception:
            results, workers = None, 1
    if results is None:
        results = []
        for n, c in enumerate(chunks, 1):
            results.append(simulate_chunk(c))
            if progress:
                progress(n, len(chunks))
    counts = [sum(r[0][i] for r in results) for i in range(40)]
    return SimResult(counts, games, turns, sum(r[1] for r in results),
                     sum(r[2] for r in results), time.perf_counter() - start, workers)


# --- Yatırım geri dönüş (ROI) analizi --------------------------------------
@dataclass
class RoiRow:
    idx: int
    name: str
    group: Group
    prob: float
    invest: int
    rent: int
    income_per_turn: float  # tüm rakiplerden beklenen kira / tur
    roi_pct: float  # tur başına geri dönüş (% yatırım)
    payback: float  # geri ödeme süresi (tur)


def roi_table(result, houses=3, opponents=3):
    """Her mülk için: yatırım = fiyat + ev maliyeti, gelir = P(iniş) x kira x rakip sayısı."""
    rows = []
    for t in TILES:
        if not t.ownable:
            continue
        p = result.probs[t.idx]
        if t.kind is Kind.PROPERTY:
            invest = t.price + houses * t.house_cost
            rent = t.rents[houses]
        elif t.kind is Kind.RAILROAD:
            invest, rent = t.price, 50  # 2 istasyon sahipken tipik kira
        else:
            invest, rent = t.price, 7 * 7  # 2 hizmet: 10 x ortalama zar (7)
        income = p * rent * opponents
        rows.append(RoiRow(t.idx, t.name, t.group, p, invest, rent, income,
                           100 * income / invest, invest / income if income else float("inf")))
    return rows


def group_roi(result, houses=3, opponents=3):
    """Grup bazında toplam ROI: sum(P x kira) / sum(yatırım)."""
    out = []
    for g, idxs in GROUP_TILES.items():
        rows = [r for r in roi_table(result, houses, opponents) if r.idx in idxs]
        invest = sum(r.invest for r in rows)
        income = sum(r.income_per_turn for r in rows)
        out.append((g, income, invest, 100 * income / invest, invest / income))
    return sorted(out, key=lambda r: -r[3])
