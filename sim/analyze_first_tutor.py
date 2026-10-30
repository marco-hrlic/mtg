"""Slice the per-state rows dumped by first_tutor.py --dump: what the lookahead picks, and the paired
Cradle - Selvala - Ashaya - Shang-Chi comparison inside each activation turn and board bucket."""
import json
import sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1]))
ARMS = ("current", "cradle", "selvala", "contextual", "lookahead")


def l4(x):
    return 1 if x and x["win"] is not None and x["win"] <= 4 else 0


def l5(x):
    return 1 if x and x["win"] is not None and x["win"] <= 5 else 0


def show(title, rs):
    print(f"\n{title} (n={len(rs)})")
    for arm in ARMS:
        av = [r for r in rs if r.get(arm)]
        if not av:
            continue
        print(f"  {arm:11s} n={len(av):4d}  lethal<=T4 {sum(l4(r[arm]) for r in av) / len(av):6.1%}"
              f"  lethal<=T5 {sum(l5(r[arm]) for r in av) / len(av):6.1%}")
    av = [r for r in rs if r.get("cradle") and r.get("selvala")]
    if av:
        d = [l4(r["cradle"]) - l4(r["selvala"]) for r in av]
        m = sum(d) / len(d)
        sd = (sum((x - m) ** 2 for x in d) / max(1, len(d) - 1)) ** .5
        print(f"  paired cradle-selvala T4: {m:+.1%} +- {1.96 * sd / len(d) ** .5:.1%}")
    picks = Counter(r["lookahead"]["fetched"] for r in rs if r.get("lookahead"))
    print("  lookahead picks: " + ", ".join(f"{k.split(',')[0]} {v / len(rs):.0%}" for k, v in picks.most_common(5)))


t3 = [r for r in rows if r["features"]["turn"] == 3]
show("ALL", rows)
show("activation on T3", t3)
for key, fn in (("T3, creatures 0-2", lambda f: f["creatures"] <= 2), ("T3, creatures 3+", lambda f: f["creatures"] >= 3),
                ("T3, land drop unused (always)", lambda f: f["land_drop"]),
                ("T3, white sources 1", lambda f: f["white"] == 1), ("T3, white sources 2+", lambda f: f["white"] >= 2),
                ("T3, untapper (Hope/Magus/Ranger/Flash) held", lambda f: f["untapper_have"]),
                ("T3, no untapper held", lambda f: not f["untapper_have"]),
                ("T3, Emiel or Flash held", lambda f: f["emiel_flash"]),
                ("T3, Cradle already held", lambda f: f["cradle_have"]),
                ("T3, hand size >=5", lambda f: f["hand_size"] >= 5), ("T3, hand size <=3", lambda f: f["hand_size"] <= 3)):
    show(key, [r for r in t3 if fn(r["features"])])

print("\nWhen the lookahead picked each target, how often it then won by T4 vs what cradle would have done:")
by = defaultdict(list)
for r in rows:
    if r.get("lookahead") and r.get("cradle"):
        by[r["lookahead"]["fetched"]].append(r)
for k, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f"  {k:32s} n={len(rs):4d}  lookahead T4 {sum(l4(r['lookahead']) for r in rs) / len(rs):6.1%}"
          f"  cradle-arm T4 {sum(l4(r['cradle']) for r in rs) / len(rs):6.1%}"
          f"  selvala-arm T4 {sum(l4(r['selvala']) for r in rs if r.get('selvala')) / max(1, sum(1 for r in rs if r.get('selvala'))):6.1%}")

print("\nFeatures when lookahead picked Selvala vs Cradle (T3 states):")
for tgt in ("Selvala, Heart of the Wilds", "Gaea's Cradle", "Ashaya, Soul of the Wild", "Shang-Chi, Master of Kung Fu"):
    rs = [r for r in t3 if r.get("lookahead") and r["lookahead"]["fetched"] == tgt]
    if not rs:
        continue
    f = [r["features"] for r in rs]
    n = len(f)
    print(f"  {tgt:32s} n={n:4d} creatures {sum(x['creatures'] for x in f) / n:.1f}  white {sum(x['white'] for x in f) / n:.1f}"
          f"  untapper held {sum(x['untapper_have'] for x in f) / n:.0%}  Emiel/Flash {sum(x['emiel_flash'] for x in f) / n:.0%}"
          f"  Cradle held {sum(x['cradle_have'] for x in f) / n:.0%}  hand {sum(x['hand_size'] for x in f) / n:.1f}")
