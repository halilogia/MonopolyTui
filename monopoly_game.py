"""Oyun mantığı: oyuncular, yapay zeka, ev/otel, kira, kartlar, iflas, tur akışı."""
import random
from collections import deque

from board_data import (
    CHANCE_CARDS, CHEST_CARDS, GO_SALARY, GROUP_TILES, JAIL_FINE,
    JAIL_POS, NEXT_RAILROAD, NEXT_UTILITY, RAILROADS, START_CASH, TILES, UTILITIES,
    Kind,
)

MAX_BUILD = 5  # 5 = otel
JAILFREE_CARD = {"chance": CHANCE_CARDS[7], "chest": CHEST_CARDS[4]}


class Player:
    def __init__(self, name, human=False, token=0):
        self.name = name
        self.human = human
        self.token = token
        self.pos = 0
        self.cash = START_CASH
        self.in_jail = False
        self.jail_turns = 0
        self.jail_cards = []  # kartın geldiği deste adları
        self.bankrupt = False

    def __repr__(self):
        return f"<Player {self.name} ${self.cash} @{self.pos}>"


class NullUI:
    """Arayüz kancaları; varsayılanlar sessizdir ve AI kararlarını kullanır."""

    def on_dice(self, game, player, d1, d2): pass
    def on_step(self, game, player): pass
    def on_jump(self, game, player, old, new): pass
    def on_event(self, game, text): pass
    def on_turn_start(self, game, player): pass
    def choose_buy(self, game, player, tile): return None
    def choose_jail(self, game, player): return None
    def build_phase(self, game, player): return False


class Game:
    def __init__(self, players, seed=None, ui=None):
        """players: [(isim, insan_mı), ...]"""
        self.rng = random.Random(seed)
        self.ui = ui or NullUI()
        self.players = [Player(n, h, i) for i, (n, h) in enumerate(players)]
        self.owner = {}  # kare -> Player
        self.houses = {t.idx: 0 for t in TILES if t.kind is Kind.PROPERTY}
        self.mortgaged = set()
        self.decks = {"chance": list(CHANCE_CARDS), "chest": list(CHEST_CARDS)}
        self.rng.shuffle(self.decks["chance"])
        self.rng.shuffle(self.decks["chest"])
        self.dice_queue = deque()  # testler için zorlanmış zarlar
        self.log = []
        self.current = 0
        self.round_no = 1
        self.last_dice = (0, 0)

    # --- yardımcılar -----------------------------------------------------
    def say(self, text):
        self.log.append(text)
        del self.log[:-200]
        self.ui.on_event(self, text)

    def active_players(self):
        return [p for p in self.players if not p.bankrupt]

    @property
    def over(self):
        return len(self.active_players()) <= 1

    @property
    def winner(self):
        act = self.active_players()
        return act[0] if len(act) == 1 else None

    def roll_dice(self):
        if self.dice_queue:
            d = self.dice_queue.popleft()
        else:
            d = (self.rng.randint(1, 6), self.rng.randint(1, 6))
        self.last_dice = d
        return d

    def props_of(self, player):
        return sorted(i for i, o in self.owner.items() if o is player)

    def owns_group(self, player, group):
        return all(self.owner.get(i) is player for i in GROUP_TILES[group])

    def count_owned(self, player, targets):
        return sum(1 for i in targets if self.owner.get(i) is player)

    def net_worth(self, player):
        total = player.cash
        for i in self.props_of(player):
            t = TILES[i]
            total += t.mortgage if i in self.mortgaged else t.price
            total += self.houses.get(i, 0) * t.house_cost
        return total

    # --- kira ------------------------------------------------------------
    def rent_for(self, idx, dice_total=7, card=None):
        tile, owner = TILES[idx], self.owner.get(idx)
        if owner is None or idx in self.mortgaged:
            return 0
        if tile.kind is Kind.PROPERTY:
            h = self.houses[idx]
            if h:
                return tile.rents[h]
            return tile.rents[0] * (2 if self.owns_group(owner, tile.group) else 1)
        if tile.kind is Kind.RAILROAD:
            rent = 25 * 2 ** (self.count_owned(owner, RAILROADS) - 1)
            return rent * 2 if card == "rr" else rent
        n = self.count_owned(owner, UTILITIES)
        mult = 10 if (n == 2 or card == "util") else 4
        return mult * dice_total

    # --- para ------------------------------------------------------------
    def raise_cash(self, player, needed):
        """Ev sat, sonra mülk ipotek et; hedef nakde ulaşınca dur."""
        while player.cash < needed:
            cand = [i for i in self.props_of(player) if self.houses.get(i, 0) > 0]
            if not cand:
                break
            best = max(cand, key=lambda i: (self.houses[i], TILES[i].house_cost))
            self.sell_house(player, best, force=True)
        for i in sorted(self.props_of(player), key=lambda i: TILES[i].price):
            if player.cash >= needed:
                break
            if i not in self.mortgaged and self.houses.get(i, 0) == 0:
                self.mortgaged.add(i)
                player.cash += TILES[i].mortgage
                self.say(f"{player.name} {TILES[i].name} mülkünü ipotek etti (+{TILES[i].mortgage}$)")

    def pay(self, player, amount, creditor=None):
        """Öder; yetmezse varlık satar, yine yetmezse iflas eder. Ödendi mi?"""
        if amount <= 0:
            return True
        if player.cash < amount:
            self.raise_cash(player, amount)
        if player.cash >= amount:
            player.cash -= amount
            if creditor:
                creditor.cash += amount
            return True
        self.declare_bankrupt(player, creditor)
        return False

    def declare_bankrupt(self, player, creditor=None):
        player.bankrupt = True
        self.say(f"{player.name} İFLAS ETTİ!" + (f" Alacaklı: {creditor.name}" if creditor else ""))
        if creditor:
            creditor.cash += player.cash
            creditor.jail_cards.extend(player.jail_cards)
        else:
            for src in player.jail_cards:  # sahipsiz kalan kart desteye döner
                self.decks[src].append(JAILFREE_CARD[src])
        player.cash = 0
        player.jail_cards = []
        for i in self.props_of(player):
            if i in self.houses:
                self.houses[i] = 0
            if creditor:
                self.owner[i] = creditor
            else:
                del self.owner[i]
                self.mortgaged.discard(i)
        player.in_jail = False

    # --- inşaat ----------------------------------------------------------
    def can_build(self, player, idx):
        tile = TILES[idx]
        if tile.kind is not Kind.PROPERTY or self.owner.get(idx) is not player:
            return False
        if not self.owns_group(player, tile.group):
            return False
        grp = GROUP_TILES[tile.group]
        if any(i in self.mortgaged for i in grp):
            return False
        h = self.houses[idx]
        return h < MAX_BUILD and h <= min(self.houses[i] for i in grp) and player.cash >= tile.house_cost

    def buildable(self, player):
        return [i for i in self.props_of(player) if self.can_build(player, i)]

    def build(self, player, idx):
        if not self.can_build(player, idx):
            return False
        player.cash -= TILES[idx].house_cost
        self.houses[idx] += 1
        what = "OTEL" if self.houses[idx] == MAX_BUILD else f"{self.houses[idx]}. ev"
        self.say(f"{player.name} {TILES[idx].name} üzerine {what} dikti (-{TILES[idx].house_cost}$)")
        return True

    def sell_house(self, player, idx, force=False):
        tile = TILES[idx]
        if tile.kind is not Kind.PROPERTY or self.owner.get(idx) is not player or self.houses[idx] == 0:
            return False
        grp = GROUP_TILES[tile.group]
        if not force and self.houses[idx] < max(self.houses[i] for i in grp):
            return False
        self.houses[idx] -= 1
        player.cash += tile.house_cost // 2
        return True

    def unmortgage(self, player, idx):
        cost = int(TILES[idx].mortgage * 1.1)
        if self.owner.get(idx) is player and idx in self.mortgaged and player.cash >= cost:
            player.cash -= cost
            self.mortgaged.discard(idx)
            self.say(f"{player.name} {TILES[idx].name} ipoteğini kaldırdı (-{cost}$)")
            return True
        return False

    def buy(self, player, idx):
        tile = TILES[idx]
        if not tile.ownable or idx in self.owner or player.cash < tile.price:
            return False
        player.cash -= tile.price
        self.owner[idx] = player
        self.say(f"{player.name} {tile.name} mülkünü satın aldı (-{tile.price}$)")
        return True

    # --- yapay zeka ------------------------------------------------------
    def ai_wants_buy(self, player, tile):
        if player.cash < tile.price:
            return False
        grp = GROUP_TILES[tile.group]
        mine = self.count_owned(player, grp)
        if mine == len(grp) - 1:  # monopoli tamamlar
            return True
        return player.cash - tile.price >= (100 if tile.kind is not Kind.PROPERTY else 150)

    def ai_manage(self, player):
        for i in list(self.props_of(player)):
            if i in self.mortgaged and player.cash > TILES[i].mortgage * 1.1 + 500:
                self.unmortgage(player, i)
        for _ in range(40):
            if player.cash < 250:
                break
            cands = [i for i in self.buildable(player) if player.cash - TILES[i].house_cost >= 200]
            if not cands:
                break
            self.build(player, min(cands, key=lambda i: (self.houses[i], TILES[i].house_cost)))

    # --- hareket ---------------------------------------------------------
    def _collect_go(self, player):
        player.cash += GO_SALARY
        self.say(f"{player.name} BAŞLA'dan geçti (+{GO_SALARY}$)")

    def advance(self, player, steps):
        """Adım adım ilerletir (animasyon kancası ile)."""
        for _ in range(steps):
            player.pos = (player.pos + 1) % 40
            if player.pos == 0:
                self._collect_go(player)
            self.ui.on_step(self, player)

    def move_to(self, player, dest, collect=True):
        old = player.pos
        player.pos = dest
        if collect and dest < old:
            self._collect_go(player)
        self.ui.on_jump(self, player, old, dest)

    def send_to_jail(self, player):
        old = player.pos
        player.pos = JAIL_POS
        player.in_jail = True
        player.jail_turns = 0
        self.say(f"{player.name} KODESE GİTTİ!")
        self.ui.on_jump(self, player, old, JAIL_POS)

    # --- kareye iniş -----------------------------------------------------
    def land(self, player, dice_total, card=None):
        tile = TILES[player.pos]
        self.say(f"{player.name} → {tile.name}")
        k = tile.kind
        if k is Kind.GO_TO_JAIL:
            self.send_to_jail(player)
        elif k is Kind.CHANCE:
            self.draw_card(player, "chance", dice_total)
        elif k is Kind.CHEST:
            self.draw_card(player, "chest", dice_total)
        elif k is Kind.TAX:
            self.say(f"{player.name} {tile.tax}$ vergi ödedi")
            self.pay(player, tile.tax)
        elif tile.ownable:
            owner = self.owner.get(tile.idx)
            if owner is None:
                self._offer(player, tile)
            elif owner is not player and not owner.bankrupt:
                rent = self.rent_for(tile.idx, dice_total, card)
                if rent:
                    self.say(f"{player.name}, {owner.name}'e {rent}$ kira öder")
                    self.pay(player, rent, owner)

    def _offer(self, player, tile):
        if player.cash < tile.price:
            return
        choice = self.ui.choose_buy(self, player, tile) if player.human else None
        if choice is None:
            choice = self.ai_wants_buy(player, tile)
        if choice:
            self.buy(player, tile.idx)

    def draw_card(self, player, deck_name, dice_total):
        deck = self.decks[deck_name]
        card = deck.pop(0)
        if card.action != "jailfree":
            deck.append(card)
        self.say(f"[{'ŞANS' if deck_name == 'chance' else 'SANDIK'}] {card.text}")
        a = card.action
        if a == "goto":
            self.move_to(player, card.arg)
            self.land(player, dice_total)
        elif a == "back":
            self.move_to(player, (player.pos - card.arg) % 40, collect=False)
            self.land(player, dice_total)
        elif a == "rr":
            self.move_to(player, NEXT_RAILROAD[player.pos])
            self.land(player, dice_total, card="rr")
        elif a == "util":
            self.move_to(player, NEXT_UTILITY[player.pos])
            self.land(player, sum(self.roll_dice()), card="util")
        elif a == "jail":
            self.send_to_jail(player)
        elif a == "jailfree":
            player.jail_cards.append(deck_name)
        elif a == "money":
            if card.arg >= 0:
                player.cash += card.arg
            else:
                self.pay(player, -card.arg)
        elif a == "repairs":
            hc, htl = card.arg
            levels = [self.houses[i] for i in self.props_of(player) if i in self.houses]
            houses = sum(h for h in levels if h < MAX_BUILD)
            hotels = levels.count(MAX_BUILD)
            self.pay(player, houses * hc + hotels * htl)
        elif a == "pay_each":
            for other in self.active_players():
                if other is not player and not player.bankrupt:
                    self.pay(player, card.arg, other)
        elif a == "collect_each":
            for other in self.active_players():
                if other is not player and not player.bankrupt:
                    self.pay(other, card.arg, player)

    # --- tur akışı -------------------------------------------------------
    def _release(self, player):
        player.in_jail = False
        player.jail_turns = 0

    def _jail_pre_roll(self, player):
        choice = self.ui.choose_jail(self, player) if player.human else None
        if choice is None:  # AI varsayılanı
            choice = "card" if player.jail_cards else "roll"
        if choice == "card" and player.jail_cards:
            src = player.jail_cards.pop(0)
            self.decks[src].append(JAILFREE_CARD[src])  # kart desteye döner
            self._release(player)
            self.say(f"{player.name} Kodesten Çık kartını kullandı")
        elif choice == "pay" and player.cash >= JAIL_FINE:
            self.pay(player, JAIL_FINE)
            self._release(player)
            self.say(f"{player.name} {JAIL_FINE}$ ödeyip kodesten çıktı")

    def play_turn(self, player):
        """Bir oyuncunun tam turu (çift zar tekrarı dahil)."""
        if player.bankrupt:
            return
        self.ui.on_turn_start(self, player)
        if player.human:
            self.ui.build_phase(self, player)
        else:
            self.ai_manage(player)
        if player.in_jail:
            self._jail_pre_roll(player)
        doubles = 0
        while not player.bankrupt:
            d1, d2 = self.roll_dice()
            self.ui.on_dice(self, player, d1, d2)
            total, is_double = d1 + d2, d1 == d2
            self.say(f"{player.name} zar: {d1}+{d2}={total}" + (" ÇİFT!" if is_double else ""))
            if player.in_jail:
                if is_double:
                    self._release(player)
                    self.say(f"{player.name} çift atarak kodesten çıktı")
                    self.advance(player, total)
                    self.land(player, total)
                    return
                player.jail_turns += 1
                if player.jail_turns >= 3:
                    self.say(f"{player.name} 3. turda {JAIL_FINE}$ ödemek zorunda")
                    if self.pay(player, JAIL_FINE):
                        self._release(player)
                        self.advance(player, total)
                        self.land(player, total)
                return
            if is_double:
                doubles += 1
                if doubles == 3:
                    self.say(f"{player.name} 3 kez üst üste çift attı!")
                    self.send_to_jail(player)
                    return
            self.advance(player, total)
            self.land(player, total)
            if player.bankrupt or player.in_jail or not is_double:
                return

    def next_turn(self):
        """Sıradaki oyuncuyu oynatır, sırayı ilerletir."""
        player = self.players[self.current]
        self.play_turn(player)
        self._advance_current()
        return player

    def _advance_current(self):
        for _ in range(len(self.players)):
            self.current = (self.current + 1) % len(self.players)
            if self.current == 0:
                self.round_no += 1
            if not self.players[self.current].bankrupt:
                return

    def run_to_end(self, max_rounds=500):
        while not self.over and self.round_no <= max_rounds:
            self.next_turn()
        return self.winner
