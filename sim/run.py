"""Run goldfish simulations and print how often / how fast each combo line wins.

    python3 sim/run.py --games 20000
    python3 sim/run.py --log 3                                   # annotated sample games
    python3 sim/run.py --remove "Gaea's Cradle"                  # cut a card (replaced by a blank)
    python3 sim/run.py --remove "Vitalize" --add "Argothian Elder"
    python3 sim/run.py --ablate --games 3000                     # value of every card, one at a time

Every game i uses seed (--seed, i) and removed cards are swapped in place, so a variant
deck sees exactly the same shuffles as the baseline. Differences are therefore due to the
change itself, not to luck, which makes small effects measurable.
"""
import argparse
import os
import random
from collections import Counter
from multiprocessing import Pool

from cards import COMMANDER, load_decklist, swap
from engine import Game, LINES

HERE = os.path.dirname(os.path.abspath(__file__))


def simulate(deck, games, seed, turns):
    return [Game(deck, random.Random(seed * 1_000_003 + i), max_turns=turns).play() for i in range(games)]


def _sim_job(args):
    label, deck, games, seed, turns = args
    return label, summarize(simulate(deck, games, seed, turns), turns)


def summarize(results, turns):
    n = len(results)
    capped = [r["win_turn"] or turns + 1 for r in results]
    return {
        "n": n,
        "by4": sum(t <= 4 for t in capped) / n,
        "by5": sum(t <= 5 for t in capped) / n,
        "by6": sum(t <= 6 for t in capped) / n,
        "mean": sum(capped) / n,
    }


def report(results, turns, deck):
    n = len(results)
    wins = [r for r in results if r["win_turn"]]
    print(f"{n} goldfish games, {turns} turns max, deck of {len(deck)}\n")
    print("Cumulative win rate by turn")
    by_turn = Counter(r["win_turn"] for r in wins)
    cum = 0
    for t in range(1, turns + 1):
        cum += by_turn[t]
        bar = "#" * round(50 * cum / n)
        print(f"  T{t}: {by_turn[t] / n:6.1%} this turn  {cum / n:6.1%} total  {bar}")
    avg = sum(r["win_turn"] for r in wins) / len(wins) if wins else 0
    print(f"  no win by T{turns}: {1 - len(wins) / n:.1%}   mean win turn: {avg:.2f}\n")
    if not wins:
        return

    print("Winning line (share of all games / of wins / mean turn)")
    lines = Counter(r["line"] for r in wins)
    for line in LINES:
        k = lines[line.name]
        if k:
            mean = sum(r["win_turn"] for r in wins if r["line"] == line.name) / k
            print(f"  {line.name:24s} {k / n:6.1%}  {k / len(wins):6.1%}  T{mean:.2f}")
    print()

    print("Lines live on the winning turn (several can be live at once)")
    print(f"  {'line':24s} {'live in % of wins':>18s} {'only line live':>15s}")
    live = Counter(l for r in wins for l in r["available"])
    only = Counter(r["available"][0] for r in wins if len(r["available"]) == 1)
    for line in LINES:
        if live[line.name]:
            print(f"  {line.name:24s} {live[line.name] / len(wins):18.1%} {only[line.name] / len(wins):15.1%}")
    print()

    print("How missing pieces were found on the winning turn (per win)")
    uses = Counter(u for r in wins for u in r["uses"])
    for u, k in uses.most_common():
        print(f"  {u:24s} {k / len(wins):6.1%}")
    print()

    noout = [r for r in results if r["noout_turn"] and (not r["win_turn"] or r["noout_turn"] < r["win_turn"])]
    print(f"Games that had infinite mana but no outlet first: {len(noout) / n:.1%}")
    mulls = Counter(r["mulligans"] for r in results)
    print("Mulligans: " + ", ".join(f"{k}: {v / n:.1%}" for k, v in sorted(mulls.items())))


def ablate(deck, args):
    names = sorted({c.name for c in deck if c.name != COMMANDER})
    jobs = [("baseline", deck, args.games, args.seed, args.turns)]
    jobs += [(name, swap(deck, [name]), args.games, args.seed, args.turns) for name in names]
    with Pool(args.jobs) as pool:
        out = dict(pool.map(_sim_job, jobs))
    base = out.pop("baseline")
    print(f"Card value: each card replaced by a blank, {args.games} identical-shuffle games per variant.")
    print(f"Baseline: win by T4 {base['by4']:.1%}, by T5 {base['by5']:.1%}, by T6 {base['by6']:.1%}, "
          f"mean win turn {base['mean']:.2f} (no win = T{args.turns + 1})\n")
    print(f"  {'card cut':34s} {'dT4':>7s} {'dT5':>7s} {'dT6':>7s} {'d mean turn':>12s}")
    rows = sorted(out.items(), key=lambda kv: kv[1]["mean"], reverse=True)
    for name, s in rows:
        print(f"  {name:34s} {s['by4'] - base['by4']:+7.1%} {s['by5'] - base['by5']:+7.1%} "
              f"{s['by6'] - base['by6']:+7.1%} {s['mean'] - base['mean']:+12.3f}")
    print("\nPositive d mean turn = the deck gets slower without the card (the card is pulling weight).")
    print("Interaction/protection cards show ~0 here by construction: a goldfish has no opponents.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--deck", default=os.path.join(HERE, "decklist.txt"))
    ap.add_argument("--remove", action="append", default=[], help="card to cut (repeatable)")
    ap.add_argument("--add", action="append", default=[], help="card to put in for a cut (repeatable)")
    ap.add_argument("--compare", action="store_true", help="also run the unmodified deck and show the difference")
    ap.add_argument("--ablate", action="store_true", help="measure every card by cutting it")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--log", type=int, default=0, help="print N sample games instead of stats")
    args = ap.parse_args()

    base_deck = load_decklist(args.deck)
    deck = swap(base_deck, args.remove, args.add)

    if args.ablate:
        ablate(deck, args)
        return

    if args.log:
        for i in range(args.log):
            g = Game(deck, random.Random(args.seed * 1_000_003 + i), log=True, max_turns=args.turns)
            r = g.play()
            print(f"===== game {i + 1}: " + (f"win T{r['win_turn']} via {r['line']}" if r["win_turn"] else "no win"))
            print("\n".join(g.logs))
            print()
        return

    if args.compare and (args.remove or args.add):
        jobs = [("baseline", base_deck, args.games, args.seed, args.turns),
                ("variant", deck, args.games, args.seed, args.turns)]
        with Pool(min(2, args.jobs)) as pool:
            out = dict(pool.map(_sim_job, jobs))
        b, v = out["baseline"], out["variant"]
        print(f"Variant: -{', -'.join(args.remove)}" + (f"  +{', +'.join(args.add)}" if args.add else ""))
        for k, label in (("by4", "win by T4"), ("by5", "win by T5"), ("by6", "win by T6")):
            print(f"  {label}: {b[k]:.1%} -> {v[k]:.1%} ({v[k] - b[k]:+.1%})")
        print(f"  mean win turn: {b['mean']:.2f} -> {v['mean']:.2f} ({v['mean'] - b['mean']:+.3f})")
        return

    report(simulate(deck, args.games, args.seed, args.turns), args.turns, deck)


if __name__ == "__main__":
    main()
