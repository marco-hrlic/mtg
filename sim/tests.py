"""Golden tests: deterministic board states and what the planner must (not) credit.

    python3 sim/tests.py

Each test builds a battlefield / hand / library by name and asks the planner whether a win
is available this turn. These pin the rulings the simulator relies on, so a change to the
engine that starts crediting an illegal line fails here before it reaches the Monte Carlo.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cards import BY_NAME, load_decklist  # noqa: E402
from engine import Game, Perm  # noqa: E402

DECK = load_decklist(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decklist.txt"))


def state(bf=(), hand=(), turn=4, land_drop=True, library=("Kamahl, Fist of Krosa",)):
    """bf: names or (name, sick) tuples. Sisay is on the battlefield only if named. The library holds only
    the named cards (default: just Kamahl), so a test cannot pass by tutoring something it did not list."""
    g = Game(DECK, random.Random(0), max_turns=8)
    g.library = [BY_NAME[n] for n in library]
    g.turn = turn
    g.land_drop = land_drop
    g.hand = []
    used = []
    for item in bf:
        name, sick = item if isinstance(item, tuple) else (item, False)
        p = Perm(BY_NAME[name], sick=sick)
        if name == "Branchloft Pathway":
            p.choice = "G"
        g.bf.append(p)
        used.append(name)
    for name in hand:
        g.hand.append(BY_NAME[name])
        used.append(name)
    if "Captain Sisay" in used:
        g.command = []
    return g


def wins(g):
    res = g.plan_win()
    if res is None:
        return False
    line, combo, land, outlet = res
    return outlet and g.attackers() >= 3


def infinite(g):
    return g.plan_win() is not None


CASES = []


def case(name, expect, build):
    CASES.append((name, expect, build))


LANDS3 = ["Forest", "Forest", "Savannah"]
SISAY = "Captain Sisay"

# --- Ashaya engine --------------------------------------------------------------------------
case("Ashaya+Hope+Cradle: Hope unsick, Kamahl in library -> win", True, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", "Hope Tender", "Gaea's Cradle", "Llanowar Elves", SISAY]))
case("Ashaya+Hope+Cradle: Hope summoning sick, no haste -> no", False, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", ("Hope Tender", True), "Gaea's Cradle", "Llanowar Elves", SISAY]))
case("...same, but Sisay can fetch Shang-Chi for haste -> win", True, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", ("Hope Tender", True), "Gaea's Cradle", "Llanowar Elves", SISAY],
    library=["Kamahl, Fist of Krosa", "Shang-Chi, Master of Kung Fu"]))
case("Ashaya+Hope+Cradle: Hope sick but Concordant Crossroads -> win", True, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", ("Hope Tender", True), "Gaea's Cradle", "Llanowar Elves", SISAY,
                 "Concordant Crossroads"]))
case("Ashaya+Hope+Cradle but Sisay sick and no Kamahl route -> infinite, no lethal", False, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", "Hope Tender", "Gaea's Cradle", "Llanowar Elves", (SISAY, True)]))
case("Ashaya+Quirion+Selvala: Ashaya power 3 (3 lands) -> win", True, lambda: state(
    bf=["Forest", "Savannah", "Temple Garden", "Ashaya, Soul of the Wild", "Quirion Ranger",
        "Selvala, Heart of the Wilds", SISAY]))
case("Ashaya+Quirion+Selvala: Quirion cast this turn still works (never taps)", True, lambda: state(
    bf=["Forest", "Savannah", "Temple Garden", "Ashaya, Soul of the Wild", ("Quirion Ranger", True),
        "Selvala, Heart of the Wilds", SISAY]))
case("Hope+Cradle without Ashaya -> no (Hope can't untap itself)", False, lambda: state(
    bf=LANDS3 + ["Hope Tender", "Gaea's Cradle", "Llanowar Elves", "Birds of Paradise", SISAY]))
case("...same, Ashaya in library: Sisay fetches, 9 mana casts her -> win", True, lambda: state(
    bf=LANDS3 + ["Hope Tender", "Gaea's Cradle", "Llanowar Elves", "Birds of Paradise", SISAY],
    library=["Kamahl, Fist of Krosa", "Ashaya, Soul of the Wild"]))
case("Sisay fetches Cradle to HAND: needs the land drop", False, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", "Hope Tender", "Llanowar Elves", SISAY], land_drop=False,
    library=["Kamahl, Fist of Krosa", "Gaea's Cradle"]))
case("Sisay fetches Cradle to hand, land drop available -> win", True, lambda: state(
    bf=LANDS3 + ["Ashaya, Soul of the Wild", "Hope Tender", "Llanowar Elves", SISAY], land_drop=True,
    library=["Kamahl, Fist of Krosa", "Gaea's Cradle"]))

# --- Emiel engine and white pips ------------------------------------------------------------
case("Emiel+Flash+Fanatic on battlefield -> win (green only)", True, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", "Fanatic of Rhonas", SISAY]))
case("Emiel in hand, only green mana -> no (WW)", False, lambda: state(
    bf=["Forest", "Forest", "Forest", "Forest", "Forest", "Forest", "Flash Thompson, Spider-Fan",
        "Fanatic of Rhonas", SISAY], hand=["Emiel the Blessed"]))
case("Emiel in hand with Savannah + Plains -> win", True, lambda: state(
    bf=["Forest", "Forest", "Forest", "Savannah", "Plains", "Forest", "Flash Thompson, Spider-Fan",
        "Fanatic of Rhonas", SISAY], hand=["Emiel the Blessed"]))
case("Emiel+Flash+Selvala: Emiel power 4 only -> no (needs 5)", False, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", "Selvala, Heart of the Wilds", SISAY]))
case("Emiel+Flash+Selvala with Badgermole Cub -> win", True, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", "Selvala, Heart of the Wilds", SISAY,
                 "Badgermole Cub"]))

# --- Animated Cradle ------------------------------------------------------------------------
case("Animate Land on a Cradle played this turn -> no haste, no", False, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", ("Gaea's Cradle", True), "Llanowar Elves",
                 "Birds of Paradise", SISAY], hand=["Animate Land"]))
case("Animate Land on a Cradle held since turn start -> win", True, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", "Gaea's Cradle", "Llanowar Elves",
                 "Birds of Paradise", SISAY], hand=["Animate Land"]))
case("Cub earthbend on a fresh Cradle gives haste -> win", True, lambda: state(
    bf=LANDS3 + ["Emiel the Blessed", "Flash Thompson, Spider-Fan", ("Gaea's Cradle", True), "Llanowar Elves",
                 "Birds of Paradise", SISAY], hand=["Badgermole Cub"]))
case("Vitalize cannot untap a non-creature Cradle (no engine) -> no", False, lambda: state(
    bf=LANDS3 + ["Gaea's Cradle", "Llanowar Elves", "Birds of Paradise", "Hope Tender", SISAY], hand=["Vitalize"]))

# --- Finish ---------------------------------------------------------------------------------
case("Infinite mana, Kamahl in hand, only 2 attackers -> not lethal", False, lambda: state(
    bf=[("Forest", True), ("Savannah", True), ("Ashaya, Soul of the Wild", True), "Hope Tender", ("Gaea's Cradle", True),
        "Llanowar Elves", (SISAY, True), "Concordant Crossroads"],
    hand=["Kamahl, Fist of Krosa"], library=[]))
case("...same board, one more land held since turn start -> lethal", True, lambda: state(
    bf=["Forest", ("Savannah", True), ("Ashaya, Soul of the Wild", True), "Hope Tender", ("Gaea's Cradle", True),
        "Llanowar Elves", (SISAY, True), "Concordant Crossroads"],
    hand=["Kamahl, Fist of Krosa"], library=[]))
case("Kamahl exiled (not in library/hand), Sisay untapped -> infinite but no lethal", False, lambda: _no_kamahl())
case("Finale in hand replaces Kamahl -> win", True, lambda: _no_kamahl(finale=True))

# --- Not infinite ----------------------------------------------------------------------------
case("Formidable Speaker + Elixir + Cradle -> no", False, lambda: state(
    bf=LANDS3 + ["Formidable Speaker", "Thousand-Year Elixir", "Gaea's Cradle", "Llanowar Elves",
                 "Birds of Paradise", SISAY]))
case("Quirion Ranger + Selvala without Ashaya -> no (once per turn)", False, lambda: state(
    bf=["Forest", "Savannah", "Temple Garden", "Quirion Ranger", "Selvala, Heart of the Wilds", "Fanatic of Rhonas",
        SISAY]))


def _no_kamahl(finale=False):
    return state(bf=LANDS3 + ["Ashaya, Soul of the Wild", "Hope Tender", "Gaea's Cradle", "Llanowar Elves", SISAY],
                 hand=["Finale of Devastation"] if finale else [], library=["Selvala, Heart of the Wilds"])


def main():
    failed = 0
    for name, expect, build in CASES:
        g = build()
        got = wins(g)
        ok = got == expect
        failed += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"  (got {got}, infinite={infinite(g)})"))
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
