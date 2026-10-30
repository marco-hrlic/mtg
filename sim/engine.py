"""Goldfish engine for the Captain Sisay deck.

The game is solitaire: no opponents, no interaction. Each turn the pilot
  1. asks the planner whether any combo line can be completed this turn,
  2. otherwise develops (land, fast mana, dorks, Sisay, combo pieces, tutors),
  3. asks the planner again with the new resources,
  4. uses Sisay / top-of-library tutors at end of turn to dig for missing pieces.

The planner is an abstraction, not a rules engine: for each line it enumerates
ways to get each missing piece onto the battlefield this turn (cast from hand,
Sisay, Green Sun's Zenith, Natural Order, ...), sums the mana, checks colors and
summoning sickness/haste, and accepts the cheapest assignment that fits.
"""
import random
from dataclasses import dataclass
from itertools import product

from cards import BY_NAME, COMMANDER

ASHAYA = "Ashaya, Soul of the Wild"
HOPE = "Hope Tender"
MAGUS = "Magus of the Candelabra"
CRADLE = "Gaea's Cradle"
NYKTHOS = "Nykthos, Shrine to Nyx"
SELVALA = "Selvala, Heart of the Wilds"
BLOOM = "Bloom Tender"
CUB = "Badgermole Cub"
EMIEL = "Emiel the Blessed"
FLASH = "Flash Thompson, Spider-Fan"
KAMAHL = "Kamahl, Fist of Krosa"
SISAY = COMMANDER
SPEAKER = "Formidable Speaker"
RANGERCAP = "Ranger-Captain of Eos"
ELDER = "Argothian Elder"
DRUID = "Devoted Druid"
VIZIER = "Vizier of Remedies"
MANTLE = "Umbral Mantle"
QUIRION = "Quirion Ranger"
SCRYB = "Scryb Ranger"
FANATIC = "Fanatic of Rhonas"
BALLISTA = "Walking Ballista"
EZURI = "Ezuri, Renegade Leader"
SATYR = "Voyaging Satyr"
ARBOR = "Arbor Elf"
YAVIMAYA = "Yavimaya, Cradle of Growth"
ANIMATE = "Animate Land"
VTOUCH = "Verdant Touch"
SHANG = "Shang-Chi, Master of Kung Fu"
HASTE_SOURCES = ("Concordant Crossroads", "Thousand-Year Elixir", "Shang-Chi, Master of Kung Fu")
GREAVES = "Lightning Greaves"

LAZY_TAGS = ("cradle", "nykthos", "selvala", "fanatic", "bloom", "satyr")


# ---------------------------------------------------------------- mana helpers

def feasible(colors, cost):
    gen, g, w = cost
    n_g = colors.count("G")
    n_w = colors.count("W")
    n_a = colors.count("A")
    return g <= n_g + n_a and w <= n_w + n_a and g + w <= n_g + n_w + n_a and g + w + gen <= len(colors)


def add_cost(*costs):
    return tuple(sum(c[i] for c in costs) for i in range(3))


ZERO = (0, 0, 0)


# ---------------------------------------------------------------- combo lines

@dataclass(frozen=True)
class Line:
    name: str
    pieces: tuple
    tappers: tuple
    startup: tuple
    kind: str            # "mana": infinite mana, needs an outlet. "win": wins by itself.
    check: object        # ctx -> bool
    haste_always: bool = False
    gives_w: bool = False
    untaps_sisay: bool = False  # Ashaya makes Sisay a land the engine can untap -> fetch every legend


def _cub_ok(need):
    # Cub lines need `need` other non-sick creatures to tap as Forests (Ashaya).
    def check(ctx):
        return ctx["tap_creatures"] - ctx["line_tappers"] >= need
    return check


LINES = [
    Line("Ashaya+Hope+Cradle", (ASHAYA, HOPE, CRADLE), (HOPE,), (1, 0, 0), "mana",
         lambda c: c["creatures"] >= 2, untaps_sisay=True),
    Line("Ashaya+Hope+Nykthos", (ASHAYA, HOPE, NYKTHOS), (HOPE,), (3, 0, 0), "mana",
         lambda c: c["devotion"] >= 4, untaps_sisay=True),
    Line("Ashaya+Hope+Selvala", (ASHAYA, HOPE, SELVALA), (HOPE, SELVALA), (1, 1, 0), "mana",
         lambda c: c["ashaya_power"] >= 3, gives_w=True, untaps_sisay=True),
    Line("Ashaya+Hope+Bloom", (ASHAYA, HOPE, BLOOM), (HOPE, BLOOM), (1, 0, 0), "mana",
         lambda c: c["w_perm"], gives_w=True, untaps_sisay=True),
    Line("Ashaya+Hope+Cub", (ASHAYA, HOPE, CUB), (HOPE,), (1, 0, 0), "mana", _cub_ok(1), untaps_sisay=True),
    Line("Ashaya+Magus+Cradle", (ASHAYA, MAGUS, CRADLE), (MAGUS,), (2, 0, 0), "mana",
         lambda c: c["creatures"] >= 3, untaps_sisay=True),
    Line("Ashaya+Magus+Nykthos", (ASHAYA, MAGUS, NYKTHOS), (MAGUS,), (4, 0, 0), "mana",
         lambda c: c["devotion"] >= 5, untaps_sisay=True),
    Line("Ashaya+Magus+Selvala", (ASHAYA, MAGUS, SELVALA), (MAGUS, SELVALA), (2, 1, 0), "mana",
         lambda c: c["ashaya_power"] >= 4, gives_w=True, untaps_sisay=True),
    Line("Ashaya+Magus+Cub", (ASHAYA, MAGUS, CUB), (MAGUS,), (3, 0, 0), "mana", _cub_ok(2), untaps_sisay=True),
    # Under Ashaya a Ranger is a Forest: it returns itself to hand to untap a creature, then is recast
    # as a new object, dodging "once each turn". No tap, so the Ranger needs no haste.
    Line("Ashaya+Quirion+Selvala", (ASHAYA, QUIRION, SELVALA), (SELVALA,), (0, 2, 0), "mana",
         lambda c: c["ashaya_power"] >= 3, gives_w=True, untaps_sisay=True),
    Line("Ashaya+Quirion+Fanatic", (ASHAYA, QUIRION, FANATIC), (FANATIC,), (0, 1, 0), "mana",
         lambda c: c["ashaya_power"] >= 4, untaps_sisay=True),
    Line("Ashaya+Quirion+Bloom", (ASHAYA, QUIRION, BLOOM), (BLOOM,), (0, 1, 0), "mana",
         lambda c: c["w_perm"], gives_w=True, untaps_sisay=True),
    Line("Ashaya+Quirion+Cub", (ASHAYA, QUIRION, CUB), (), (0, 1, 0), "mana", _cub_ok(2), untaps_sisay=True),
    Line("Ashaya+Scryb+Selvala", (ASHAYA, SCRYB, SELVALA), (SELVALA,), (1, 2, 0), "mana",
         lambda c: c["ashaya_power"] >= 4, gives_w=True, untaps_sisay=True),
    Line("Ashaya+Scryb+Fanatic", (ASHAYA, SCRYB, FANATIC), (FANATIC,), (1, 1, 0), "mana",
         lambda c: c["ashaya_power"] >= 4, untaps_sisay=True),
    # Ashaya + Hope Tender + Shang-Chi: Hope untaps itself and Shang-Chi for {1}; Shang-Chi makes 2 that only
    # pay for creature abilities (Hope, Sisay). Infinite Sisay activations fetch Selvala, which turns the same
    # engine into real mana. Shang-Chi grants haste to abilities, so neither Hope nor Sisay needs to be unsick.
    Line("Ashaya+Hope+Shang-Chi", (ASHAYA, HOPE, SHANG), (), (1, 0, 0), "mana",
         lambda c: c["sisay"] and c["selvala_reachable"] and c["ashaya_power"] >= 3, gives_w=True,
         untaps_sisay=True),
    Line("Ashaya+Argothian Elder", (ASHAYA, ELDER), (ELDER,), ZERO, "mana",
         lambda c: True, untaps_sisay=True),
    Line("Devoted Druid+Vizier", (DRUID, VIZIER), (DRUID,), ZERO, "mana", lambda c: True),
    Line("Selvala+Umbral Mantle", (SELVALA, MANTLE), (SELVALA,), (3, 1, 0), "mana",
         lambda c: c["max_power"] >= 4, gives_w=True),
    # Emiel lines work without Ashaya: Emiel is a 4/4 (turns on Fanatic, makes Selvala tap for 4,
    # 5 with Badgermole Cub). Each blink can also untap/re-buy Sisay -> every legend -> Kamahl.
    Line("Emiel+Flash+Selvala", (EMIEL, FLASH, SELVALA), (SELVALA,), (3, 1, 0), "mana",
         lambda c: c["max_power"] + c["cub"] >= 5, gives_w=True, untaps_sisay=True),
    Line("Emiel+Flash+Fanatic", (EMIEL, FLASH, FANATIC), (FANATIC,), (3, 0, 0), "mana",
         lambda c: True, untaps_sisay=True),
    Line("Emiel+Selvala+haste", (EMIEL, SELVALA), (SELVALA,), (3, 1, 0), "mana",
         lambda c: c["max_power"] + c["cub"] >= 5, haste_always=True, gives_w=True, untaps_sisay=True),
    Line("Emiel+Fanatic+haste", (EMIEL, FANATIC), (FANATIC,), (3, 0, 0), "mana",
         lambda c: True, haste_always=True, untaps_sisay=True),
    # Emiel + Flash + Gaea's Cradle as a creature: blinking Flash untaps Cradle. Cradle counts itself.
    # Animate Land / Verdant Touch need a Cradle that has been out since the turn began (or global haste);
    # Badgermole Cub's earthbend grants haste and its static adds G when the creature-Cradle taps.
    Line("Emiel+Flash+Cradle+Animate Land", (EMIEL, FLASH, CRADLE, ANIMATE), (), (3, 0, 0), "mana",
         lambda c: c["creatures"] + 1 >= 4 and (not c["cradle_fresh"] or c["haste"]), untaps_sisay=True),
    Line("Emiel+Flash+Cradle+Verdant Touch", (EMIEL, FLASH, CRADLE, VTOUCH), (), (3, 0, 0), "mana",
         lambda c: c["creatures"] + 1 >= 4 and (not c["cradle_fresh"] or c["haste"]), untaps_sisay=True),
    Line("Emiel+Flash+Cradle+Kamahl", (EMIEL, FLASH, CRADLE, KAMAHL), (), (3, 1, 0), "mana",
         lambda c: c["creatures"] + 1 >= 4 and (not c["cradle_fresh"] or c["haste"]), untaps_sisay=True),
    Line("Emiel+Flash+Cradle+Cub", (EMIEL, FLASH, CRADLE, CUB), (), (3, 0, 0), "mana",
         lambda c: c["creatures"] + 2 >= 4, untaps_sisay=True),
    # Emiel + Flash + a land-untapper: Flash untaps the creature, the creature untaps Cradle / Nykthos.
    Line("Emiel+Flash+Satyr+Cradle", (EMIEL, FLASH, SATYR, CRADLE), (SATYR,), (3, 0, 0), "mana",
         lambda c: c["creatures"] >= 4, untaps_sisay=True),
    Line("Emiel+Flash+Arbor Elf+Cradle", (EMIEL, FLASH, ARBOR, CRADLE, YAVIMAYA), (ARBOR,), (3, 0, 0), "mana",
         lambda c: c["creatures"] >= 4, untaps_sisay=True),
    Line("Emiel+Flash+Hope+Cradle", (EMIEL, FLASH, HOPE, CRADLE), (HOPE,), (4, 0, 0), "mana",
         lambda c: c["creatures"] >= 5, untaps_sisay=True),
    Line("Emiel+Flash+Magus+Cradle", (EMIEL, FLASH, MAGUS, CRADLE), (MAGUS,), (4, 0, 0), "mana",
         lambda c: c["creatures"] >= 5, untaps_sisay=True),
    Line("Emiel+Flash+Satyr+Nykthos", (EMIEL, FLASH, SATYR, NYKTHOS), (SATYR,), (5, 0, 0), "mana",
         lambda c: c["devotion"] >= 6, untaps_sisay=True),
]
LINE_BY_NAME = {l.name: l for l in LINES}


@dataclass
class Opt:
    cost: tuple
    uses: frozenset
    enter: object  # Card entering the battlefield this turn, or None if already there
    how: str


# ---------------------------------------------------------------- game state

class Perm:
    __slots__ = ("card", "sick", "tapped", "choice")

    def __init__(self, card, sick=True):
        self.card = card
        self.sick = sick
        self.tapped = False
        self.choice = None


PROTECTION_BF = ("Grand Abolisher", "Voice of Victory", "Jennifer Walters", "Boromir, Warden of the Tower",
                 "Ranger-Captain of Eos")
PROTECTION_HAND = {"Silence": (0, 0, 1), "Veil of Summer": (0, 1, 0)}
BURST = {"Vitalize": (0, 1, 0), "Emerald Charm": (0, 1, 0)}


class Game:
    def __init__(self, deck, rng, log=False, max_turns=8, policy=None, islands=0, on_draw=False):
        self.rng = rng
        self.policy = policy          # mulligan policy object (see mulligan.py); None = built-in heuristic
        self.islands = islands        # opposing Islands for Carpet of Flowers
        self.on_draw = on_draw        # not the starting player: Gemstone Caverns may start in play
        self.carpet_used = False
        self.sisay_acts_turn = 0
        self.ms = {}                  # milestones: name -> earliest turn
        self.deck = [c for c in deck if c.name != SISAY]
        self.library = list(self.deck)
        rng.shuffle(self.library)
        self.hand = []
        self.bf = []
        self.gy = []
        self.command = [BY_NAME[SISAY]]
        self.turn = 0
        self.land_drop = False
        self.floating = []
        self.spells_cast = 0
        self.log_on = log
        self.logs = []
        self.max_turns = max_turns
        self.result = {"win_turn": None, "line": None, "uses": (), "noout_turn": None,
                       "noout_line": None, "mulligans": 0, "hand_size": 7, "protected": None,
                       "milestones": self.ms, "fail": None, "spare_mana": 0}

    def mark(self, name):
        if name not in self.ms:
            self.ms[name] = self.turn

    # ------------------------------------------------------------ utilities
    def log(self, msg):
        if self.log_on:
            self.logs.append(f"T{self.turn}: {msg}")

    def on_bf(self, name):
        return any(p.card.name == name for p in self.bf)

    def perm(self, name):
        for p in self.bf:
            if p.card.name == name:
                return p
        return None

    def has_tag(self, tag):
        return any(p.card.has(tag) for p in self.bf)

    def in_hand(self, name):
        return any(c.name == name for c in self.hand)

    def hand_card(self, name):
        for c in self.hand:
            if c.name == name:
                return c
        return None

    def creatures(self):
        return [p for p in self.bf if p.card.is_("creature")]

    def haste_active(self):
        return any(p.card.name in HASTE_SOURCES for p in self.bf)

    def ashaya_on(self):
        return self.on_bf(ASHAYA)

    def n_lands(self):
        if self.ashaya_on():
            return sum(1 for p in self.bf if p.card.is_("land") or p.card.is_("creature"))
        return sum(1 for p in self.bf if p.card.is_("land"))

    def max_power(self):
        best = 0
        for p in self.creatures():
            pw = self.n_lands() if p.card.name == ASHAYA else p.card.power
            best = max(best, pw)
        return best

    def devotion(self):
        return sum(p.card.gpips for p in self.bf)

    def forest_on(self):
        lands = [p for p in self.bf if p.card.is_("land")]
        if any(p.card.has("yavimaya") for p in lands) and lands:
            return True
        return any(p.card.forest for p in lands)

    def w_perm(self):
        return any("W" in p.card.colors for p in self.bf if not p.card.is_("land"))

    def has_w_source(self):
        return any(u in ("W", "A") for p in self.bf for u in self.units_of(p, ignore_tapped=True))

    def can_tap(self, p):
        if p.tapped:
            return False
        if p.card.is_("creature") and p.sick and not self.haste_active():
            return False
        return True

    # ------------------------------------------------------------ mana
    def units_of(self, p, ignore_tapped=False):
        c = p.card
        if p.tapped and not ignore_tapped:
            return []
        if c.has("wall"):
            return ["G"]
        if c.is_("creature"):
            if not ignore_tapped and not self.can_tap(p):
                return []
            if c.has("dork"):
                if c.has("bloom"):
                    u = ["G"] + (["W"] if self.w_perm() else [])
                elif c.has("fanatic"):
                    u = ["G"] * 4 if self.max_power() >= 4 else ["G"]
                elif c.has("selvala"):
                    x = self.max_power()
                    u = ["A"] * (x - 1) if x >= 2 else []
                elif c.has("satyr"):
                    u = ["G"] * (len(self.creatures()) if self.on_bf(CRADLE) else 1)
                elif c.has("arbor"):
                    u = ["G"] if self.forest_on() else []
                else:
                    u = list(c.mana)
            elif self.ashaya_on():
                u = ["G"]
            else:
                u = []
            if u and self.on_bf(CUB):
                u = u + ["G"]
            return u
        if c.is_("land"):
            if c.has("cradle"):
                return ["G"] * len(self.creatures())
            if c.has("nykthos"):
                d = self.devotion()
                return ["G"] * (d - 2) if d - 2 >= 2 else ["C"]
            if c.has("pathway"):
                return [p.choice or "G"]
            return list(c.mana)
        if c.has("amber"):
            return ["A"] if any(q.card.legendary and q.card.is_("creature") for q in self.bf) else []
        if c.has("imprint"):
            return [p.choice] if p.choice else []
        if c.has("aura"):
            return list(c.mana) if self.forest_on() else []
        if c.name == "Fal'Cie Paradise":  # Carpet of Flowers: X mana of one color, X = opposing Islands
            return [] if self.carpet_used or self.islands == 0 else ["A"] * self.islands
        return list(c.mana)

    def _pref(self, p):
        if p.card.has("petal"):
            return 3
        if any(p.card.has(t) for t in LAZY_TAGS):
            return 2
        return 1

    def all_units(self, oneshots=False):
        """List of (color, source, preference). Source is a Perm, 'float' or a hand Card."""
        units = [(u, "float", 0) for u in self.floating]
        for p in self.bf:
            pref = self._pref(p)
            for u in self.units_of(p):
                units.append((u, p, pref))
        if oneshots:
            for c in self.hand:
                if c.name == "Elvish Spirit Guide":
                    units.append(("G", c, 4))
                elif c.name == "Lotus Petal":
                    units.append(("A", c, 4))
        return units

    def can_pay(self, cost, oneshots=False):
        return feasible([u[0] for u in self.all_units(oneshots)], cost)

    def pay(self, cost, oneshots=False):
        units = self.all_units(oneshots)
        if not feasible([u[0] for u in units], cost):
            return False
        gen, g, w = cost
        order = sorted(range(len(units)), key=lambda i: units[i][2])
        chosen = set()

        def take(colors, k):
            for i in order:
                if k <= 0:
                    break
                if i not in chosen and units[i][0] in colors:
                    chosen.add(i)
                    k -= 1
            return k

        w = take(("W",), w)
        take(("A",), w)
        g = take(("G",), g)
        take(("A",), g)
        gen = take(("C",), gen)
        gen = take(("G", "W"), gen)
        take(("A",), gen)

        touched = set()
        new_float = []
        for i, (col, src, _) in enumerate(units):
            if src == "float":
                if i not in chosen:
                    new_float.append(col)
            elif i in chosen:
                touched.add(id(src))
        for i, (col, src, _) in enumerate(units):
            if src != "float" and id(src) in touched and i not in chosen:
                new_float.append(col)
        for src in {id(u[1]): u[1] for u in units if u[1] != "float"}.values():
            if id(src) not in touched:
                continue
            if isinstance(src, Perm):
                if src.card.name == "Fal'Cie Paradise":
                    self.carpet_used = True
                elif src.card.has("petal"):
                    self.bf.remove(src)
                    self.gy.append(src.card)
                else:
                    src.tapped = True
            else:  # one-shot from hand
                self.hand.remove(src)
                if src.name == "Lotus Petal":
                    self.gy.append(src)
        self.floating = new_float
        return True

    # ------------------------------------------------------------ zones
    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def search(self, name):
        for i, c in enumerate(self.library):
            if c.name == name:
                return self.library.pop(i)
        return None

    def shuffle(self):
        self.rng.shuffle(self.library)

    def enter(self, card):
        p = Perm(card, sick=True)
        self.bf.append(p)
        c = card
        if c.has("pathway"):
            p.choice = "G" if self.has_w_source() else "W"
        elif c.has("imprint"):
            pick = self._worst_card(nonland=True, colored=True)
            if pick:
                self.hand.remove(pick)
                p.choice = "A" if pick.colors == "GW" else pick.colors[0]
                self.log(f"Chrome Mox imprints {pick.name}")
        elif c.has("diamond"):
            land = self._worst_land()
            if land:
                self.hand.remove(land)
                self.gy.append(land)
            else:
                self.bf.remove(p)
                self.gy.append(card)
        elif c.name == SPEAKER:
            discard = self._worst_card(exclude={SPEAKER})
            if discard:
                target = self._tutor_target(lambda k: k.is_("creature") and not k.is_("land"))
                if target:
                    self.hand.remove(discard)
                    self.gy.append(discard)
                    self.hand.append(self.search(target.name))
                    self.shuffle()
                    self.log(f"Formidable Speaker discards {discard.name}, finds {target.name}")
        elif c.name == RANGERCAP:
            target = self._tutor_target(lambda k: k.is_("creature") and not k.is_("land") and k.mv <= 1)
            if target:
                self.hand.append(self.search(target.name))
                self.shuffle()
                self.log(f"Ranger-Captain finds {target.name}")
        return p

    def play_land(self, card):
        self.hand.remove(card)
        self.land_drop = False
        if card.has("fetch"):
            self.gy.append(card)
            for name in ("Savannah", "Temple Garden", "Forest", "Plains", "Dryad Arbor"):
                got = self.search(name)
                if got:
                    self.enter(got)
                    self.shuffle()
                    self.log(f"play {card.name}, fetch {got.name}")
                    return
            self.log(f"play {card.name} (whiffs)")
            return
        self.enter(card)
        self.log(f"play {card.name}")

    def cast(self, card, cost=None, from_command=False, oneshots=False):
        cost = cost if cost is not None else card.cost
        if from_command:
            self.command.remove(card)
        else:
            self.hand.remove(card)
        if not self.pay(cost, oneshots):
            # put back, should not happen because callers check can_pay first
            (self.command if from_command else self.hand).append(card)
            return False
        self.spells_cast += 1
        if card.name == SISAY:
            self.mark("sisay_cast")
        self.log(f"cast {card.name}")
        if card.is_("instant") or card.is_("sorcery"):
            self.gy.append(card)
        else:
            self.enter(card)
        return True

    # ------------------------------------------------------------ heuristics
    DEAD_ORDER = ("dead",)

    def _worst_card(self, nonland=False, colored=False, exclude=()):
        def badness(c):
            if c.has("dead"):
                return 0
            if c.is_("creature") and not c.has("dork") and c.name not in self._wanted():
                return 1
            if c.is_("land"):
                return 2
            return 3
        cands = [c for c in self.hand if c.name not in exclude
                 and (not nonland or not c.is_("land"))
                 and (not colored or c.colors)
                 and c.name not in self._wanted()
                 and not c.has("tutor")]
        if not cands:
            return None
        cands.sort(key=badness)
        if nonland and badness(cands[0]) > 1:
            return None
        return cands[0]

    def _worst_land(self):
        lands = [c for c in self.hand if c.is_("land")]
        if not lands:
            return None
        lands.sort(key=lambda c: (c.name in (CRADLE, NYKTHOS), c.mana == ("A",)))
        return lands[0]

    def lines_by_distance(self):
        names = {p.card.name for p in self.bf} | {c.name for c in self.hand}
        out = []
        for i, line in enumerate(LINES):
            missing = [x for x in line.pieces if x not in names]
            out.append(((len(missing), i), line, missing))
        out.sort(key=lambda t: t[0])
        return out

    def closest_line(self):
        _, line, missing = self.lines_by_distance()[0]
        return line, missing

    def _wanted(self):
        line, _ = self.closest_line()
        return set(line.pieces) | {KAMAHL}

    def _tutor_target(self, pred):
        line, missing = self.closest_line()
        lib = {c.name: c for c in self.library}
        for name in missing:
            if name in lib and pred(lib[name]):
                return lib[name]
        # secondary targets
        for name in (ASHAYA, HOPE, CRADLE, SELVALA, MAGUS, KAMAHL, EMIEL, NYKTHOS, CUB, "Birds of Paradise",
                     "Llanowar Elves", "Elvish Mystic", "Fyndhorn Elves", "Avacyn's Pilgrim"):
            if name in lib and pred(lib[name]) and not self.in_hand(name) and not self.on_bf(name):
                return lib[name]
        return None

    # ------------------------------------------------------------ planner
    def _land_units(self, card, creatures_after, devotion_after):
        if card.has("fetch"):
            lib = {c.name for c in self.library}
            if "Savannah" in lib or "Temple Garden" in lib:
                return ["A"]
            if "Forest" in lib:
                return ["G"]
            if "Plains" in lib:
                return ["W"]
            return []
        if card.has("cradle"):
            return ["G"] * creatures_after
        if card.has("nykthos"):
            return ["G"] * (devotion_after - 2) if devotion_after - 2 >= 2 else ["C"]
        if card.has("pathway"):
            return ["A"]
        if card.is_("creature"):
            return ["G"] if self.haste_active() else []
        return list(card.mana)

    def _sisay_ok(self):
        p = self.perm(SISAY)
        return p is not None and not p.tapped and (not p.sick or self.haste_active())

    def _options(self, names, land, line_pieces, sisay_ok):
        bf_names = {p.card.name for p in self.bf} | ({land.name} if land else set())
        for name in names:
            if name in bf_names:
                return [Opt(ZERO, frozenset(), None, "battlefield")]
        hand = {c.name for c in self.hand}
        tutors = hand
        spare_bf = [p for p in self.creatures() if p.card.name not in line_pieces and p.card.name != SISAY]
        opts = []
        for name in names:
            card = BY_NAME[name]
            if card.is_("land"):
                if name in hand and land is None:
                    opts.append(Opt(ZERO, frozenset({"drop"}), card, "hand"))
                if card.legendary and sisay_ok and land is None:
                    opts.append(Opt(ZERO, frozenset({"sisay", "drop"}), card, "Sisay"))
                knight = self.perm("Knight of the Reliquary")
                if knight and self.can_tap(knight):
                    opts.append(Opt(ZERO, frozenset({"knight"}), card, "Knight of the Reliquary"))
                reclaimer = self.perm("Elvish Reclaimer")
                if reclaimer and self.can_tap(reclaimer):
                    opts.append(Opt((2, 0, 0), frozenset({"reclaimer"}), card, "Elvish Reclaimer"))
                if "Crop Rotation" in tutors:
                    opts.append(Opt((1, 1, 0), frozenset({"Crop Rotation"}), card, "Crop Rotation"))
                if "Sylvan Scrying" in tutors and land is None:
                    opts.append(Opt((1, 1, 0), frozenset({"Sylvan Scrying", "drop"}), card, "Sylvan Scrying"))
                continue
            if name not in {c.name for c in self.library} and name not in hand:
                continue
            green = "G" in card.colors
            mv = card.mv
            if name in hand:
                opts.append(Opt(card.cost, frozenset({"hand:" + name}), card, "hand"))
            if card.legendary and sisay_ok and name not in hand:
                opts.append(Opt(card.cost, frozenset({"sisay"}), card, "Sisay"))
            if not card.is_("creature"):
                continue
            if name in hand:
                # tutoring a card already in hand only helps via Natural Order (cheaper than Ashaya)
                if "Natural Order" in tutors and green and mv > 4 and any("G" in p.card.colors for p in spare_bf):
                    opts.append(Opt((2, 2, 0), frozenset({"Natural Order"}), card, "Natural Order"))
                continue
            if "Green Sun's Zenith" in tutors and green:
                opts.append(Opt((mv, 1, 0), frozenset({"Green Sun's Zenith"}), card, "Green Sun's Zenith"))
            if "Chord of Calling" in tutors:
                conv = sum(1 for p in self.creatures() if p.sick and not self.haste_active())
                gen = max(0, mv - conv)
                left = conv - (mv - gen)
                opts.append(Opt((gen, max(0, 3 - left), 0), frozenset({"Chord of Calling"}), card, "Chord of Calling"))
            if "Finale of Devastation" in tutors:
                opts.append(Opt((mv, 2, 0), frozenset({"Finale of Devastation"}), card, "Finale of Devastation"))
            if "Nature's Rhythm" in tutors:
                opts.append(Opt((mv, 2, 0), frozenset({"Nature's Rhythm"}), card, "Nature's Rhythm"))
            if "Natural Order" in tutors and green and any("G" in p.card.colors for p in spare_bf):
                opts.append(Opt((2, 2, 0), frozenset({"Natural Order"}), card, "Natural Order"))
            if "Eldritch Evolution" in tutors and any(p.card.mv >= mv - 2 for p in spare_bf):
                opts.append(Opt((1, 2, 0), frozenset({"Eldritch Evolution"}), card, "Eldritch Evolution"))
            if "Summoner's Pact" in tutors and green:
                opts.append(Opt(card.cost, frozenset({"Summoner's Pact"}), card, "Summoner's Pact"))
            if "Eladamri's Call" in tutors:
                opts.append(Opt(add_cost(card.cost, (0, 1, 1)), frozenset({"Eladamri's Call"}), card, "Eladamri's Call"))
            if self.on_bf("Survival of the Fittest") and any(
                    c.is_("creature") and c.name not in line_pieces for c in self.hand):
                opts.append(Opt(add_cost(card.cost, (0, 1, 0)), frozenset({"survival"}), card, "Survival"))
            if SPEAKER in hand and len(self.hand) >= 2:
                opts.append(Opt(add_cost(card.cost, (2, 1, 0)), frozenset({"hand:" + SPEAKER}), card, "Formidable Speaker"))
            if RANGERCAP in hand and mv <= 1:
                opts.append(Opt(add_cost(card.cost, (1, 0, 1)), frozenset({"hand:" + RANGERCAP}), card, "Ranger-Captain"))
        return opts

    def burst_bases(self, base):
        """(units, extra_cost, label) alternatives: plain, then each one-shot untap spell in hand."""
        out = [(base, ZERO, None)]
        if self.in_hand("Vitalize"):
            extra = [u for u, src, _ in self.all_units() if isinstance(src, Perm) and src.card.is_("creature")]
            tapped = [u for p in self.bf if p.tapped and p.card.is_("creature") for u in self.units_of(p, True)]
            extra += tapped
            if len(extra) > 1:
                out.append((base + extra, (0, 1, 0), "Vitalize"))
        if self.in_hand("Emerald Charm"):
            best = []
            for p in self.bf:
                u = self.units_of(p, ignore_tapped=True)
                if p.card.is_("creature") and p.sick and not self.haste_active():
                    continue
                if len(u) > len(best):
                    best = u
            if len(best) > 1:
                out.append((base + best, (0, 1, 0), "Emerald Charm"))
        return out

    def _plan_line(self, line, land, base, extra_cost=ZERO):
        sisay_ok = self._sisay_ok()
        haste_now = self.haste_active()
        nonsick = {p.card.name for p in self.creatures() if not p.sick}
        sick_tappers = [t for t in line.tappers if t not in nonsick and not haste_now]
        slots = [[x] for x in line.pieces]
        need_haste = (line.haste_always and not haste_now) or bool(sick_tappers)
        if need_haste:
            hs = list(HASTE_SOURCES)
            if not line.haste_always and len(sick_tappers) <= 1:
                hs.append(GREAVES)
            slots.append(hs)
        all_opts = []
        for s in slots:
            o = self._options(s, land, line.pieces, sisay_ok)
            if not o:
                return None
            all_opts.append(o)

        cur_creatures = len(self.creatures()) + (1 if land and land.is_("creature") else 0)
        cur_lands = sum(1 for p in self.bf if p.card.is_("land")) + (1 if land else 0)
        cur_nonland_creatures = sum(1 for p in self.creatures() if not p.card.is_("land"))
        cur_dev = self.devotion()
        cur_nonsick = len([p for p in self.creatures() if not p.sick])
        best = None
        for combo in product(*all_opts):
            uses = set()
            if land is not None or not self.land_drop:
                uses.add("drop")  # the land drop is spent (or was never available this turn)
            ok = True
            for o in combo:
                if uses & o.uses:
                    ok = False
                    break
                uses |= o.uses
            if not ok:
                continue
            entering = [o.enter for o in combo if o.enter is not None]
            ent_creatures = [c for c in entering if c.is_("creature")]
            creatures = cur_creatures + len(ent_creatures)
            devotion = cur_dev + sum(c.gpips for c in entering)
            haste = haste_now or any(c.name in HASTE_SOURCES or c.name == GREAVES for c in entering)
            lands = cur_lands + sum(1 for c in entering if c.is_("land"))
            ctx = {
                "creatures": creatures,
                "devotion": devotion,
                "ashaya_power": lands + cur_nonland_creatures + len(ent_creatures),
                "w_perm": self.w_perm() or any("W" in c.colors for c in entering if not c.is_("land")),
                "tap_creatures": creatures if haste_now or any(
                    c.name in HASTE_SOURCES for c in entering) else cur_nonsick,
                "line_tappers": len(line.tappers),
                "haste": haste,
                "sisay": self.perm(SISAY) is not None and not self.perm(SISAY).tapped,
                "selvala_reachable": self.on_bf(SELVALA) or any(c.name == SELVALA for c in self.library),
                "cradle_fresh": (land is not None and land.name == CRADLE)
                or any(c.name == CRADLE for c in entering)
                or (self.perm(CRADLE) is not None and self.perm(CRADLE).sick),
                "cub": int(self.on_bf(CUB) or any(c.name == CUB for c in entering)),
                "max_power": max(self.max_power(), 2, *[c.power for c in ent_creatures],
                                 lands + cur_nonland_creatures + len(ent_creatures)
                                 if self.on_bf(ASHAYA) or any(c.name == ASHAYA for c in entering) else 0),
            }
            if not line.check(ctx):
                continue
            cost = add_cost(line.startup, extra_cost, *[o.cost for o in combo])
            units = list(base)
            if land is not None:
                units += self._land_units(land, creatures, devotion)
            for c in entering:
                if c.is_("land"):
                    units += self._land_units(c, creatures, devotion)
            if not feasible(units, cost):
                continue
            total = sum(cost)
            if best is None or total < best[0]:
                best = (total, combo, uses, haste)
        return best

    def _ezuri_live(self, haste):
        # infinite Ezuri pumps: needs ~3 Elves able to attack (one per opponent); Ezuri itself counts with haste
        elves = [p for p in self.creatures() if p.card.has("elf") and (not p.sick or haste or self.haste_active())]
        extra = 0 if self.on_bf(EZURI) else int(haste or self.haste_active())  # Ezuri cast this turn
        return len(elves) + extra >= 3

    def _outlet(self, line, uses, haste):
        if line.kind == "win":
            return True
        hand = {c.name for c in self.hand}
        lib = {c.name for c in self.library}
        if "Finale of Devastation" in hand and "Finale of Devastation" not in uses:
            return True
        # each remaining outlet is a finisher in hand/play, or a tutor that can find one
        finishers = [KAMAHL] + ([EZURI] if self._ezuri_live(haste) else [])
        green = [f for f in finishers if f in lib]
        if any(f in hand or self.on_bf(f) for f in finishers) or (BALLISTA in hand or self.on_bf(BALLISTA)):
            return True
        anything = green + ([BALLISTA] if BALLISTA in lib else [])
        if not anything:
            return False
        for t in ("Green Sun's Zenith", "Natural Order", "Summoner's Pact"):
            if green and t in hand and t not in uses:
                return True
        for t in ("Chord of Calling", "Nature's Rhythm", "Eldritch Evolution"):
            if t in hand and t not in uses:
                return True
        if "Eladamri's Call" in hand and "Eladamri's Call" not in uses and (line.gives_w or self.has_w_source()):
            return True
        if self.on_bf("Survival of the Fittest") and "survival" not in uses and any(
                c.is_("creature") for c in self.hand):
            return True
        if SPEAKER in hand and "hand:" + SPEAKER not in uses and len(self.hand) >= 2:
            return True
        sisay = self.perm(SISAY)
        if green and line.untaps_sisay and sisay and (not sisay.sick or haste):
            return True  # the engine untaps/re-buys Sisay -> fetch a legendary finisher
        return False

    def available_lines(self):
        """Names of every line that could be completed (with an outlet) right now."""
        base = [u[0] for u in self.all_units(oneshots=True)]
        lands = [None]
        if self.land_drop:
            lands += list({c.name: c for c in self.hand if c.is_("land")}.values())
        out = []
        for line in LINES:
            for land in lands:
                res = self._plan_line(line, land, base)
                if res and self._outlet(line, res[2], res[3]):
                    out.append(line.name)
                    break
        return out

    def _burst_label(self, combo):
        return getattr(self, "_last_burst", None)

    def plan_win(self):
        """Return (line, plan, outlet) for the best line completable now, or None."""
        base = [u[0] for u in self.all_units(oneshots=True)]
        lands = [None]
        if self.land_drop:
            seen = set()
            for c in self.hand:
                if c.is_("land") and c.name not in seen:
                    seen.add(c.name)
                    lands.append(c)
        fallback = None
        self._last_burst = None
        for units, extra, label in self.burst_bases(base):
            for line in LINES:
                for land in lands:
                    res = self._plan_line(line, land, units, extra)
                    if res is None:
                        continue
                    _, combo, uses, haste = res
                    if self._outlet(line, uses, haste):
                        self._last_burst = label
                        return line, combo, land, True
                    if fallback is None:
                        fallback = (line, combo, land, False)
        return fallback

    # ------------------------------------------------------------ turn structure
    def mulligan(self):
        free_used = False
        size = 7
        while True:
            self.library += self.hand
            self.hand = []
            self.shuffle()
            self.draw(7)
            if self._keepable(size) or size <= 5:
                break
            self.result["mulligans"] += 1
            if not free_used:
                free_used = True
            else:
                size -= 1
        for _ in range(7 - size):
            card = self._bottom_choice()
            self.hand.remove(card)
            self.library.insert(0, card)

    def _keepable(self, size):
        lands = sum(1 for c in self.hand if c.is_("land"))
        accel = sum(1 for c in self.hand if c.has("dork") or c.name in (
            "Sol Ring", "Mana Vault", "Chrome Mox", "Mox Diamond", "Lotus Petal", "Elvish Spirit Guide",
            "Utopia Sprawl", "Wild Growth", "Wall of Roots"))
        if lands == 0:
            return False
        if size == 7:
            return 3 <= lands + accel and lands <= 4
        return lands + accel >= 2

    def _bottom_choice(self):
        lands = [c for c in self.hand if c.is_("land")]
        if len(lands) > 3:
            return lands[-1]
        dead = [c for c in self.hand if c.has("dead")]
        if dead:
            return dead[0]
        return self._worst_card() or self.hand[-1]

    def choose_land(self):
        lands = [c for c in self.hand if c.is_("land")]
        if not lands:
            return None
        has_w = self.has_w_source()
        has_g = any(u in ("G", "A") for p in self.bf for u in self.units_of(p, ignore_tapped=True))

        def score(c):
            u = self._land_units(c, len(self.creatures()), self.devotion())
            s = len(u)
            if c.has("cradle") and len(self.creatures()) < 2:
                s = -1 + 0.1 * len(lands)
            if not has_w and any(x in ("W", "A") for x in u):
                s += 0.5
            if not has_g and any(x in ("G", "A") for x in u):
                s += 0.6
            if c.has("fetch"):
                s += 0.05
            return s

        return max(lands, key=score)

    def _castable(self, card, oneshots=False):
        return self.can_pay(card.cost, oneshots)

    def develop(self):
        if self.land_drop:
            land = self.choose_land()
            if land:
                self.play_land(land)

        progress = True
        while progress:
            progress = False
            for card, oneshots in self._dev_candidates():
                if self._try_dev_cast(card, oneshots):
                    progress = True
                    break

    def _dev_candidates(self):
        line, missing = self.closest_line()
        wanted = set(line.pieces)
        hand = list(self.hand)
        out = []
        lands_in_hand = sum(1 for c in hand if c.is_("land"))

        def add(names, oneshots=False):
            for n in names:
                c = next((h for h in hand if h.name == n), None)
                if c:
                    out.append((c, oneshots))

        if self.hand_card("Mox Diamond") and lands_in_hand >= (1 if not self.land_drop else 2):
            add(["Mox Diamond"])
        if self.hand_card("Chrome Mox") and self._worst_card(nonland=True, colored=True):
            add(["Chrome Mox"])
        if any(p.card.legendary and p.card.is_("creature") for p in self.bf):
            add(["Mox Amber"])
        add(["Sol Ring", "Mana Vault"])
        if self.islands:
            add(["Fal'Cie Paradise"])
        dorks1 = ["Llanowar Elves", "Fyndhorn Elves", "Elvish Mystic", "Birds of Paradise", "Avacyn's Pilgrim"]
        if self.forest_on():
            dorks1 = ["Utopia Sprawl", "Wild Growth", "Arbor Elf"] + dorks1
        add(dorks1)
        if SISAY in [c.name for c in self.command]:
            out.append((self.command[0], True))
        add(["Delighted Halfling", "Wall of Roots", "Bloom Tender", "Voyaging Satyr", CUB, "Fanatic of Rhonas"])
        add([x for x in line.pieces if x in wanted], oneshots=True)
        if line.tappers:
            add(list(HASTE_SOURCES))
        add(["Survival of the Fittest", "Knight of the Reliquary", SELVALA, ASHAYA, HOPE, MAGUS])
        # tutors toward the missing pieces
        add(["Natural Order", "Green Sun's Zenith", "Nature's Rhythm", "Chord of Calling", "Eldritch Evolution",
             "Eladamri's Call", "Sylvan Scrying", "Once Upon a Time", SPEAKER, RANGERCAP])
        add(["Esper Sentinel", "Quirion Ranger", "Grand Abolisher", "Mayor Tong of Chin Village", "Voice of Victory",
             "Spectacular Spider-Man", "Scryb Ranger", "Marvin, Murderous Mimic", "Jennifer Walters",
             "Toph, the Blind Bandit", "Boromir, Warden of the Tower", EMIEL, FLASH, KAMAHL, GREAVES])
        return out

    def _try_dev_cast(self, card, oneshots):
        name = card.name
        if card.has("tutor") or card.has("scrying") or card.has("ouat"):
            return self._dev_tutor(card)
        if name == SISAY:
            if self.can_pay(card.cost, oneshots):
                return self.cast(card, from_command=True, oneshots=oneshots)
            return False
        if card not in self.hand or card.is_("land"):
            return False
        if card.is_("instant") or card.is_("sorcery"):
            return False
        if self._castable(card, oneshots):
            return self.cast(card, oneshots=oneshots)
        return False

    def _dev_tutor(self, card):
        name = card.name
        line, missing = self.closest_line()
        lib = {c.name: c for c in self.library}
        creature_targets = [lib[m] for m in missing if m in lib and lib[m].is_("creature") and not lib[m].is_("land")]
        if name == "Sylvan Scrying":
            targets = [lib[m] for m in missing if m in lib and lib[m].is_("land")]
            if targets and self.can_pay(card.cost):
                self.cast(card)
                self.hand.append(self.search(targets[0].name))
                self.shuffle()
                return True
            return False
        if name == "Once Upon a Time":
            cost = ZERO if self.spells_cast == 0 else card.cost
            if not self.can_pay(cost):
                return False
            self.cast(card, cost=cost)
            top = self.library[-5:]
            del self.library[-5:]
            want = [c for c in top if c.name in missing] or \
                   [c for c in top if c.name in (ASHAYA, HOPE, MAGUS, SELVALA, CRADLE)] or \
                   [c for c in top if c.has("dork")] or [c for c in top if c.is_("land") or c.is_("creature")]
            if want:
                top.remove(want[0])
                self.hand.append(want[0])
                self.log(f"Once Upon a Time finds {want[0].name}")
            self.library = top + self.library
            return True
        if not creature_targets:
            return False
        tgt = creature_targets[0]
        if name == "Natural Order":
            green = [t for t in creature_targets if "G" in t.colors]
            spare = [p for p in self.creatures() if "G" in p.card.colors and p.card.name not in line.pieces
                     and p.card.name != SISAY]
            if not green or not spare or not self.can_pay(card.cost):
                return False
            sac = min(spare, key=lambda p: p.card.mv)
            self.cast(card)
            self.bf.remove(sac)
            self.gy.append(sac.card)
            self.enter(self.search(green[0].name))
            self.log(f"Natural Order (sac {sac.card.name}) -> {green[0].name}")
            return True
        if name == "Green Sun's Zenith":
            green = [t for t in creature_targets if "G" in t.colors]
            if not green:
                return False
            t = green[0]
            if not self.can_pay((t.mv, 1, 0)):
                return False
            self.cast(card, cost=(t.mv, 1, 0))
            self.enter(self.search(t.name))
            self.log(f"GSZ -> {t.name}")
            return True
        if name in ("Nature's Rhythm", "Chord of Calling"):
            cost = (tgt.mv, 2, 0) if name == "Nature's Rhythm" else (tgt.mv, 3, 0)
            if not self.can_pay(cost):
                return False
            self.cast(card, cost=cost)
            self.enter(self.search(tgt.name))
            self.log(f"{name} -> {tgt.name}")
            return True
        if name == "Eldritch Evolution":
            spare = [p for p in self.creatures() if p.card.name not in line.pieces and p.card.name != SISAY
                     and p.card.mv >= tgt.mv - 2]
            if not spare or not self.can_pay(card.cost):
                return False
            sac = min(spare, key=lambda p: p.card.mv)
            self.cast(card)
            self.bf.remove(sac)
            self.gy.append(sac.card)
            self.enter(self.search(tgt.name))
            self.log(f"Eldritch Evolution (sac {sac.card.name}) -> {tgt.name}")
            return True
        if name == "Eladamri's Call":
            if not self.can_pay(card.cost):
                return False
            self.cast(card)
            self.hand.append(self.search(tgt.name))
            self.shuffle()
            self.log(f"Eladamri's Call -> {tgt.name}")
            return True
        return False

    def end_step(self):
        line, missing = self.closest_line()
        lib = {c.name: c for c in self.library}
        if self._sisay_ok():
            target = None
            for _, _, miss in self.lines_by_distance():
                target = next((m for m in miss if m in lib and lib[m].legendary), None)
                if target:
                    break
            if target is None:
                for m in (KAMAHL, ASHAYA, CRADLE, SELVALA, NYKTHOS, EMIEL):
                    if m in lib and not self.in_hand(m):
                        target = m
                        break
            if target:
                self.perm(SISAY).tapped = True
                self.hand.append(self.search(target))
                self.mark("sisay_act")
                self.sisay_acts_turn += 1
                self.log(f"Sisay fetches {target}")
        # Worldly / Sylvan Tutor: stack the top for next turn
        for t in ("Worldly Tutor", "Sylvan Tutor"):
            card = self.hand_card(t)
            lib = {c.name: c for c in self.library}
            target = next((m for m in missing if m in lib and lib[m].is_("creature")), None)
            if card and target and self.can_pay(card.cost):
                self.cast(card)
                got = self.search(target)
                self.shuffle()
                self.library.append(got)
                self.log(f"{t} stacks {target}")
                break
        card = self.hand_card("Enlightened Tutor")
        if card and self.can_pay(card.cost):
            for t in ([MANTLE] if MANTLE in missing else []) + [
                    "Survival of the Fittest", "Concordant Crossroads", "Thousand-Year Elixir"]:
                got = self.search(t)
                if got:
                    self.cast(card)
                    self.shuffle()
                    self.library.append(got)
                    self.log(f"Enlightened Tutor stacks {t}")
                    break
        while len(self.hand) > 7:
            c = self._worst_card() or self.hand[0]
            self.hand.remove(c)
            self.gy.append(c)

    def attackers(self, entering=()):
        """Bodies that can attack this turn once Kamahl animates lands: lands and creatures controlled
        since the turn began. The loop itself untaps them. Lethal at a 4-player table needs 3."""
        n = 0
        for p in self.bf:
            if p.card.is_("land") and not p.sick:
                n += 1
            elif p.card.is_("creature") and not p.sick:
                n += 1
        return n

    def protection_ready(self, spare_units):
        """Protection already on the battlefield, or a one-mana protection spell castable with mana the
        combo does not need. Goldfish can only say 'ready', not 'resilient'."""
        if any(self.on_bf(n) for n in PROTECTION_BF):
            return True
        for name, cost in PROTECTION_HAND.items():
            if self.in_hand(name) and feasible(spare_units, cost):
                return True
        return False

    def try_win(self):
        res = self.plan_win()
        if res is None:
            return False
        line, combo, land, outlet = res
        if res is not None:
            self.mark("infinite")
        if outlet and self.attackers() < 3:
            outlet = False
            if self.result["fail"] is None:
                self.result["fail"] = "attackers"
            self.log(f"infinite mana via {line.name} but only {self.attackers()} attackers")
        if outlet:
            self.mark("lethal")
            base = [u[0] for u in self.all_units(oneshots=True)]
            cost = add_cost(line.startup, *[o.cost for o in combo])
            spare = list(base)
            for col in ("W", "G", "C", "A"):
                pass
            # remove the combo's cost from the pool greedily (white first so a spare W is a real W)
            gen, g, w = cost
            for need, cols in ((w, ("W", "A")), (g, ("G", "A"))):
                for _ in range(need):
                    for c in cols:
                        if c in spare:
                            spare.remove(c)
                            break
            for _ in range(gen):
                for c in ("C", "G", "W", "A"):
                    if c in spare:
                        spare.remove(c)
                        break
            self.result["spare_mana"] = len(spare)
            self.result["protected"] = self.protection_ready(spare)
            if self.result["protected"]:
                self.mark("protected_lethal")
            self.result["win_turn"] = self.turn
            self.result["line"] = line.name
            self.result["uses"] = tuple(o.how for o in combo if o.how not in ("battlefield",)) + (
                (self._last_burst,) if self._last_burst else ())
            self.result["available"] = tuple(self.available_lines())
            if self.log_on:
                how = ", ".join(f"{(o.enter.name if o.enter else '-')} via {o.how}" for o in combo)
                self.log(f"WIN with {line.name}" + (f" (land: {land.name})" if land else "") + f": {how}")
            return True
        if self.result["noout_turn"] is None:
            self.result["noout_turn"] = self.turn
            self.result["noout_line"] = line.name
            self.log(f"infinite mana via {line.name} but no outlet")
        return False

    def play_from(self, hand):
        """Play out a game from a given kept hand; the rest of the deck is the (already shuffled) library."""
        names = list(hand)
        self.library = list(self.deck)
        self.hand = []
        for c in names:
            self.library.remove(c)
            self.hand.append(c)
        self.rng.shuffle(self.library)
        return self.play(skip_mulligan=True)

    def play(self, skip_mulligan=False):
        if skip_mulligan:
            pass
        elif self.policy is not None:
            self.policy.run(self)
        else:
            self.mulligan()
        self.result["hand_size"] = len(self.hand)
        self.log("opening hand: " + ", ".join(c.name for c in self.hand))
        if self.on_draw:
            cav = self.hand_card("Gemstone Caverns")
            exile = self._worst_card(exclude={"Gemstone Caverns"}) if cav else None
            if cav and exile:
                self.hand.remove(cav)
                self.hand.remove(exile)
                self.enter(cav)
                self.log(f"Gemstone Caverns starts in play, exiling {exile.name}")
        for _ in range(self.max_turns):
            self.turn += 1
            self.sisay_acts_turn = 0
            self.carpet_used = False
            for p in self.bf:
                p.sick = False
                if not p.card.has("vault"):
                    p.tapped = False
            self.floating = []
            self.land_drop = True
            self.draw()
            if self.try_win():
                return self.result
            self.develop()
            if self.try_win():
                return self.result
            self.end_step()
            cradle = self.perm(CRADLE)
            if cradle and len(self.creatures()) >= 3:
                self.mark("cradle3")
            if self.sisay_acts_turn >= 2:
                self.mark("sisay_x2")
            if self.turn == 4 and self.result["fail"] is None:
                self.result["fail"] = self.diagnose()
            if self.log_on:
                self.log("board: " + ", ".join(p.card.name for p in self.bf))
        return self.result

    def diagnose(self):
        """Why no lethal by now: first matching reason, checked from the most specific."""
        bf = {p.card.name for p in self.bf}
        hand = {c.name for c in self.hand}
        have = bf | hand
        if "infinite" in self.ms:
            return "no outlet"
        if SISAY not in bf:
            return "Sisay too late"
        _, line, missing = self.lines_by_distance()[0]
        emiel_line = EMIEL in line.pieces
        if emiel_line and (EMIEL in hand or FLASH in hand):
            units = [u[0] for u in self.all_units(oneshots=True)]
            w = units.count("W") + units.count("A")
            if (EMIEL in hand and w < 2) or (FLASH in hand and w < 1):
                return "missing white"
        if ASHAYA not in have and EMIEL not in have:
            return "no engine (Ashaya/Emiel)"
        untappers = (HOPE, MAGUS, QUIRION, SCRYB, FLASH, SATYR, ARBOR)
        if not any(u in have for u in untappers):
            return "no untapper"
        if not any(m in have for m in (CRADLE, NYKTHOS, SELVALA, FANATIC, BLOOM, CUB)):
            return "no mana source (Cradle)"
        if len(missing) == 0:
            tapper_sick = any(self.perm(t) and self.perm(t).sick for t in line.tappers) and not self.haste_active()
            if tapper_sick:
                return "no haste"
            return "short on mana"
        return "pieces in hand, not castable"
