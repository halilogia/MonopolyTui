"""Birim testleri: tahta verisi, oyun mantığı, Monte Carlo istatistik doğruluğu, renkler, çizim."""
import unittest

import colors as C
import renderer as R
from board_data import (
    CHANCE_CARDS, CHEST_CARDS, GROUP_TILES, NEXT_RAILROAD, NEXT_UTILITY, RAILROADS, TILES,
    UTILITIES, Card, Group, Kind,
)
from monopoly_game import Game
from monte_carlo import group_roi, roi_table, run_simulation, simulate_chunk

# Tüm istatistik testleri tek seferlik, tohumlu bir koşuyu paylaşır.
_SIM = None


def sim():
    global _SIM
    if _SIM is None:
        _SIM = run_simulation(games=20_000, turns=50, seed=12345, workers=1)
    return _SIM


def new_game(n=2):
    return Game([(f"P{i}", False) for i in range(n)], seed=1)


def rig(game, deck, card):
    game.decks[deck].insert(0, card)


class TestBoardData(unittest.TestCase):
    def test_forty_tiles_in_order(self):
        self.assertEqual(len(TILES), 40)
        self.assertEqual([t.idx for t in TILES], list(range(40)))

    def test_corner_and_special_squares(self):
        self.assertEqual(TILES[0].kind, Kind.GO)
        self.assertEqual(TILES[10].kind, Kind.JAIL)
        self.assertEqual(TILES[20].kind, Kind.FREE_PARKING)
        self.assertEqual(TILES[30].kind, Kind.GO_TO_JAIL)
        self.assertEqual([t.tax for t in (TILES[4], TILES[38])], [200, 100])

    def test_counts_of_kinds(self):
        kinds = [t.kind for t in TILES]
        self.assertEqual(kinds.count(Kind.PROPERTY), 22)
        self.assertEqual(kinds.count(Kind.RAILROAD), 4)
        self.assertEqual(kinds.count(Kind.UTILITY), 2)
        self.assertEqual(kinds.count(Kind.CHANCE), 3)
        self.assertEqual(kinds.count(Kind.CHEST), 3)

    def test_group_sizes(self):
        sizes = {g: len(v) for g, v in GROUP_TILES.items()}
        self.assertEqual(sizes[Group.BROWN], 2)
        self.assertEqual(sizes[Group.DARK_BLUE], 2)
        for g in (Group.LIGHT_BLUE, Group.PINK, Group.ORANGE, Group.RED, Group.YELLOW, Group.GREEN):
            self.assertEqual(sizes[g], 3)

    def test_total_price_matches_classic_board(self):
        self.assertEqual(sum(t.price for t in TILES if t.kind is Kind.PROPERTY), 4590)
        self.assertEqual(sum(t.price for t in TILES if t.ownable), 5690)

    def test_rent_tables_increase(self):
        for t in TILES:
            if t.kind is Kind.PROPERTY:
                self.assertEqual(len(t.rents), 6)
                self.assertEqual(list(t.rents), sorted(t.rents))

    def test_cards_decks_are_16(self):
        self.assertEqual(len(CHANCE_CARDS), 16)
        self.assertEqual(len(CHEST_CARDS), 16)

    def test_nearest_lookup_tables(self):
        self.assertEqual(NEXT_RAILROAD[7], 15)
        self.assertEqual(NEXT_RAILROAD[36], 5)
        self.assertEqual(NEXT_UTILITY[22], 28)
        self.assertEqual(NEXT_UTILITY[36], 12)
        self.assertEqual(RAILROADS, (5, 15, 25, 35))
        self.assertEqual(UTILITIES, (12, 28))


class TestGameRules(unittest.TestCase):
    def test_movement_and_go_salary(self):
        g = new_game()
        p = g.players[0]
        p.pos = 38
        g.advance(p, 4)
        self.assertEqual(p.pos, 2)
        self.assertEqual(p.cash, 1500 + 200)

    def test_buy_property_and_rent(self):
        g = new_game()
        a, b = g.players
        a.pos = 1
        g.land(a, 5)
        self.assertIs(g.owner[1], a)
        b.pos = 1
        g.land(b, 5)
        self.assertEqual(b.cash, 1500 - 2)
        self.assertEqual(a.cash, 1500 - 60 + 2)

    def test_monopoly_doubles_base_rent(self):
        g = new_game()
        a = g.players[0]
        g.owner[1] = g.owner[3] = a
        self.assertEqual(g.rent_for(1), 4)

    def test_railroad_and_utility_rent(self):
        g = new_game()
        a = g.players[0]
        g.owner[5] = a
        self.assertEqual(g.rent_for(5), 25)
        g.owner[15] = a
        self.assertEqual(g.rent_for(5), 50)
        g.owner[12] = a
        self.assertEqual(g.rent_for(12, 8), 32)
        g.owner[28] = a
        self.assertEqual(g.rent_for(12, 8), 80)

    def test_building_requires_monopoly_and_is_even(self):
        g = new_game()
        a = g.players[0]
        g.owner[1] = a
        self.assertFalse(g.can_build(a, 1))
        g.owner[3] = a
        self.assertTrue(g.build(a, 1))
        self.assertFalse(g.can_build(a, 1))  # eşit dağılım: önce Baltic
        self.assertTrue(g.build(a, 3))
        self.assertEqual(g.rent_for(1), 10)
        self.assertEqual(a.cash, 1500 - 100)

    def test_hotel_rent_and_cap(self):
        g = new_game()
        a = g.players[0]
        g.owner[1] = g.owner[3] = a
        a.cash = 10_000
        for _ in range(5):
            g.build(a, 1)
            g.build(a, 3)
        self.assertEqual(g.houses[1], 5)
        self.assertFalse(g.can_build(a, 1))
        self.assertEqual(g.rent_for(1), 250)

    def test_income_and_luxury_tax(self):
        g = new_game()
        p = g.players[0]
        p.pos = 4
        g.land(p, 3)
        p.pos = 38
        g.land(p, 3)
        self.assertEqual(p.cash, 1500 - 300)

    def test_go_to_jail_square(self):
        g = new_game()
        p = g.players[0]
        p.pos = 30
        g.land(p, 3)
        self.assertTrue(p.in_jail)
        self.assertEqual(p.pos, 10)

    def test_three_doubles_send_to_jail(self):
        g = new_game()
        p = g.players[0]
        g.dice_queue.extend([(1, 1), (2, 2), (3, 3)])
        g.play_turn(p)
        self.assertTrue(p.in_jail)
        self.assertEqual(p.pos, 10)

    def test_double_gives_extra_roll_then_ends(self):
        g = new_game()
        p = g.players[0]
        p.pos = 24
        g.dice_queue.extend([(1, 1), (1, 2)])
        g.play_turn(p)
        self.assertEqual(p.pos, 29)  # 24 + 2 + 3
        self.assertFalse(g.dice_queue)

    def test_jail_third_failure_forces_fine(self):
        g = new_game()
        p = g.players[0]
        g.send_to_jail(p)
        g.owner[15] = p  # inilen kareyi satın almasın
        for roll in [(1, 2), (1, 3), (2, 3)]:
            g.dice_queue.append(roll)
            g.play_turn(p)
        self.assertFalse(p.in_jail)
        self.assertEqual(p.cash, 1500 - 50)
        self.assertEqual(p.pos, 15)  # 10 + 5

    def test_jail_leaves_on_doubles_without_extra_turn(self):
        g = new_game()
        p = g.players[0]
        g.send_to_jail(p)
        g.dice_queue.extend([(2, 2), (3, 4)])
        g.play_turn(p)
        self.assertFalse(p.in_jail)
        self.assertEqual(p.pos, 14)
        self.assertEqual(len(g.dice_queue), 1)


class TestCards(unittest.TestCase):
    def test_advance_to_go_collects(self):
        g = new_game()
        p = g.players[0]
        p.pos = 7
        rig(g, "chance", CHANCE_CARDS[0])
        g.draw_card(p, "chance", 5)
        self.assertEqual((p.pos, p.cash), (0, 1700))

    def test_illinois_card(self):
        g = new_game()
        p = g.players[0]
        p.pos = 36
        rig(g, "chance", CHANCE_CARDS[1])
        g.draw_card(p, "chance", 5)
        self.assertEqual(p.pos, 24)
        self.assertEqual(p.cash, 1500 + 200 - 240)  # GO'dan geçti, Illinois'i aldı

    def test_nearest_railroad_double_rent(self):
        g = new_game()
        a, b = g.players
        g.owner[15] = a
        b.pos = 7
        rig(g, "chance", CHANCE_CARDS[4])
        g.draw_card(b, "chance", 5)
        self.assertEqual(b.pos, 15)
        self.assertEqual(b.cash, 1500 - 50)

    def test_nearest_utility_ten_times_dice(self):
        g = new_game()
        a, b = g.players
        g.owner[28] = a
        b.pos = 22
        g.dice_queue.append((3, 4))
        rig(g, "chance", CHANCE_CARDS[3])
        g.draw_card(b, "chance", 5)
        self.assertEqual(b.pos, 28)
        self.assertEqual(b.cash, 1500 - 70)

    def test_back_three_squares(self):
        g = new_game()
        p = g.players[0]
        p.pos = 22
        rig(g, "chance", CHANCE_CARDS[8])
        g.draw_card(p, "chance", 5)
        self.assertEqual(p.pos, 19)

    def test_back_three_from_36_lands_on_chest(self):
        g = new_game()
        p = g.players[0]
        p.pos = 36
        rig(g, "chance", CHANCE_CARDS[8])
        rig(g, "chest", Card("test", "money", 10))
        g.draw_card(p, "chance", 5)
        self.assertEqual((p.pos, p.cash), (33, 1510))

    def test_go_to_jail_card(self):
        g = new_game()
        p = g.players[0]
        rig(g, "chest", CHEST_CARDS[5])
        g.draw_card(p, "chest", 5)
        self.assertTrue(p.in_jail)

    def test_get_out_of_jail_card_cycle(self):
        g = new_game()
        p = g.players[0]
        before = len(g.decks["chance"])
        rig(g, "chance", CHANCE_CARDS[7])
        g.draw_card(p, "chance", 5)
        self.assertEqual(p.jail_cards, ["chance"])
        self.assertEqual(len(g.decks["chance"]), before)
        held = len(g.decks["chance"])
        g.send_to_jail(p)
        g.dice_queue.append((1, 2))
        g.play_turn(p)
        self.assertFalse(p.in_jail)
        self.assertEqual(len(g.decks["chance"]), held + 1)  # kart desteye döndü

    def test_collect_from_each_player(self):
        g = new_game(3)
        p = g.players[0]
        rig(g, "chest", CHEST_CARDS[8])
        g.draw_card(p, "chest", 5)
        self.assertEqual(p.cash, 1520)
        self.assertEqual(g.players[1].cash, 1490)

    def test_repairs_card(self):
        g = new_game()
        a = g.players[0]
        g.owner[1] = g.owner[3] = a
        g.houses[1], g.houses[3] = 2, 5
        rig(g, "chance", CHANCE_CARDS[10])
        g.draw_card(a, "chance", 5)
        self.assertEqual(a.cash, 1500 - (2 * 25 + 100))


class TestBankruptcy(unittest.TestCase):
    def test_bankrupt_transfers_assets(self):
        g = new_game()
        a, b = g.players
        a.cash = 10
        g.owner[1] = a
        g.owner[39] = b
        g.houses[39] = 0
        self.assertFalse(g.pay(a, 5000, b))
        self.assertTrue(a.bankrupt)
        self.assertIs(g.owner[1], b)

    def test_raise_cash_mortgages_before_bankruptcy(self):
        g = new_game()
        a, b = g.players
        a.cash = 0
        g.owner[39] = a
        self.assertTrue(g.pay(a, 150, b))
        self.assertIn(39, g.mortgaged)
        self.assertEqual(g.rent_for(39), 0)

    def test_winner_detected(self):
        g = new_game()
        g.players[0].bankrupt = True
        self.assertTrue(g.over)
        self.assertIs(g.winner, g.players[1])

    def test_full_ai_game_runs_cleanly(self):
        for seed in range(5):
            g = Game([("A", False), ("B", False), ("C", False)], seed=seed)
            g.run_to_end(max_rounds=200)
            for p in g.players:
                self.assertGreaterEqual(p.cash, 0)
                self.assertTrue(0 <= p.pos < 40)


class TestMonteCarlo(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(sim().probs), 1.0, places=9)

    def test_jail_is_most_visited_near_six_percent(self):
        r = sim()
        self.assertEqual(r.rank_of(10), 1)
        self.assertTrue(0.055 < r.probs[10] < 0.070, r.probs[10])

    def test_go_to_jail_square_is_never_resting_place(self):
        self.assertEqual(sim().counts[30], 0)

    def test_illinois_is_most_landed_property(self):
        r = sim()
        self.assertEqual(r.top(1, only_ownable=True)[0][0], 24)
        props = [i for i, _ in r.top(40) if TILES[i].kind is Kind.PROPERTY]
        self.assertEqual(props[0], 24)

    def test_chance_squares_below_uniform(self):
        for i in (7, 22, 36):
            self.assertLess(sim().probs[i], 0.025)

    def test_deterministic_with_seed(self):
        a = simulate_chunk((200, 20, 7))
        b = simulate_chunk((200, 20, 7))
        self.assertEqual(a, b)

    def test_parallel_matches_total_volume(self):
        r = run_simulation(games=400, turns=10, seed=3, workers=2)
        self.assertEqual(r.games, 400)
        self.assertEqual(sum(r.counts) + 0, r.total_landings)
        self.assertGreater(r.rolls, 4000)

    def test_independent_seeds_agree(self):
        other = run_simulation(games=20_000, turns=50, seed=999, workers=1)
        for i in (10, 24, 19, 0):
            self.assertAlmostEqual(sim().probs[i], other.probs[i], delta=0.003)

    def test_roi_orange_group_beats_cheap_groups(self):
        ranking = [g for g, *_ in group_roi(sim())]
        self.assertEqual(ranking[0], Group.ORANGE)
        self.assertGreater(ranking.index(Group.BROWN), ranking.index(Group.RED))

    def test_new_york_top_roi_in_orange_and_overall_top3(self):
        rows = sorted(roi_table(sim()), key=lambda r: -r.roi_pct)
        self.assertIn(19, [r.idx for r in rows[:3]])
        orange = [r for r in rows if r.group is Group.ORANGE]
        self.assertEqual(orange[0].idx, 19)


class TestColorsAndRenderer(unittest.TestCase):
    def test_heat_gradient_endpoints(self):
        self.assertEqual(C.heat_color(0.0), (12, 24, 110))
        self.assertEqual(C.heat_color(1.0), (235, 40, 15))
        self.assertEqual(C.heat_color(0.33), (0, 215, 230))
        self.assertEqual(len(C.heat_gradient(16)), 16)

    def test_truecolor_escape_format(self):
        self.assertEqual(C.fg(1, 2, 3), "\x1b[38;2;1;2;3m")
        self.assertEqual(C.bg(4, 5, 6), "\x1b[48;2;4;5;6m")

    def test_visible_len_and_pad_ignore_ansi(self):
        s = C.paint("abc", (1, 2, 3))
        self.assertEqual(C.visible_len(s), 3)
        self.assertEqual(C.visible_len(C.pad(s, 10)), 10)
        self.assertEqual(C.visible_len(C.pad(s * 5, 10)), 10)

    def test_board_frames_have_exact_geometry(self):
        r = sim()
        for frame in (R.heat_frame(r), R.game_frame(new_game(), new_game().players[0], (3, 4), "x")):
            self.assertEqual(len(frame), R.BOARD_H + 2)
            self.assertTrue(all(C.visible_len(l) == R.BOARD_W for l in frame))

    def test_grid_positions_are_unique_border_cells(self):
        pos = {R.grid_pos(i) for i in range(40)}
        self.assertEqual(len(pos), 40)
        self.assertEqual(R.grid_pos(0), (10, 10))
        self.assertEqual(R.grid_pos(10), (10, 0))
        self.assertEqual(R.grid_pos(20), (0, 0))
        self.assertEqual(R.grid_pos(30), (0, 10))

    def test_analysis_page_confirms_core_facts(self):
        text = C.strip_ansi("\n".join(R.analysis_lines(sim())))
        self.assertNotIn("[SAPMA]", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
