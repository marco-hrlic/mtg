"""First Sisay activation: Cradle vs Selvala vs the rest, as a paired counterfactual.

    python3 sim/first_tutor.py --games 5000                      # capture states under policy A, run all arms
    python3 sim/first_tutor.py --games 800 --policy D            # same under the rollout mulligan policy
    python3 sim/first_tutor.py --games 3000 --islands 2
    python3 sim/first_tutor.py --games 2000 --divergences 12     # print traces where the arms disagree

Method. Real games are played by the normal pilot until the first turn on which Sisay can legally
activate (untapped, not summoning sick or ability-hasted, with a legendary target in the library).
The game is frozen there, before the end step. Each arm then continues an identical copy of that
state with the same random seed, differing only in what Sisay fetches:

  current       the pilot's own choice (missing legend of the closest line)
  cradle        Gaea's Cradle if in library, else not_available
  selvala       Selvala if in library, else not_available
  contextual    the hand-written rule from the brief's section C
  lookahead     every relevant legend in the library, R rollouts each, highest utility wins

Downstream play is the same pilot for every arm. After the fetch the library is reshuffled by the
pilot's normal shuffle, so no illegal deck order survives the tutor.
"""
import argparse
import copy
import math
import os
import random
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cards import load_decklist  # noqa: E402
from engine import (ASHAYA, CRADLE, CUB, EMIEL, FANATIC, FLASH, HOPE, KAMAHL, MAGUS, QUIRION, SCRYB, SELVALA,  # noqa: E402
                    SHANG, SISAY, TOPH, Game)
from mulligan import POLICIES, Rollout, utility  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TURNS = 5
CANDIDATES = (CRADLE, SELVALA, ASHAYA, SHANG, TOPH, EMIEL, FLASH, KAMAHL)
ARMS = ("current", "cradle", "selvala", "contextual", "lookahead")


class Captured(Exception):
    pass


# ------------------------------------------------------------------ state capture

def capture(deck, games, seed, policy_key, islands, on_draw, rollouts, calib):
    pol = None
    if policy_key == "D":
        pol = Rollout(deck, rollouts=rollouts, calib_hands=calib, seed=seed + 7, islands=islands, on_draw=on_draw)
    elif policy_key:
        pol = POLICIES[policy_key]()
    states = []

    def hook(g):
        raise Captured()

    for i in range(games):
        g = Game(deck, random.Random(seed * 1_000_003 + i), max_turns=TURNS, policy=pol,
                 islands=islands, on_draw=on_draw)
        g.first_activation_hook = hook
        try:
            g.play()
        except Captured:
            g.policy = None
            g.first_activation_hook = None
            g.game_index = i
            states.append(g)
    return states, games


def snapshot(g):
    """Features of a captured state, for stratification."""
    lib = {c.name for c in g.library}
    bf = {p.card.name for p in g.bf}
    hand = {c.name for c in g.hand}
    have = bf | hand
    units = [u for p in g.bf for u in g.units_of(p, ignore_tapped=True)]
    white = sum(1 for u in units if u in ("W", "A"))
    n = len(g.creatures())
    p = g.max_power()
    tap_untappers = [x for x in (HOPE, MAGUS) if x in have]
    fresh_tappers = any(g.perm(x) is not None and g.perm(x).sick for x in (HOPE, MAGUS, SELVALA, FANATIC))
    return {
        "turn": g.turn, "land_drop": g.land_drop, "creatures": n, "power": p, "white": white,
        "hand_size": len(g.hand), "mulligans": g.result["mulligans"],
        "cradle_lib": CRADLE in lib, "selvala_lib": SELVALA in lib, "cradle_have": CRADLE in have,
        "emiel_flash": EMIEL in have and FLASH in have,
        "emiel_flash_bf": EMIEL in bf and FLASH in bf,
        "fanatic_active": g.perm(FANATIC) is not None and g.can_tap(g.perm(FANATIC)),
        "selvala_usable": g.haste_active(),
        "ashaya_untapper": ASHAYA in have and bool(tap_untappers),
        "untapper_have": any(x in have for x in (HOPE, MAGUS, QUIRION, SCRYB, FLASH)),
        "cradle_tutor": "Crop Rotation" in hand or "Sylvan Scrying" in hand or "Knight of the Reliquary" in bf,
        "fresh_tappers": fresh_tappers, "haste": g.haste_active(), "cub": CUB in have,
    }


# ------------------------------------------------------------------ target rules

def contextual_target(g):
    f = snapshot(g)
    lib = {c.name for c in g.library}
    bf = {p.card.name for p in g.bf}
    have = bf | {c.name for c in g.hand}
    if CRADLE in lib and f["land_drop"] and f["creatures"] >= 3:
        return CRADLE
    if CRADLE in lib and f["ashaya_untapper"]:
        return CRADLE
    if CRADLE not in lib:  # Cradle already in hand or play
        if ASHAYA in lib and f["untapper_have"]:
            return ASHAYA
        if f["fresh_tappers"] and not f["haste"] and SHANG in lib:
            return SHANG
        if f["emiel_flash"] and CRADLE in bf and TOPH in lib and not f["cub"]:
            return TOPH
        if KAMAHL in lib:
            return KAMAHL
    if f["emiel_flash"] and SELVALA in lib and (f["power"] >= 5 or f["cub"]):
        return SELVALA
    if f["white"] == 0 and (EMIEL in have or FLASH in have) and SELVALA in lib:
        return SELVALA
    if f["fresh_tappers"] and not f["haste"] and SHANG in lib:
        return SHANG
    if f["emiel_flash"] and f["fanatic_active"] and KAMAHL in lib:
        return KAMAHL
    if f["creatures"] <= 2 and not f["untapper_have"] and f["power"] >= 4 and SELVALA in lib:
        return SELVALA
    if CRADLE in lib:
        return CRADLE
    if ASHAYA in lib:
        return ASHAYA
    return g.default_sisay_target()


def run_arm(state, target, seed, log=False):
    g = copy.deepcopy(state)
    g.rng = random.Random(seed)
    g.log_on = log
    g.forced_target = target
    lib = {c.name for c in g.library}
    fetched = target if (target in lib) else (g.default_sisay_target() if target is None else None)
    stranded = fetched == CRADLE and not g.land_drop
    selvala_sick = fetched == SELVALA and not g.haste_active()
    r = g.resume()
    return r, g, {"fetched": fetched, "stranded": stranded, "selvala_sick": selvala_sick}


def lookahead_target(state, seed, rollouts):
    lib = {c.name for c in state.library}
    cands = [c for c in CANDIDATES if c in lib]
    best = None
    for c in cands:
        tot = 0.0
        for j in range(rollouts):
            r, _, _ = run_arm(state, c, seed * 31 + j * 7 + 1)
            tot += utility(r) + 0.1 * (1 if r["win_turn"] and r["win_turn"] <= 5 else 0)
        if best is None or tot > best[0]:
            best = (tot, c)
    return best[1] if best else None


def evaluate_state(args):
    state, seed, rollouts, arms = args
    out = {"features": snapshot(state), "game": state.game_index}
    lib = {c.name for c in state.library}
    for arm in arms:
        if arm == "current":
            target = None
        elif arm == "cradle":
            target = CRADLE if CRADLE in lib else "n/a"
        elif arm == "selvala":
            target = SELVALA if SELVALA in lib else "n/a"
        elif arm == "contextual":
            target = contextual_target(state)
        else:
            target = lookahead_target(state, seed, rollouts)
        if target == "n/a":
            out[arm] = None
            continue
        r, g, info = run_arm(state, target, seed)
        out[arm] = {
            "win": r["win_turn"], "prot": bool(r["protected"]), "inf4": r["milestones"].get("infinite", 99) <= 4,
            "x2_4": r["milestones"].get("sisay_x2", 99) <= 4, "line": r.get("line"), "util": utility(r),
            "fail": r["fail"], **info,
        }
    return out


# ------------------------------------------------------------------ reporting

def ci(vals):
    n = len(vals)
    if n == 0:
        return (0, 0, 0)
    m = sum(vals) / n
    var = sum((v - m) ** 2 for v in vals) / max(1, n - 1)
    h = 1.96 * math.sqrt(var / n)
    return (m, m - h, m + h)


def rate(rows, arm, key):
    vals = [1 if (row[arm] and key(row[arm])) else 0 for row in rows if row[arm] is not None]
    return ci(vals), len(vals)


def table(rows, arms, title):
    print(f"\n{title}  (n = {len(rows)})")
    print(f"  {'arm':12s} {'n':>5s} {'lethal<=T3':>11s} {'lethal<=T4':>11s} {'lethal<=T5':>11s} {'prot<=T4':>9s} "
          f"{'inf<=T4':>8s} {'Emiel line':>10s} {'Ashaya line':>11s} {'utility':>8s}")
    for arm in arms:
        avail = [r for r in rows if r[arm] is not None]
        if not avail:
            continue
        n = len(avail)
        l3 = sum(1 for r in avail if r[arm]["win"] and r[arm]["win"] <= 3) / n
        l4 = sum(1 for r in avail if r[arm]["win"] and r[arm]["win"] <= 4) / n
        l5 = sum(1 for r in avail if r[arm]["win"] and r[arm]["win"] <= 5) / n
        p4 = sum(1 for r in avail if r[arm]["win"] and r[arm]["win"] <= 4 and r[arm]["prot"]) / n
        i4 = sum(1 for r in avail if r[arm]["inf4"]) / n
        x2 = sum(1 for r in avail if r[arm]["x2_4"]) / n
        em = sum(1 for r in avail if r[arm]["win"] and (r[arm]["line"] or "").startswith("Emiel")) / n
        ash = sum(1 for r in avail if r[arm]["win"] and (r[arm]["line"] or "").startswith("Ashaya")) / n
        u = sum(r[arm]["util"] for r in avail) / n
        print(f"  {arm:12s} {n:5d} {l3:11.1%} {l4:11.1%} {l5:11.1%} {p4:9.1%} {i4:8.1%} {em:10.1%} {ash:11.1%} {u:8.3f}")


def paired(rows, a, b, key=lambda x: x["win"] is not None and x["win"] <= 4):
    diffs = [(1 if key(r[a]) else 0) - (1 if key(r[b]) else 0) for r in rows if r[a] is not None and r[b] is not None]
    return ci(diffs), len(diffs)


def bucket(rows, name, fn):
    groups = defaultdict(list)
    for r in rows:
        groups[fn(r["features"])].append(r)
    return name, groups


def report(rows, args):
    arms = args.arms
    print(f"{len(rows)} first-activation states captured from {args.games} games (policy {args.policy or 'none'}, "
          f"seed {args.seed}, islands={args.islands}, {'on the draw' if args.on_draw else 'on the play'}); "
          f"{TURNS} turns; lookahead rollouts={args.rollouts}")
    turns = Counter(r["features"]["turn"] for r in rows)
    print("First activation on turn: " + ", ".join(f"T{t}: {k / len(rows):.0%}" for t, k in sorted(turns.items())))
    both = [r for r in rows if r["features"]["cradle_lib"] and r["features"]["selvala_lib"]]

    table(rows, arms, "ALL first-activation states")
    table(both, arms, "COHORT: both Cradle and Selvala still in the library")

    print("\nPaired differences on the cohort, P(lethal<=T4), mean [95% CI]")
    for a, b in (("cradle", "selvala"), ("contextual", "cradle"), ("lookahead", "cradle"), ("lookahead", "contextual"),
                 ("current", "cradle")):
        if a in arms and b in arms:
            (m, lo, hi), n = paired(both, a, b)
            print(f"  {a:11s} - {b:11s}: {m:+.1%} [{lo:+.1%}, {hi:+.1%}]  n={n}")
    (m, lo, hi), n = paired(both, "cradle", "selvala", key=lambda x: x["win"] is not None and x["win"] <= 5)
    print(f"  cradle - selvala on lethal<=T5: {m:+.1%} [{lo:+.1%}, {hi:+.1%}]")

    print("\nFetched-Cradle stranded (land drop already spent) / fetched-Selvala summoning sick, share of arm's states")
    for arm in arms:
        avail = [r[arm] for r in rows if r[arm] is not None]
        if avail:
            print(f"  {arm:12s} stranded {sum(1 for x in avail if x['stranded']) / len(avail):6.1%}   "
                  f"Selvala sick {sum(1 for x in avail if x['selvala_sick']) / len(avail):6.1%}")

    for arm in ("current", "contextual", "lookahead"):
        if arm in arms:
            dist = Counter(r[arm]["fetched"] for r in rows if r[arm] is not None)
            print(f"\nWhat `{arm}` fetched: " + ", ".join(f"{k}: {v / len(rows):.0%}" for k, v in dist.most_common()))

    print("\nSTRATIFIED cohort: P(lethal<=T4) by arm  [n]")
    strata = [
        bucket(both, "land drop", lambda f: "unused" if f["land_drop"] else "spent"),
        bucket(both, "creatures", lambda f: "0-2" if f["creatures"] <= 2 else ("3-4" if f["creatures"] <= 4 else "5+")),
        bucket(both, "max power", lambda f: "<=3" if f["power"] <= 3 else ("4" if f["power"] == 4 else "5+")),
        bucket(both, "Emiel+Flash in hand/play", lambda f: "yes" if f["emiel_flash"] else "no"),
        bucket(both, "Fanatic active", lambda f: "yes" if f["fanatic_active"] else "no"),
        bucket(both, "Selvala could tap at once (haste src)", lambda f: "yes" if f["selvala_usable"] else "no"),
        bucket(both, "Ashaya + Hope/Magus held", lambda f: "yes" if f["ashaya_untapper"] else "no"),
        bucket(both, "white sources", lambda f: "0" if f["white"] == 0 else ("1" if f["white"] == 1 else "2+")),
        bucket(both, "independent Cradle tutor", lambda f: "yes" if f["cradle_tutor"] else "no"),
        bucket(both, "activation turn", lambda f: f"T{f['turn']}"),
    ]
    hdr = "".join(f"{a:>13s}" for a in arms)
    for name, groups in strata:
        print(f"  {name}")
        for key in sorted(groups):
            rs = groups[key]
            cells = ""
            for arm in arms:
                avail = [r for r in rs if r[arm] is not None]
                if avail:
                    l4 = sum(1 for r in avail if r[arm]["win"] and r[arm]["win"] <= 4) / len(avail)
                    cells += f"{l4:12.1%} "
                else:
                    cells += f"{'-':>12s} "
            print(f"    {key:8s} [{len(rs):4d}] {cells}")
    print("  columns: " + hdr.strip())

    print("\nPrimary T4 failure reason by arm (share of the arm's states without a T4 lethal)")
    reasons = sorted({r[a]["fail"] for r in rows for a in arms if r[a] is not None and r[a]["fail"]}, key=str)
    print(f"  {'reason':32s}" + "".join(f"{a:>12s}" for a in arms))
    for reason in reasons:
        cells = ""
        for arm in arms:
            avail = [r[arm] for r in rows if r[arm] is not None and not (r[arm]["win"] and r[arm]["win"] <= 4)]
            cells += f"{(sum(1 for x in avail if x['fail'] == reason) / len(avail)) if avail else 0:12.1%}"
        print(f"  {str(reason):32s}{cells}")


def divergences(states, rows, args):
    """Print full traces where cradle and selvala disagree on a T4 lethal."""
    by_game = {s.game_index: s for s in states}
    picked = []
    for r in rows:
        c, s = r.get("cradle"), r.get("selvala")
        if not c or not s:
            continue
        cw = c["win"] is not None and c["win"] <= 4
        sw = s["win"] is not None and s["win"] <= 4
        if cw != sw:
            picked.append((r, cw))
    cradle_wins = [p for p in picked if p[1]][: args.divergences // 2]
    selvala_wins = [p for p in picked if not p[1]][: args.divergences - len(cradle_wins)]
    for r, cw in cradle_wins + selvala_wins:
        st = by_game[r["game"]]
        f = r["features"]
        print("\n" + "=" * 100)
        print(f"game {r['game']}: {'CRADLE wins T4, Selvala does not' if cw else 'SELVALA wins T4, Cradle does not'}")
        print(f"  T{f['turn']}, land drop {'unused' if f['land_drop'] else 'spent'}, creatures {f['creatures']}, "
              f"max power {f['power']}, white sources {f['white']}, hand {f['hand_size']}")
        print("  board: " + ", ".join(p.card.name + ("(sick)" if p.sick else "") + ("(T)" if p.tapped else "")
                                     for p in st.bf))
        print("  hand:  " + ", ".join(c.name for c in st.hand))
        units = [u for p in st.bf for u in st.units_of(p, ignore_tapped=True)]
        print(f"  mana potential: {Counter(units)}")
        for arm, target in (("cradle", CRADLE), ("selvala", SELVALA)):
            _, g, _ = run_arm(st, target, args.seed * 7 + r["game"], log=True)
            print(f"  --- {arm}:")
            for line in g.logs:
                print("    " + line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--policy", default="A", help="mulligan policy used to reach the first activation (A/B/C/D)")
    ap.add_argument("--islands", type=int, default=0)
    ap.add_argument("--on-draw", action="store_true")
    ap.add_argument("--rollouts", type=int, default=4, help="lookahead rollouts per candidate")
    ap.add_argument("--calib", type=int, default=60, help="policy D calibration hands")
    ap.add_argument("--arms", nargs="+", default=list(ARMS))
    ap.add_argument("--divergences", type=int, default=0, help="print N traces where cradle/selvala disagree")
    ap.add_argument("--deck", default=os.path.join(HERE, "decklist.txt"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    deck = load_decklist(args.deck)

    states, played = capture(deck, args.games, args.seed, args.policy, args.islands, args.on_draw,
                             5, args.calib)
    jobs = [(s, args.seed * 7 + s.game_index, args.rollouts, args.arms) for s in states]
    with Pool(args.jobs) as pool:
        rows = pool.map(evaluate_state, jobs, chunksize=8)
    print(f"Games played: {played}; games reaching a first activation by T{TURNS}: {len(states)} "
          f"({len(states) / played:.0%})")
    report(rows, args)
    if args.divergences:
        divergences(states, rows, args)


if __name__ == "__main__":
    main()
