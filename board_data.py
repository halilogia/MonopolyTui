"""40 karelik klasik Monopoly tahtası: kareler, renk grupları, kira tabloları, kartlar."""
from dataclasses import dataclass
from enum import Enum


class Kind(Enum):
    GO = "go"
    PROPERTY = "property"
    RAILROAD = "railroad"
    UTILITY = "utility"
    CHEST = "chest"
    CHANCE = "chance"
    TAX = "tax"
    JAIL = "jail"
    FREE_PARKING = "free_parking"
    GO_TO_JAIL = "go_to_jail"


class Group(Enum):
    BROWN = "Kahverengi"
    LIGHT_BLUE = "Açık Mavi"
    PINK = "Pembe"
    ORANGE = "Turuncu"
    RED = "Kırmızı"
    YELLOW = "Sarı"
    GREEN = "Yeşil"
    DARK_BLUE = "Koyu Mavi"
    RAILROAD = "İstasyon"
    UTILITY = "Hizmet"


GROUP_RGB = {
    Group.BROWN: (140, 85, 50),
    Group.LIGHT_BLUE: (135, 206, 250),
    Group.PINK: (230, 90, 170),
    Group.ORANGE: (250, 150, 30),
    Group.RED: (220, 40, 40),
    Group.YELLOW: (250, 220, 40),
    Group.GREEN: (30, 160, 80),
    Group.DARK_BLUE: (40, 70, 200),
    Group.RAILROAD: (150, 150, 160),
    Group.UTILITY: (180, 200, 120),
}

GO_SALARY = 200
JAIL_POS = 10
GO_TO_JAIL_POS = 30
JAIL_FINE = 50
START_CASH = 1500
INCOME_TAX = 200
LUXURY_TAX = 100


@dataclass(frozen=True)
class Tile:
    idx: int
    name: str
    short: str
    kind: Kind
    group: Group | None = None
    price: int = 0
    rents: tuple = ()  # (temel, 1 ev, 2 ev, 3 ev, 4 ev, otel)
    house_cost: int = 0
    tax: int = 0

    @property
    def ownable(self):
        return self.kind in (Kind.PROPERTY, Kind.RAILROAD, Kind.UTILITY)

    @property
    def mortgage(self):
        return self.price // 2


def _p(idx, name, short, group, price, rents, house):
    return Tile(idx, name, short, Kind.PROPERTY, group, price, rents, house)


def _rr(idx, name, short):
    return Tile(idx, name, short, Kind.RAILROAD, Group.RAILROAD, 200)


def _ut(idx, name, short):
    return Tile(idx, name, short, Kind.UTILITY, Group.UTILITY, 150)


G = Group
TILES = (
    Tile(0, "GO", "BAŞLA", Kind.GO),
    _p(1, "Mediterranean Ave", "Mediterr", G.BROWN, 60, (2, 10, 30, 90, 160, 250), 50),
    Tile(2, "Community Chest", "Sandık", Kind.CHEST),
    _p(3, "Baltic Ave", "Baltic", G.BROWN, 60, (4, 20, 60, 180, 320, 450), 50),
    Tile(4, "Income Tax", "G.Vergi", Kind.TAX, tax=INCOME_TAX),
    _rr(5, "Reading Railroad", "Reading"),
    _p(6, "Oriental Ave", "Oriental", G.LIGHT_BLUE, 100, (6, 30, 90, 270, 400, 550), 50),
    Tile(7, "Chance", "Şans", Kind.CHANCE),
    _p(8, "Vermont Ave", "Vermont", G.LIGHT_BLUE, 100, (6, 30, 90, 270, 400, 550), 50),
    _p(9, "Connecticut Ave", "Connectic", G.LIGHT_BLUE, 120, (8, 40, 100, 300, 450, 600), 50),
    Tile(10, "Jail / Just Visiting", "KODES", Kind.JAIL),
    _p(11, "St. Charles Place", "St.Charl", G.PINK, 140, (10, 50, 150, 450, 625, 750), 100),
    _ut(12, "Electric Company", "Elektrik"),
    _p(13, "States Ave", "States", G.PINK, 140, (10, 50, 150, 450, 625, 750), 100),
    _p(14, "Virginia Ave", "Virginia", G.PINK, 160, (12, 60, 180, 500, 700, 900), 100),
    _rr(15, "Pennsylvania Railroad", "Penn RR"),
    _p(16, "St. James Place", "St.James", G.ORANGE, 180, (14, 70, 200, 550, 750, 950), 100),
    Tile(17, "Community Chest", "Sandık", Kind.CHEST),
    _p(18, "Tennessee Ave", "Tennessee", G.ORANGE, 180, (14, 70, 200, 550, 750, 950), 100),
    _p(19, "New York Ave", "New York", G.ORANGE, 200, (16, 80, 220, 600, 800, 1000), 100),
    Tile(20, "Free Parking", "OTOPARK", Kind.FREE_PARKING),
    _p(21, "Kentucky Ave", "Kentucky", G.RED, 220, (18, 90, 250, 700, 875, 1050), 150),
    Tile(22, "Chance", "Şans", Kind.CHANCE),
    _p(23, "Indiana Ave", "Indiana", G.RED, 220, (18, 90, 250, 700, 875, 1050), 150),
    _p(24, "Illinois Ave", "Illinois", G.RED, 240, (20, 100, 300, 750, 925, 1100), 150),
    _rr(25, "B&O Railroad", "B&O RR"),
    _p(26, "Atlantic Ave", "Atlantic", G.YELLOW, 260, (22, 110, 330, 800, 975, 1150), 150),
    _p(27, "Ventnor Ave", "Ventnor", G.YELLOW, 260, (22, 110, 330, 800, 975, 1150), 150),
    _ut(28, "Water Works", "Su İşl."),
    _p(29, "Marvin Gardens", "Marvin G.", G.YELLOW, 280, (24, 120, 360, 850, 1025, 1200), 150),
    Tile(30, "Go To Jail", "KODESE", Kind.GO_TO_JAIL),
    _p(31, "Pacific Ave", "Pacific", G.GREEN, 300, (26, 130, 390, 900, 1100, 1275), 200),
    _p(32, "North Carolina Ave", "N.Carol.", G.GREEN, 300, (26, 130, 390, 900, 1100, 1275), 200),
    Tile(33, "Community Chest", "Sandık", Kind.CHEST),
    _p(34, "Pennsylvania Ave", "Penn Ave", G.GREEN, 320, (28, 150, 450, 1000, 1200, 1400), 200),
    _rr(35, "Short Line", "ShortLine"),
    Tile(36, "Chance", "Şans", Kind.CHANCE),
    _p(37, "Park Place", "ParkPlace", G.DARK_BLUE, 350, (35, 175, 500, 1100, 1300, 1500), 200),
    Tile(38, "Luxury Tax", "L.Vergi", Kind.TAX, tax=LUXURY_TAX),
    _p(39, "Boardwalk", "Boardwalk", G.DARK_BLUE, 400, (50, 200, 600, 1400, 1700, 2000), 200),
)

RAILROADS = tuple(t.idx for t in TILES if t.kind is Kind.RAILROAD)
UTILITIES = tuple(t.idx for t in TILES if t.kind is Kind.UTILITY)
CHANCE_TILES = tuple(t.idx for t in TILES if t.kind is Kind.CHANCE)
CHEST_TILES = tuple(t.idx for t in TILES if t.kind is Kind.CHEST)

GROUP_TILES = {}
for _t in TILES:
    if _t.group is not None:
        GROUP_TILES.setdefault(_t.group, []).append(_t.idx)
GROUP_TILES = {g: tuple(v) for g, v in GROUP_TILES.items()}


def next_of(pos, targets):
    """`pos` karesinden ileri yöndeki en yakın hedef kare."""
    for t in targets:
        if t > pos:
            return t
    return targets[0]


NEXT_RAILROAD = tuple(next_of(p, RAILROADS) for p in range(40))
NEXT_UTILITY = tuple(next_of(p, UTILITIES) for p in range(40))


# --- Kartlar -----------------------------------------------------------------
@dataclass(frozen=True)
class Card:
    text: str
    action: str  # goto | jail | back | rr | util | money | jailfree | repairs | pay_each | collect_each
    arg: object = 0


CHANCE_CARDS = (
    Card("Başlangıç'a ilerle (200$ al)", "goto", 0),
    Card("Illinois Ave'ye ilerle", "goto", 24),
    Card("St. Charles Place'e ilerle", "goto", 11),
    Card("En yakın Hizmet karesine ilerle (10x zar)", "util"),
    Card("En yakın İstasyona ilerle (2x kira)", "rr"),
    Card("En yakın İstasyona ilerle (2x kira)", "rr"),
    Card("Banka temettü öder: 50$ al", "money", 50),
    Card("Kodesten Çık kartı", "jailfree"),
    Card("3 kare geri git", "back", 3),
    Card("Kodese git", "jail"),
    Card("Genel tamirat: ev başı 25$, otel başı 100$", "repairs", (25, 100)),
    Card("Fakirlik vergisi: 15$ öde", "money", -15),
    Card("Reading Railroad'a ilerle", "goto", 5),
    Card("Boardwalk'a ilerle", "goto", 39),
    Card("Başkan seçildin: her oyuncuya 50$ öde", "pay_each", 50),
    Card("Bina kredin vadesi geldi: 150$ al", "money", 150),
)

CHEST_CARDS = (
    Card("Başlangıç'a ilerle (200$ al)", "goto", 0),
    Card("Banka hatası lehine: 200$ al", "money", 200),
    Card("Doktor ücreti: 50$ öde", "money", -50),
    Card("Hisse satışından 50$ kazan", "money", 50),
    Card("Kodesten Çık kartı", "jailfree"),
    Card("Kodese git", "jail"),
    Card("Tatil fonu olgunlaştı: 100$ al", "money", 100),
    Card("Gelir vergisi iadesi: 20$ al", "money", 20),
    Card("Doğum günün: her oyuncudan 10$ al", "collect_each", 10),
    Card("Hayat sigortası olgunlaştı: 100$ al", "money", 100),
    Card("Hastane masrafı: 100$ öde", "money", -100),
    Card("Okul ücreti: 50$ öde", "money", -50),
    Card("Danışmanlık ücreti: 25$ al", "money", 25),
    Card("Sokak tamiratı: ev başı 40$, otel başı 115$", "repairs", (40, 115)),
    Card("Güzellik yarışmasında 2.lik: 10$ al", "money", 10),
    Card("Miras kaldı: 100$ al", "money", 100),
)
