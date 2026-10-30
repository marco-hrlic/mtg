"""Mulligan-policy experiment: same deck, same seeds, policies A-D.

    python3 sim/experiment.py --games 5000
    python3 sim/experiment.py --games 20000 --policies A B C
    python3 sim/experiment.py --games 3000 --islands 1 --on-draw
    python3 sim/experiment.py --hands 10          # opening-hand decisions side by side

Game i of every policy starts from the same shuffled library (seed, i), so differences are
the policy, not the deck order. Proportions carry 95% Wilson intervals.
"""
import argparse
import math
import os
import random
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cards import load_decklist  # noqa: E402
from engine import Game  # noqa: E402
from mulligan import POLICIES, Rollout, features, utility  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TURNS = 6  # the brief cares about T3/T4; six turns keeps the run fast


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k / n:5.1%} [{lo:4.1%}-{hi:4.1%}]"


def make_policy(key, deck, args):
    if key == "D":
        return Rollout(deck, rollouts=args.rollouts, calib_hands=args.calib, seed=args.seed + 7,
                       islands=args.islands, on_draw=args.on_draw)
    return POLICIES[key]()


def run_policy(job):
    key, deck, games, seed, islands, on_draw, args_d = job
    class A:  # minimal args holder for make_policy
        pass
    a = A()
    a.rollouts, a.calib, a.seed, a.islands, a.on_draw = args_d["rollouts"], args_d["calib"], seed, islands, on_draw
    pol = make_policy(key, deck, a)
    results = []
    for i in range(games):
        g = Game(deck, random.Random(seed * 1_000_003 + i), max_turns=TURNS, policy=pol,
                 islands=islands, on_draw=on_draw)
        results.append(g.play())
    return key, pol.name, results, getattr(pol, "V", None)


def summarize(results):
    n = len(results)
    ms = [r["milestones"] for r in results]

    def by(name, t):
        return sum(1 for m in ms if m.get(name, 99) <= t)

    lethal = lambda t: sum(1 for r in results if r["win_turn"] and r["win_turn"] <= t)  # noqa: E731
    prot4 = sum(1 for r in results if r["win_turn"] and r["win_turn"] <= 4 and r["protected"])
    sizes = Counter(r["hand_size"] for r in results)
    fails = Counter(r["fail"] for r in results if not (r["win_turn"] and r["win_turn"] <= 4))
    white = fails["missing white"]
    return {
        "n": n, "sizes": sizes,
        "sisay2": by("sisay_cast", 2), "act3": by("sisay_act", 3), "cradle3": by("cradle3", 3),
        "x2_4": by("sisay_x2", 4), "inf4": by("infinite", 4),
        "lethal3": lethal(3), "lethal4": lethal(4), "prot4": prot4, "white": white, "fails": fails,
        "util": sum(utility(r) for r in results) / n,
        "mulls": sum(r["mulligans"] for r in results) / n,
    }


def report(all_runs, args):
    print(f"{args.games} games per policy, seed {args.seed}, {TURNS} turns, Carpet islands={args.islands}, "
          f"{'on the draw' if args.on_draw else 'on the play'}\n")
    hdr = f"{'policy':16s} {'keep 7/6/5/4 %':>18s} {'Sisay<=T2':>20s} {'1st act<=T3':>20s} {'inf<=T4':>20s}"
    print(hdr)
    for key, name, results, V in all_runs:
        s = summarize(results)
        n = s["n"]
        sz = "/".join(f"{s['sizes'][k] / n * 100:.0f}" for k in (7, 6, 5, 4))
        print(f"{name:16s} {sz:>18s} {fmt(s['sisay2'], n):>20s} {fmt(s['act3'], n):>20s} {fmt(s['inf4'], n):>20s}")
    print()
    hdr = f"{'policy':16s} {'lethal<=T3':>20s} {'lethal<=T4':>20s} {'protected<=T4':>20s} {'white %':>8s} {'utility':>8s} {'mulls':>6s}"
    print(hdr)
    for key, name, results, V in all_runs:
        s = summarize(results)
        n = s["n"]
        print(f"{name:16s} {fmt(s['lethal3'], n):>20s} {fmt(s['lethal4'], n):>20s} {fmt(s['prot4'], n):>20s} "
              f"{s['white'] / n:7.1%} {s['util']:8.3f} {s['mulls']:6.2f}")
    print("\nutility = 1.0*P(protected lethal<=T4) + 0.35*P(lethal<=T4) + 0.15*P(infinite<=T4)")
    print("white % = games without a T4 lethal where an Emiel/Flash piece sat in hand short of W\n")

    print("Primary reason there was no lethal by T4 (share of all games)")
    keys = sorted({k for _, _, r, _ in all_runs for k in summarize(r)["fails"]}, key=str)
    print(f"  {'reason':32s}" + "".join(f"{k:>8s}" for k, *_ in all_runs))
    for reason in keys:
        row = "".join(f"{summarize(r)['fails'][reason] / len(r):8.1%}" for _, _, r, _ in all_runs)
        print(f"  {str(reason):32s}{row}")
    for key, name, results, V in all_runs:
        if V:
            print(f"\nPolicy D calibration: value of mulliganing to k cards: " +
                  ", ".join(f"V[{k}]={v:.3f}" for k, v in sorted(V.items())))


def sample_hands(deck, args):
    """Show the same seven-card openers to every policy."""
    pols = {k: make_policy(k, deck, args) for k in args.policies}
    print(f"{'#':>2s}  " + "  ".join(f"{k:>6s}" for k in args.policies) + "   D: keep est vs mulligan value   hand")
    flashy_worse, dull_better = [], []
    for i in range(args.hands):
        g = Game(deck, random.Random(args.seed * 7919 + i), max_turns=TURNS)
        hand = g.library[-7:]
        names = ", ".join(c.name for c in hand)
        decisions = []
        for k, p in pols.items():
            g.result["mulligans"] = 0
            decisions.append("keep" if p.keep(g, hand, 7) else "mull")
        d = pols.get("D")
        est = mull = None
        if d:
            _, _, est, mull, _ = d.decisions[-1]
        tail = f"   {est:.3f} vs {mull:.3f}" if est is not None else ""
        print(f"{i + 1:2d}  " + "  ".join(f"{x:>6s}" for x in decisions) + f"{tail:>32s}   {names}")
        if est is not None:
            f = features(hand)
            if f["cradle"] and est < mull:
                flashy_worse.append((names, est, mull))
            if not f["cradle"] and f["engine"] == 0 and est >= mull:
                dull_better.append((names, est, mull))
    if flashy_worse:
        print("\nCradle in the opener but the rollout says take the free mulligan:")
        for n, e, m in flashy_worse[:5]:
            print(f"  {e:.3f} < {m:.3f}  {n}")
    if dull_better:
        print("\nNo Cradle and no engine piece, but the rollout keeps:")
        for n, e, m in dull_better[:5]:
            print(f"  {e:.3f} >= {m:.3f}  {n}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--policies", nargs="+", default=["A", "B", "C", "D"])
    ap.add_argument("--islands", type=int, default=0, help="opposing Islands for Carpet of Flowers")
    ap.add_argument("--on-draw", action="store_true")
    ap.add_argument("--rollouts", type=int, default=5, help="policy D rollouts per estimate")
    ap.add_argument("--calib", type=int, default=120, help="policy D calibration hands per hand size")
    ap.add_argument("--hands", type=int, default=0, help="show N opening hands and each policy's decision")
    ap.add_argument("--deck", default=os.path.join(HERE, "decklist.txt"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    deck = load_decklist(args.deck)

    if args.hands:
        sample_hands(deck, args)
        return

    args_d = {"rollouts": args.rollouts, "calib": args.calib}
    jobs = [(k, deck, args.games, args.seed, args.islands, args.on_draw, args_d) for k in args.policies]
    with Pool(min(len(jobs), args.jobs)) as pool:
        runs = pool.map(run_policy, jobs)
    report(runs, args)


if __name__ == "__main__":
    main()
