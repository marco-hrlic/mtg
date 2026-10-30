"""London-mulligan policies for the Sisay goldfish.

All policies share the same mechanics (see Policy.run): draw 7, decide, first mulligan free
(4-player Commander), then each further mulligan costs one card, bottomed after the final draw.
Policies differ in keep() and bottom().

  A  Heuristic     real early colored mana, acceleration, plausible T2 Sisay or T3 Cradle
  B  Fast Sisay    Sisay castable by T2 (or T3 with an activation target) above all else
  C  Cradle-first  creature density + Cradle access, accepts a T3 Sisay
  D  Rollout       plays each candidate keep (and each bottoming choice) forward with the pilot
                   and keeps when the estimate beats the expected value of mulliganing

Utility used by D and by the report: 1.0*P(protected lethal<=T4) + 0.35*P(lethal<=T4)
+ 0.15*P(infinite<=T4). Weights are a starting heuristic; raw milestone rates are reported too.
"""
import random

from engine import Game

ROCKS_FREE = ("Lotus Petal", "Elvish Spirit Guide", "Chrome Mox", "Mox Diamond", "Mox Amber")
ROCKS_ONE = ("Sol Ring", "Mana Vault")
DORK1 = ("Llanowar Elves", "Fyndhorn Elves", "Elvish Mystic", "Birds of Paradise", "Avacyn's Pilgrim", "Arbor Elf",
         "Magus of the Candelabra", "Quirion Ranger", "Utopia Sprawl", "Wild Growth")
CRADLE_ACCESS = ("Gaea's Cradle", "Crop Rotation", "Sylvan Scrying", "Knight of the Reliquary")
ENGINE = ("Ashaya, Soul of the Wild", "Emiel the Blessed", "Hope Tender", "Magus of the Candelabra",
          "Quirion Ranger", "Scryb Ranger", "Flash Thompson, Spider-Fan", "Selvala, Heart of the Wilds")
TUTORS = ("Green Sun's Zenith", "Natural Order", "Summoner's Pact", "Chord of Calling", "Eldritch Evolution",
          "Eladamri's Call", "Nature's Rhythm", "Worldly Tutor", "Sylvan Tutor", "Survival of the Fittest",
          "Finale of Devastation", "Formidable Speaker", "Ranger-Captain of Eos")
PROTECTION = ("Silence", "Veil of Summer", "Grand Abolisher", "Voice of Victory", "Jennifer Walters",
              "Ranger-Captain of Eos")


def utility(r):
    ok4 = r["win_turn"] is not None and r["win_turn"] <= 4
    return (1.0 * (ok4 and bool(r["protected"])) + 0.35 * ok4
            + 0.15 * (r["milestones"].get("infinite", 99) <= 4))


def features(hand):
    names = [c.name for c in hand]
    lands = [c for c in hand if c.is_("land")]
    n_land = len(lands)
    # colors a land can produce on its own ("A" = either)
    land_cols = set()
    for c in lands:
        if c.has("fetch") or c.has("pathway"):
            land_cols.add("A")
        for u in c.mana:
            land_cols.add(u)
    green_land = bool(land_cols & {"G", "A"})
    white_land = bool(land_cols & {"W", "A"})
    nonland_colored = [c for c in hand if not c.is_("land") and c.colors]
    # real payable fast mana
    fast = 0
    if "Lotus Petal" in names:
        fast += 1
    if "Elvish Spirit Guide" in names:
        fast += 1
    if "Mox Diamond" in names and n_land >= 2:
        fast += 1
    if "Chrome Mox" in names and len(nonland_colored) >= 2:
        fast += 1
    rocks1 = sum(1 for n in ROCKS_ONE if n in names)
    dorks = sum(1 for n in DORK1 if n in names and green_land)
    t1_mana = min(n_land, 1) + fast
    # T2: two lands + rocks cast T1 + dorks cast T1 (at most t1_mana of them)
    t2_mana = min(n_land, 2) + fast + (2 * rocks1 if t1_mana >= 1 else 0) + min(dorks, t1_mana)
    t3_mana = min(n_land, 3) + fast + 2 * rocks1 + dorks
    creatures = sum(1 for c in hand if c.is_("creature"))
    return {
        "lands": n_land, "green": green_land, "white": white_land, "fast": fast, "rocks1": rocks1,
        "dorks": dorks, "t1": t1_mana, "t2": t2_mana, "t3": t3_mana, "creatures": creatures,
        "cradle_access": sum(1 for n in CRADLE_ACCESS if n in names),
        "cradle": "Gaea's Cradle" in names,
        "engine": sum(1 for n in ENGINE if n in names),
        "tutors": sum(1 for n in TUTORS if n in names),
        "protection": sum(1 for n in PROTECTION if n in names),
        "dead": sum(1 for c in hand if c.has("dead")),
        "any_w": white_land or "Birds of Paradise" in names or "Avacyn's Pilgrim" in names
        or "Lotus Petal" in names or ("Mox Diamond" in names and n_land >= 2) or "Chrome Mox" in names,
    }


def heuristic_bottom(game, hand, n):
    """Bottom n cards: dead cards, then surplus lands beyond 3, then the pilot's worst card."""
    hand = list(hand)
    out = []
    for _ in range(n):
        lands = [c for c in hand if c.is_("land")]
        dead = [c for c in hand if c.has("dead")]
        if dead:
            pick = dead[0]
        elif len(lands) > 3:
            pick = max(lands, key=lambda c: (c.mana == ("C",), c.name in ("Gaea's Cradle",)))
        else:
            saved = game.hand
            game.hand = hand
            pick = game._worst_card() or hand[-1]
            game.hand = saved
        hand.remove(pick)
        out.append(pick)
    return out


class Policy:
    name = "base"

    def keep(self, game, hand, size):
        raise NotImplementedError

    def bottom(self, game, hand, n):
        return heuristic_bottom(game, hand, n)

    def run(self, game):
        free_used = False
        size = 7
        while True:
            game.library += game.hand
            game.hand = []
            game.shuffle()
            game.draw(7)
            if size <= 4 or self.keep(game, game.hand, size):
                break
            game.result["mulligans"] += 1
            if not free_used:
                free_used = True
            else:
                size -= 1
        for card in self.bottom(game, game.hand, 7 - size):
            game.hand.remove(card)
            game.library.insert(0, card)


class Heuristic(Policy):
    name = "A heuristic"

    def keep(self, game, hand, size):
        f = features(hand)
        if f["lands"] == 0 or not f["green"]:
            return False
        if f["lands"] > 4:
            return False
        sources = f["lands"] + f["fast"] + f["rocks1"] + f["dorks"]
        if size == 7:
            return sources >= 3 and (f["t2"] >= 3 or f["engine"] + f["tutors"] >= 1) and f["dead"] <= 2
        if size == 6:
            return sources >= 2
        return sources >= 2 or f["lands"] >= 2


class FastSisay(Policy):
    name = "B fast Sisay"

    def keep(self, game, hand, size):
        f = features(hand)
        if f["lands"] == 0 or not f["green"]:
            return False
        sisay_t2 = f["t2"] >= 4 and f["any_w"]
        sisay_t3 = f["t3"] >= 4 and f["any_w"]
        if size == 7:
            return sisay_t2 or (sisay_t3 and f["engine"] + f["tutors"] + f["cradle_access"] >= 1)
        if size == 6:
            return sisay_t3
        return f["t3"] >= 3


class CradleFirst(Policy):
    name = "C Cradle-first"

    def keep(self, game, hand, size):
        f = features(hand)
        if f["lands"] == 0 or not f["green"]:
            return False
        bodies = f["dorks"] + f["creatures"]
        access = f["cradle_access"] >= 1 or f["t3"] >= 4  # Sisay by T3 finds Cradle
        if size == 7:
            return bodies >= 2 and access and f["lands"] <= 4
        if size == 6:
            return bodies >= 1 and (access or f["t2"] >= 3)
        return f["lands"] + f["dorks"] + f["fast"] >= 2


class Rollout(Policy):
    """Keep when the rollout estimate of this hand beats the expected value of mulliganing.
    V[size] (value of mulliganing down to `size` kept cards) is estimated once per deck."""
    name = "D rollout"

    def __init__(self, deck, rollouts=5, calib_hands=120, seed=99, islands=0, on_draw=False):
        self.deck = [c for c in deck if c.name != "Captain Sisay"]
        self.R = rollouts
        self.islands = islands
        self.on_draw = on_draw
        self.rng = random.Random(seed)
        self.V = {}
        self.decisions = []  # (hand names, size, est_keep, est_mull, kept)
        self._calibrate(calib_hands)

    def estimate(self, hand, rollouts=None):
        R = rollouts or self.R
        total = 0.0
        for _ in range(R):
            g = Game(self.deck + [hand[0]] * 0, random.Random(self.rng.random()), islands=self.islands,
                     on_draw=self.on_draw)
            total += utility(g.play_from(list(hand)))
        return total / R

    def best_bottom(self, hand, n):
        hand = list(hand)
        for _ in range(n):
            scores = []
            for c in {c.name: c for c in hand}.values():
                trial = list(hand)
                trial.remove(c)
                scores.append((self.estimate(trial, max(2, self.R - 2)), c))
            _, pick = max(scores, key=lambda t: t[0])
            hand.remove(pick)
        return hand

    def _calibrate(self, m):
        """V[k] = expected utility when you have decided to mulligan to a k-card hand and then play D."""
        self.V[4] = 0.0
        for k in (4, 5, 6, 7):
            vals = []
            for _ in range(m):
                lib = list(self.deck)
                self.rng.shuffle(lib)
                hand = lib[:7]
                kept = self.best_bottom(hand, 7 - k) if k < 7 else hand
                u = self.estimate(kept)
                vals.append(u if k == 4 else max(u, self.V[k - 1]))
            self.V[k] = sum(vals) / len(vals)

    def keep(self, game, hand, size):
        est = self.estimate(hand)
        # free mulligan: next hand is a 7; otherwise next is size-1
        mull_value = self.V[7] if game.result["mulligans"] == 0 else self.V[size - 1]
        keep = est >= mull_value or size <= 4
        self.decisions.append(([c.name for c in hand], size, est, mull_value, keep))
        return keep

    def bottom(self, game, hand, n):
        if n == 0:
            return []
        kept = self.best_bottom(hand, n)
        return [c for c in hand if c not in kept] if len(kept) == len(hand) - n else \
            [c for c in list(hand) if not _remove_once(kept, c)]


def _remove_once(lst, c):
    if c in lst:
        lst.remove(c)
        return True
    return False


POLICIES = {"A": Heuristic, "B": FastSisay, "C": CradleFirst, "D": Rollout}
