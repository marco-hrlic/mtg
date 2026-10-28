"""Run goldfish simulations and print how often / how fast each combo line wins.

    python3 sim/run.py --games 20000
    python3 sim/run.py --log 3          # print 3 annotated sample games
"""
import argparse
import os
import random
from collections import Counter

from cards import load_decklist
from engine import Game, LINES

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--deck", default=os.path.join(HERE, "decklist.txt"))
    ap.add_argument("--log", type=int, default=0, help="print N sample games instead of stats")
    args = ap.parse_args()

    deck = load_decklist(args.deck)
    rng = random.Random(args.seed)

    if args.log:
        for i in range(args.log):
            g = Game(deck, rng, log=True, max_turns=args.turns)
            r = g.play()
            print(f"===== game {i + 1}: " + (f"win T{r['win_turn']} via {r['line']}" if r["win_turn"] else "no win"))
            print("\n".join(g.logs))
            print()
        return

    results = [Game(deck, rng, max_turns=args.turns).play() for _ in range(args.games)]
    n = len(results)
    wins = [r for r in results if r["win_turn"]]

    print(f"{n} goldfish games, {args.turns} turns max, deck of {len(deck)}\n")
    print("Cumulative win rate by turn")
    by_turn = Counter(r["win_turn"] for r in wins)
    cum = 0
    for t in range(1, args.turns + 1):
        cum += by_turn[t]
        bar = "#" * round(50 * cum / n)
        print(f"  T{t}: {by_turn[t] / n:6.1%} this turn  {cum / n:6.1%} total  {bar}")
    avg = sum(r["win_turn"] for r in wins) / len(wins) if wins else 0
    print(f"  no win by T{args.turns}: {1 - len(wins) / n:.1%}   mean win turn: {avg:.2f}\n")

    print("Winning line (share of all games / of wins / mean turn)")
    lines = Counter(r["line"] for r in wins)
    for line in LINES:
        k = lines[line.name]
        if not k:
            continue
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


if __name__ == "__main__":
    main()
