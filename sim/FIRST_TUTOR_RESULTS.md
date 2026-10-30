# Captain Sisay — First Activation: Cradle vs Selvala

Paired counterfactual on real simulated games: when Sisay first activates, what should she fetch?
Companion to `RESULTS.md`; raw outputs in `sim/results/first_tutor_*.txt`, per-state rows reproducible
with `--dump`.

**Short answer.** Cradle beats Selvala by 7 points of turn-4 wins, and by 17 points when the activation
is on turn 3. But Cradle-first is not the best rule: fetch **Cradle when you already hold a nonlegendary
untapper, Ashaya when you don't, Cradle otherwise**. That rule beats plain Cradle-first by 1.7 points and
the pilot's own choice by 1.1. A rollout lookahead that tries every legend gains another 5.5 points, which
puts a ceiling on how much a hand-rule can recover. Selvala-first wins only in narrow states: Cradle is
already in hand or reachable by Crop Rotation, or the hand is nearly empty.

---

## 1. What changed in the engine first

The brief's rule list (section B) was checked against the engine before any measurement.

| Rule | Engine before | Engine now |
|---|---|---|
| Sisay tutors to hand; a fetched Cradle needs the land drop | correct, but the pilot activated at end step, so a fetched Cradle waited a turn and a fetched creature was cast a turn late | Sisay activates in the **first main phase** when able; Cradle is that turn's land, creatures are castable that turn |
| Library is shuffled after a search | **not shuffled** — a rollout policy could see upcoming draws | every search shuffles; the lookahead's advantage fell from +9.2 to +7.2 points when this was fixed |
| Kamahl's {G} gives no haste | attack count already used "controlled since turn start" | unchanged; wording in the combo map corrected |
| Concordant Crossroads gives animated lands haste | not counted | counted for the attack test |
| Toph earthbends on entry | no effect | animates Cradle with haste for the Emiel + Flash loop (a Sisay-fetchable animator) |
| Nature's Chosen | no effect | enchanted mana creature taps twice per turn (its {0} untap); the white-creature mode is not modelled |
| Emiel + Flash + Selvala at P = 4 is mana-neutral | correct | pinned by test D4.3 |
| Flash cannot untap an unanimated Cradle; Ashaya does not animate Cradle | correct | pinned by tests D4.6, D4.8 |
| Shang-Chi: ability haste only, no attacks | correct | pinned by test D4.13 |
| Crop Rotation puts Cradle into play without a land drop | correct | pinned by test D4.15 |

Still not modelled: command tax, Nature's Chosen on Sisay (opportunity cost of her tap), the Kamahl
"animate before overrun" sequencing (lethal is credited only with 3 bodies held since the turn began, so a
freshly animated land never counts), Toph's power. `python3 sim/tests.py` → 41/41.

**Re-benchmark after the pilot fix** (policy A, 20,000 games, 8 turns): lethal by T4 **21.9%** (was 19.3%),
by T5 **63.5%** (was 55.1%), by T6 83.0% (was 76.0%). Mulligan policies A/B/C re-run at 5,000 games:
lethal ≤T4 23.1% / 23.5% / 22.2%, still within each other's intervals. The failure ranking is unchanged:
no nonlegendary untapper (18.7%), Sisay too late (12.2%), short on mana (9.1%), no Cradle (8.5%).

---

## 2. Method

1. Play real games with the normal pilot (policy A mulligan) until the first turn on which Sisay can
   legally activate: untapped, not summoning sick (or Shang-Chi/Elixir/Crossroads in play), with a legendary
   card left to find. Freeze the game there, in the first main phase, before the land drop.
2. Continue identical copies of the frozen state, same random seed, one per arm:

| Arm | Fetch |
|---|---|
| `current` | the pilot's own rule: the missing legend of the closest line (Ashaya 61%, Emiel 14%, Cradle 11%, Selvala 9%) |
| `cradle` | Gaea's Cradle if in library, else the state is excluded from this arm |
| `selvala` | Selvala if in library, else excluded |
| `contextual` | the brief's section-C hierarchy |
| `rule2` | the rule fitted to the lookahead (section 5) |
| `lookahead` | every relevant legend in the library (Cradle, Selvala, Ashaya, Shang-Chi, Toph, Emiel, Flash, Kamahl), 4 rollouts each on seeds disjoint from the evaluation seed, highest utility |

3. Downstream play is the same pilot for every arm. Games run to turn 5.

Utility, as in the brief: `1.0·P(protected lethal ≤T4) + 0.35·P(lethal ≤T4) + 0.15·P(infinite ≤T4)`;
the lookahead adds `0.1·P(lethal ≤T5)` so it does not throw away turn-5 wins. All milestone rates are
reported raw. Protection-ready means a protection creature in play or Silence/Veil castable from spare mana.

5,000 games, seed 1, on the play, 0 opposing Islands: **3,195 states** (64% of games reach a first
activation by T5). Activation turn: T2 1%, **T3 33%**, T4 53%, T5 13%.

---

## 3. Results

### All first-activation states (n = 3,195)

| Arm | n | Lethal ≤T4 | Lethal ≤T5 | Protected ≤T4 | Infinite ≤T4 | Emiel line | Ashaya line | Utility |
|---|---|---|---|---|---|---|---|---|
| current | 3195 | 17.8% | 68.1% | 1.8% | 17.8% | 9.5% | 58.5% | 0.107 |
| cradle | 2869 | 18.5% | 65.7% | 3.9% | 18.5% | 7.2% | 58.5% | 0.132 |
| selvala | 2801 | 12.5% | 63.0% | 1.3% | 12.5% | 10.2% | 52.8% | 0.076 |
| contextual | 3195 | 17.8% | 65.0% | 3.8% | 17.8% | 7.1% | 57.9% | 0.127 |
| **rule2** | 3195 | **19.2%** | **68.6%** | 3.1% | 19.2% | 5.4% | 63.2% | 0.127 |
| lookahead | 3195 | **24.7%** | **78.5%** | 5.5% | 24.7% | 11.2% | 67.4% | 0.178 |

### Cohort: both Cradle and Selvala still in the library (n = 2,510)

| Arm | Lethal ≤T4 | Lethal ≤T5 | Protected ≤T4 | Utility |
|---|---|---|---|---|
| current | 19.7% | 69.2% | 2.0% | 0.119 |
| cradle | 19.2% | 65.9% | 4.1% | 0.136 |
| selvala | 12.1% | 62.4% | 1.2% | 0.072 |
| contextual | 19.2% | 65.9% | 4.1% | 0.136 |
| rule2 | 20.8% | 69.4% | 3.3% | 0.137 |
| lookahead | 26.3% | 79.0% | 5.7% | 0.189 |

### Paired differences on the cohort, P(lethal ≤T4), 95% CI

| Comparison | Difference |
|---|---|
| cradle − selvala | **+7.1** [+5.7, +8.5] |
| cradle − selvala, lethal ≤T5 | +3.5 [+1.7, +5.4] |
| current − cradle | +0.6 [−0.7, +1.8] (not significant) |
| contextual − cradle | 0.0 (the brief's hierarchy chose Cradle in 90% of states) |
| **rule2 − cradle** | **+1.7** [+0.6, +2.7] |
| **rule2 − current** | **+1.1** [+0.3, +1.9] |
| lookahead − cradle | +7.2 [+6.1, +8.3] |
| lookahead − rule2 | +5.5 [+4.5, +6.5] |

**Fetched Selvala could not tap that turn in 100% of `selvala` states** (no haste source was ever in play
at a first activation). Fetched Cradle was never stranded, because the activation happens before the land
drop. With 2 opposing Islands (Carpet of Flowers, 3,000 games): cradle − selvala +7.0 [+5.1, +8.9],
lookahead − cradle +8.5; same picture.

### By activation turn

Turn 3 is where the decision matters: a T4 activation almost never converts into a T4 lethal whatever is
fetched (2–4%), and T5 activations never do.

| T3 activations (n = 1,068) | current | cradle | selvala | rule2 | lookahead |
|---|---|---|---|---|---|
| Lethal ≤T4 | 49.6% | 50.0% | 34.5% | **53.6%** | 66.1% |
| Lethal ≤T5 | 85.6% | 80.6% | 86.0% | 84.9% | 89.7% |

Paired cradle − selvala at T3: **+16.6 ± 3.5**. Note Selvala catches up by T5 (86.0 vs 80.6): fetching
Selvala costs a turn, it does not cost the game.

### Stratified, T3 activations, P(lethal ≤T4)

| Bucket | n | current | cradle | selvala | rule2 | lookahead | Lookahead picks |
|---|---|---|---|---|---|---|---|
| Untapper held (Hope/Magus/Ranger/Flash) | 339 | 65.2% | **75.0%** | 56.5% | 75.5% | 84.1% | Cradle 68%, Selvala 18% |
| No untapper held | 729 | **42.4%** | 38.3% | 24.1% | 43.3% | 57.8% | Cradle 45%, Ashaya 20%, Selvala 12%, Shang-Chi 11% |
| … and pilot would fetch Ashaya | 683 | **54.6%** | 46.1% | 35.4% | — | 66.2% | |
| … and pilot would fetch Selvala/Emiel/Flash | 128 | 30% | **63%** | 20% | — | 75% | |
| Creatures 0–1 | 282 | 39.7% | 41.5% | 22.7% | — | 57.1% | |
| Creatures 2 | 535 | 56.3% | 53.8% | 36.6% | — | 71.6% | |
| Creatures 3+ | 92 | 54.3% | 48.8% | 42.7% | — | 68.5% | Cradle 47%, Selvala 20% |
| White sources 1 | 298 | 46.3% | 50.9% | 36.5% | — | 63.8% | |
| White sources 2+ | 767 | 51.1% | 49.6% | 33.9% | — | 67.0% | |
| Hand ≥5 cards | 792 | 49.4% | 52.6% | 34.3% | — | 67.7% | |
| Hand ≤3 cards | 91 | 46.2% | 31.8% | 32.6% | — | 59.3% | Cradle 34%, Ashaya 27%, Selvala 20% |
| Cradle already held | 87 | 55.2% | — | 54.3% | — | 67.8% | **Selvala 52%**, Ashaya 21%, Shang-Chi 10% |

Creature count and white sources barely move the Cradle/Selvala gap. What moves it is **whether the
nonlegendary untapper is already in hand**: with one, Cradle is +10 over the pilot's Ashaya-first; without
one, Ashaya-first is +4 over Cradle because the deck needs Ashaya more than it needs mana.

### When the lookahead chose each target (all states)

| Lookahead picked | n | Lookahead ≤T4 | Cradle arm ≤T4 | Selvala arm ≤T4 |
|---|---|---|---|---|
| Gaea's Cradle | 1982 | 22.4% | 22.4% | 11.3% |
| Ashaya | 313 | 39.9% | 8.6% | 9.4% |
| Selvala | 269 | 20.8% | 7.8% | 20.8% |
| Shang-Chi | 172 | 29.1% | 12.8% | 11.9% |
| Emiel | 71 | 28.2% | 11.3% | 6.5% |
| Toph | 28 | 28.6% | 14.3% | 16.0% |
| Flash | 27 | 33.3% | 14.8% | 15.0% |

When the lookahead deviates from Cradle it is usually because Cradle would have been close to useless in
that state (8–13% T4), not because the alternative is spectacular.

### Why there was no T4 lethal (share of each arm's non-winning states)

| Reason | current | cradle | selvala | rule2 | lookahead |
|---|---|---|---|---|---|
| No nonlegendary untapper | 30.1% | 26.9% | 23.6% | 36.7% | 26.3% |
| No engine (Ashaya/Emiel) | 9.6% | **40.4%** | **47.3%** | 23.3% | 41.1% |
| No haste for a sick tapper | 13.4% | 8.8% | 6.3% | 9.6% | 8.7% |
| No Cradle / mana source | 13.7% | 1.1% | 1.1% | 5.1% | 3.6% |
| Short on mana | 13.9% | 3.8% | 12.6% | 5.5% | 5.9% |
| Missing white | 10.6% | 4.4% | 5.7% | 4.7% | 4.8% |
| Pieces in hand, not castable | 8.8% | 14.6% | 3.3% | 15.1% | 9.6% |

Fetching Cradle trades "short on mana" for "no engine". Fetching Selvala does neither job: it still leaves
the deck short on mana (12.6%) **and** without an engine (47.3%).

---

## 4. Counterexamples (full traces in `sim/results/first_tutor_divergences.txt`)

**Cradle wins, Selvala loses**

- *Game 0.* T3, Brushland, Elvish Mystic, Boseiju, Sisay; hand Ashaya, Nykthos, Bloom Tender, Chord,
  Arbor Elf, Mana Vault. Cradle → play it, Vault, Bloom Tender, Ashaya on T3; T4 Chord for Hope Tender,
  Sisay for Shang-Chi, Ashaya + Hope + Cradle. Selvala → Nykthos as the land, Selvala cast and sick; Ashaya
  only on T4; the same Chord line lands on T5.
- *Game 13.* Hand Bloom Tender, Badgermole Cub, Emerald Charm, Verdant Touch, two lands. Cradle → T4 Sisay
  finds Ashaya, Formidable Speaker finds Quirion, Ashaya + Quirion + Bloom. Selvala → T4 Sisay must find
  Emiel instead, Emiel + Flash + Selvala on T5.
- *Game 43.* Hand Hope Tender, GSZ, Scryb Ranger, Sylvan Scrying. Cradle in hand T3; T4 Sisay finds
  Ashaya, Ashaya + Hope + Cradle with GSZ → Kamahl. Selvala → T4 is spent casting her; Cradle arrives T5.
- *Game 156.* Four-card hand with Ashaya and Eladamri's Call. Cradle → Ashaya and Call → Hope on T3; T4 Sisay
  finds Shang-Chi for haste, win. Selvala → no Cradle, no mana, T5.

**Selvala wins, Cradle loses**

- *Game 158.* Hand Finale, Eldritch Evolution, **Crop Rotation**, Voice of Victory, two lands; one
  creature. Selvala → T3 Selvala + Voice; T4 Eldritch (sac Voice) → Ashaya, Finale → Hope, **Crop Rotation →
  Cradle**, Sisay → Shang-Chi: protected win. Cradle → the pilot holds Cradle (one creature), finds Ashaya
  T4, has no second creature to Eldritch into Hope, wins T5. Independent Cradle access made Cradle the
  wrong tutor.
- *Game 137.* Yavimaya + Sol Ring + Pilgrim; hand Flash, Formidable Speaker, Elixir, Emerald Charm.
  Selvala → T3 Selvala, Elixir, Flash; T4 Speaker finds Emiel, Sisay finds Cradle, Emiel + Flash + Arbor
  Elf + Cradle (Yavimaya makes Cradle a Forest). Cradle → Speaker finds Ashaya instead, Nykthos T4, no
  untapper that taps Cradle, T5+.
- *Game 119.* Four-card hand of Bloom Tender, Cub, Marvin, Spider-Man. Selvala → T4 Sisay finds Ashaya,
  Eldritch → Quirion, Ashaya + Quirion + Bloom. Cradle → T3 Cradle makes the pilot overcommit (Spider-Man,
  Marvin), T4 Ashaya but no untapper, wins T5 protected.

Pattern: Selvala-first wins when (a) Cradle is reachable some other way, (b) the hand is thin and a body
with power matters more than mana, or (c) the engine in hand is Emiel/Flash-shaped. In every other state
the extra turn Selvala costs is the turn that mattered.

---

## 5. Pilot decision tree for the first Sisay activation

```
Sisay can activate, first main phase, land drop unused
│
├─ Hold a nonlegendary untapper (Hope, Magus, Quirion, Scryb, or Flash)?
│    └─ yes → GAEA'S CRADLE.  Play it as the land. (75% T4 at T3 vs 65% for anything else)
│
├─ Ashaya not in hand or play, still in library?
│    └─ yes → ASHAYA.  Cast her this turn if you can.  (55% vs 46% for Cradle)
│
├─ Cradle still in library?
│    └─ yes → GAEA'S CRADLE.
│
├─ Cradle already held, Hope/Magus in play but summoning sick, no haste source?
│    └─ yes → SHANG-CHI.
│
├─ Cradle already held → SELVALA (the lookahead's top pick, 52%),
│                        then Toph if Emiel + Flash are held and Cradle needs animating,
│                        then KAMAHL.
│
└─ Exceptions the rule does not capture (lookahead only):
     Crop Rotation / Sylvan Scrying in hand → treat Cradle as held.
     Hand ≤3 cards and no engine → Ashaya over Cradle.
     Emiel + Flash both held and a 4-power body in play → Cradle for the animated-Cradle loop,
       Selvala only with Cub in play.
```

Second activation: whatever the first one did not get, in the order Ashaya → Cradle → Shang-Chi (if a
tapper is sick) → Kamahl. Never fetch Selvala before Ashaya and Cradle unless the Emiel loop is already
live.

---

## 6. Caveats

- The lookahead's +5.5 over `rule2` is the gap a hand-rule leaves on the table. It is a real policy (its
  picks are evaluated on seeds it never saw) but it uses the simulator's pilot as its model of the future.
- No opponents. Selvala is also a creature that dies to removal and a white source against stax; none of
  that is here.
- Protected-lethal is a floor: the pilot casts protection last.
- The `selvala` arm's 100% "summoning sick" is a property of these states (no haste source ever in play at
  a first activation), not of Selvala.
- **Policy-D (rollout mulligan) states** (800 games → 421 states, 44% of them T3 activations because D
  mulligans harder): the ordering holds and the gaps widen. Cohort n = 361: cradle − selvala **+10.2**
  [+6.2, +14.3]; rule2 − cradle +3.3 [−0.0, +6.7]; lookahead − cradle +9.1; lookahead − rule2 +5.8.
  Lethal ≤T4 over all D states: current 27.3%, cradle 25.9%, selvala 16.3%, rule2 28.3%, lookahead 34.2%.
  Selection bias runs the expected way: hands kept by D hold more engine pieces, so the "untapper already
  held → Cradle" branch fires more often and Selvala-first costs more.

---

## 7. Reproduce

```
python3 sim/tests.py                                               # 41 rulings
python3 sim/first_tutor.py --games 5000 --seed 1 --dump rows.json   # main table (~5 min on 4 cores)
python3 sim/analyze_first_tutor.py rows.json                        # slices by turn / untapper / hand size
python3 sim/first_tutor.py --games 3000 --seed 1 --islands 2
python3 sim/first_tutor.py --games 2000 --seed 5 --arms cradle selvala lookahead --divergences 12
python3 sim/run.py --games 20000 --seed 7                           # re-benchmark after the pilot fix
python3 sim/experiment.py --games 5000 --policies A B C --jobs 3
```
