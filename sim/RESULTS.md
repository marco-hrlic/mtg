# Captain Sisay — Cradle Turbo: Simulation Results

Goldfish (no opponents) Monte Carlo study of the Captain Sisay cEDH list: which combo lines exist,
how often and how fast they assemble, which cards carry the deck, and which London-mulligan policy
produces the most turn-4 wins. All numbers come from `sim/` in this repository; raw outputs are in
`sim/results/`.

**Read this first.** Everything here is an upper bound on speed and a floor on protection. Nobody
interacts with the deck, the pilot is a heuristic that plans one turn ahead, and "protected" only
means a protection piece was in play or castable from spare mana. Trust the comparisons and the
failure ranking more than the absolute rates.

---

## 1. Deck

The brief's provisional list and the simulator's `decklist.txt` are the same 99 + Captain Sisay.
Four names differ only by printing:

| Brief | Simulator (same card) |
|---|---|
| Lifelong Friendship | Eladamri's Call |
| Paths of the Dead | Cavern of Souls |
| Carpet of Flowers | Fal'Cie Paradise |
| Drannith Magistrate | Mayor Tong of Chin Village |

Validated: 100 cards, 1 commander, 99 in library, unique names except 2 Forest, all cards G/W or
colorless. The suggested but unconfirmed swaps (Nykthos → Wooded Bastion, Forest → Mana Confluence,
To Arms!, Village Bell-Ringer) were **not** applied.

---

## 2. Combo lines modelled

Every infinite in the deck has the same shape: an **untapper** untaps a **mana source** that makes
more than the untap costs. The untapper must be able to untap *itself* too, which Ashaya and Emiel each
solve differently. Any loop can untap Sisay instead, which turns infinite mana into every legendary
card and then Kamahl.

### Engine A — Ashaya (creatures are Forest lands)

| Untapper | Per pass | Gaea's Cradle | Nykthos | Selvala | Bloom Tender | Badgermole Cub | Fanatic |
|---|---|---|---|---|---|---|---|
| Hope Tender (taps) | {1}, exert | 2+ creatures | devotion 4+ | power 3+ | W permanent | untap a dork, +G | — |
| Magus of the Candelabra (taps) | {X}=2 | 3+ creatures | devotion 5+ | power 4+ | — | X=3, two dorks | — |
| Quirion Ranger (recast {G}) | return self | — | — | power 3+ | W permanent | untap a dork | power 4+ |
| Scryb Ranger (recast {1G}) | return self | — | — | power 4+ | — | — | power 4+ |

Hope and Magus tap, so they need haste (Concordant Crossroads, Thousand-Year Elixir, Shang-Chi,
Greaves) or a turn in play. The Rangers return themselves to hand as the Forest and are new objects
when recast, so "once each turn" never binds; they never tap, so no haste.

Special case: **Ashaya + Hope Tender + Shang-Chi + Sisay.** Shang-Chi's two mana pays only for creature
abilities, which includes Hope's untap and Sisay's tutor. Unlimited Sisay activations fetch Selvala,
and the same engine then makes real mana. Shang-Chi grants haste to abilities, so neither Hope nor
Sisay needs to wait a turn.

### Engine B — Emiel (blink instead of untap)

Emiel pays {3} to blink Flash Thompson; Flash's ETB untaps a creature. None of this needs Ashaya and
nothing taps, so no haste is needed. Targets:

| Target | Needs |
|---|---|
| Fanatic of Rhonas | nothing — Emiel is a 4/4, Fanatic makes GGGG |
| Selvala | power 5+ in play: Badgermole Cub (Emiel 4 + 1) or Ashaya |
| Gaea's Cradle as a creature | 4+ creatures; animate with Cub's earthbend (haste), Kamahl {G}, Animate Land or Verdant Touch (the last two only on a Cradle held since the turn began) |
| A land-untapper creature → Cradle | 4+ creatures: Voyaging Satyr, Arbor Elf + Yavimaya; 5+: Hope Tender, Magus |
| Voyaging Satyr → Nykthos | devotion 6+ |

With a haste source in play, blink the mana creature itself and skip Flash.

### Finish

Infinite mana → Sisay (untapped or re-bought each pass) → **Kamahl, Fist of Krosa**: {G} per land makes
it a 1/1 (no haste), then {2}{G}{G}{G} for +3/+3 and trample as often as needed. Lethal is credited
only with **3 bodies controlled since the turn began** (one per opponent) and Kamahl castable or in play.
**Finale of Devastation** for X ≥ 10 is the only other finisher. Walking Ballista was tested and
excluded per the brief.

### Not infinite

Formidable Speaker, Thousand-Year Elixir, Voyaging Satyr, Arbor Elf and Marvin on their own tap
themselves to untap one thing, so there is never a spare untap. Nature's Chosen is once per turn in
both modes. Vitalize and Emerald Charm are one-shot bursts and are modelled as such on the win turn.

---

## 3. Engine credibility work

### Rulings fixed before the experiments

| Issue | Before | After |
|---|---|---|
| Lethal without attackers | infinite mana + Kamahl counted as a win | needs 3 bodies held since turn start; a loop can untap them |
| Sisay-fetched Cradle with the land drop spent | credited | blocked (`drop` is consumed when the land drop is gone) |
| Emiel lines | depended on Ashaya for power | Emiel's own power 4 turns on Fanatic; Selvala needs Cub or Ashaya |
| Outlet with Kamahl gone | any leftover tutor counted | tutor must have a finisher left to find |
| Emiel + Flash + animated Cradle, Emiel + Flash + untapper + Cradle | not modelled | modelled with fresh-Cradle / haste rules |
| Quirion / Scryb under Ashaya | once-per-turn, so ignored | self-return + recast loop |

Also added: Carpet of Flowers scenario (`--islands 0/1/2`), Gemstone Caverns on the draw (`--on-draw`),
Vitalize / Emerald Charm bursts, per-game milestones, and a primary failure reason at T4.

### Golden tests (`python3 sim/tests.py`, 26/26 pass)

Deterministic board states the planner must rule on, with a library that holds only the named cards so
a test cannot pass by tutoring something it did not list. Examples:

- Ashaya + Hope + Cradle with Hope summoning sick and no haste → no win; with Concordant Crossroads, or
  with Shang-Chi fetchable by Sisay → win.
- Hope + Cradle without Ashaya → no win (Hope cannot untap itself); with Ashaya in library and 9 mana →
  Sisay fetches and casts her → win.
- Sisay fetches Cradle to hand with the land drop spent → no win.
- Emiel in hand with six Forests → no win (WW); with Savannah + Plains → win.
- Animate Land on a Cradle played this turn → no win; Badgermole Cub's earthbend on the same Cradle → win.
- Infinite mana, Kamahl in hand, two bodies held since turn start → not lethal; three → lethal.
- Formidable Speaker + Elixir + Cradle → no; Quirion + Selvala without Ashaya → no.

### What is still an abstraction

- Loop detection is **line-based**: `engine.LINES` names each infinite with its pieces, tapping piece,
  startup cost and condition. The planner checks routes, mana, colors, land drop and haste against that
  list. It does not derive loops from first principles; a line not in the list is never credited.
- Command tax is not tracked (Sisay is cast once in a goldfish game).
- Nature's Chosen and Toph have no modelled effect (Toph's printed text could not be verified).
- Protection: only *protection-ready* is measurable without opponents. The pilot casts protection last,
  so this is a floor.

---

## 4. Baseline goldfish (policy A, 20,000 games, 8 turns)

| Turn | Wins that turn | Cumulative |
|---|---|---|
| T3 | 0.7% | 0.7% |
| T4 | 18.6% | 19.3% |
| T5 | 35.8% | 55.1% |
| T6 | 20.9% | 76.0% |
| T7 | 9.7% | 85.7% |
| T8 | 6.6% | 92.3% |

Mean win turn 5.4. Lines live on the winning turn (several are usually live at once; 3,000-game run
with the full line set):

| Line | Live in % of wins | Only line live |
|---|---|---|
| Ashaya + Hope + Cradle | 56% | 5.2% |
| Ashaya + Magus + Cradle | 55% | 5.7% |
| Ashaya + Hope + Nykthos | 30% | 0.3% |
| Ashaya + Magus + Nykthos | 27% | 0.2% |
| Ashaya + Hope + Shang-Chi | 26% | 0.6% |
| Emiel + Flash + Cradle + Cub | 17% | 2.9% |
| Ashaya + Quirion + Selvala | 16% | 2.0% |
| Ashaya + Scryb + Selvala | 12% | 2.1% |
| Emiel + Fanatic + haste | 11% | 0.7% |
| Emiel + Flash + Satyr + Cradle | 10% | 1.0% |
| Emiel + Selvala + haste | 10% | 2.1% |

Reading: Ashaya + a tap-untapper + Cradle is the deck. Nykthos, Selvala, Bloom and Cub are redundancy
rather than new wins. The Emiel package is the only plan without Ashaya and is the sole live line in
about 1 win in 10.

---

## 5. Card value (ablation, 3,000 identical-shuffle games per cut)

Each card replaced by a blank; the deck gets slower by the amount shown. Interaction and protection
cards score about zero by construction.

| Card cut | Δ wins by T5 | Note |
|---|---|---|
| Ashaya | −57 pts | every Ashaya line |
| Kamahl | −51 pts | the finisher nearly every line ends on |
| Shang-Chi | −12 pts | haste source Sisay can fetch, plus its own line |
| Magus, Hope Tender | −6 pts each | |
| Selvala | −1.5 pts (−4.7 by T6) | |
| Quirion Ranger, Summoner's Pact, Ranger-Captain | −3 pts each | |
| Emiel | −1.4 pts (−3.7 by T6) | backup plan, so it hides behind Ashaya |
| Fal'Cie Paradise, Nature's Chosen, Animate Land, Verdant Touch, Vitalize, Toph, Marvin | ~0 | cutting all seven together: −0.6 pts |

Resilience, not speed, is what the backup lines buy: cut Ashaya and wins by T6 fall from 79% to 35%;
cut Ashaya **and** Emiel and they fall to 0%. Cut Kamahl alone and wins by T6 fall to 8%.

Swaps tested on identical shuffles (wins by T5, from 55.6%):

| Swap | Δ T4 | Δ T5 |
|---|---|---|
| + Argothian Elder, − Fal'Cie Paradise | +1.2 | +2.5 |
| + Devoted Druid + Vizier of Remedies, − Animate Land − Verdant Touch | +1.9 | +1.7 |
| + Ezuri, Renegade Leader (second legendary finisher), − Vitalize | 0.0 | +0.1 (restores wins by T6 from 8% to 31% when Kamahl is gone) |
| + Umbral Mantle | −0.5 | −1.3 |
| + Elvish Reclaimer, + Gilded Goose | ±0.2 | ±0.2 |

The brief asks to keep Voice of Victory, the untap spells and the land animators; none of those is a
measured liability in a goldfish, so no cut is recommended from these numbers alone.

---

## 6. Mulligan policies

### Setup

London mulligan, 4-player Commander: draw 7, the first mulligan is free, each later one bottoms a card
after the final draw. Game *i* of every policy starts from library shuffle (seed, *i*), so differences
are the policy, not the deck order. Six turns per game. 95% Wilson intervals in brackets.

| Policy | Keep logic | Bottoming |
|---|---|---|
| A heuristic | green land; 1–4 lands; ≥3 real mana sources (Mox Diamond needs a spare land, Chrome Mox an imprint); T2 mana ≥3 or an engine piece / tutor; ≤2 dead cards | dead cards, surplus lands beyond 3, pilot's worst card |
| B fast Sisay | Sisay castable T2 with a white source, or T3 with an engine piece / tutor / Cradle access | same |
| C Cradle-first | ≥2 bodies and Cradle access (Cradle, Crop Rotation, Sylvan Scrying, Knight, or Sisay by T3) | same |
| D rollout | plays the hand forward with the pilot (5 rollouts) and keeps when the estimate beats the calibrated value of mulliganing; bottoming by trying each card | by rollout |

Objective used by D and reported for all: `1.0·P(protected lethal ≤T4) + 0.35·P(lethal ≤T4) + 0.15·P(infinite ≤T4)`.

### Results (A–C: 5,000 games each; D: 1,500)

| Policy | Keep 7/6/5/4 % | Sisay ≤T2 | 1st act ≤T3 | Infinite ≤T4 | Lethal ≤T3 | Lethal ≤T4 | Protected ≤T4 | Utility | Mulls/game |
|---|---|---|---|---|---|---|---|---|---|
| A heuristic | 81/14/4/1 | 23.5% [22.4–24.7] | 29.5% [28.2–30.8] | 21.0% [19.9–22.1] | 0.7% | **20.6%** [19.5–21.8] | 2.9% [2.5–3.4] | 0.133 | 0.69 |
| B fast Sisay | 48/16/22/13 | 27.3% [26.1–28.5] | 32.0% [30.7–33.3] | 20.5% [19.4–21.6] | 0.7% | 20.3% [19.2–21.5] | 2.9% [2.5–3.4] | 0.131 | 1.72 |
| C Cradle-first | 62/21/13/4 | 22.8% [21.6–24.0] | 27.8% [26.5–29.0] | 20.4% [19.3–21.5] | 0.7% | 20.1% [19.0–21.2] | 3.0% [2.6–3.6] | 0.131 | 1.20 |
| D rollout | 41/24/15/20 | 24.5% [22.4–26.7] | 31.5% [29.2–33.9] | 26.6% [24.4–28.9] | 1.1% | **26.0%** [23.8–28.3] | 4.3% [3.4–5.4] | 0.174 | 1.91 |

Findings:

1. **A, B and C are statistically identical** on lethal ≤T4. Keep rules that look very different (B
   keeps only 48% of sevens, A 81%) land within one point of each other. B raises Sisay-by-T2 by four
   points and gains nothing at T4 for it.
2. **D is better by 5.4 points** at T4 and the intervals do not overlap. It gets there by mulliganing
   almost twice per game and ending on four cards 20% of the time. Its objective ignores wins after
   T4, so it discards hands that win on T5 reliably; its estimates use five rollouts, so marginal hands
   are biased toward the mulligan. It shows what aggressive mulliganing buys at T4, not what to do at
   a real table.
3. Calibrated value of mulliganing (policy D): V[7 after free mull] = 0.196, V[6] = 0.120,
   V[5] = 0.079, V[4] = 0.036. A seven is worth keeping when its rollout estimate beats 0.196.

### Scenarios (policy A, 3,000 games each)

| Scenario | Sisay ≤T2 | Lethal ≤T3 | Lethal ≤T4 | Protected ≤T4 |
|---|---|---|---|---|
| On the play, 0 Islands (baseline) | 23.5% | 0.7% | 20.6% | 2.9% |
| On the draw, 0 Islands | 24.8% | 0.9% | 21.0% | 3.1% |
| 1 opposing Island (Carpet) | 25.2% | 0.8% | 22.3% | 3.4% |
| 2 opposing Islands | 28.8% | 1.8% | 24.4% | 4.0% |

Carpet of Flowers is worth about one point of T4 wins per Island and doubles T3 wins at two Islands.
Being on the draw changes nothing measurable.

### Why there is no lethal by turn 4 (share of all games)

| Primary reason | A | B | C | D |
|---|---|---|---|---|
| No nonlegendary untapper in hand or play | **19.4%** | 20.6% | 19.0% | 17.5% |
| Sisay not cast by T3 | 12.3% | 17.1% | 16.6% | 20.9% |
| No Cradle / mana source | 9.9% | 9.0% | 9.1% | 7.3% |
| Missing white for Emiel / Flash in hand | 9.1% | 6.5% | 8.2% | 5.1% |
| Pieces assembled, short on mana | 8.9% | 8.5% | 8.4% | 7.0% |
| Pieces in hand, not castable | 7.2% | 6.7% | 7.0% | 5.8% |
| No engine (neither Ashaya nor Emiel) | 6.8% | 5.9% | 6.5% | 5.8% |
| Tapping untapper summoning sick, no haste | 5.4% | 5.3% | 4.9% | 4.0% |
| Infinite mana but no outlet | 0.3% | 0.2% | 0.3% | 0.6% |

**The limiting resource is a nonlegendary untapper.** Sisay finds Ashaya, Cradle, Selvala, Shang-Chi and
Kamahl; Hope Tender, Magus, Quirion and Scryb come only from the draw or the creature tutors. White is a
real but second-order bottleneck (9% of games) and shrinks under any policy that mulligans hands without
a white source. Raw mana is third.

---

## 7. Opening hands

Fourteen sevens shown to all four policies (seed 3; D with 12 rollouts). Full list in
`sim/results/opening_hands.txt`.

**Flashy keeps that lose to the free mulligan** (D estimate vs 0.242 for mulliganing):

| Hand | A | B | C | D |
|---|---|---|---|---|
| Gaea's Cradle, Quirion Ranger, Branchloft Pathway, Flash Thompson, Vitalize, Wild Growth, Arbor Elf | keep | keep | keep | mull (0.00) — one real land, no white, Cradle is dead for two turns |
| Boseiju, Scryb Ranger, Avacyn's Pilgrim, Boromir, Arbor Elf, Lightning Greaves, Birds of Paradise | keep | keep | keep | mull (0.00) — three dorks on one land |
| Ancient Tomb, Wooded Foothills, Sylvan Scrying, Emiel, Mox Diamond, Wall of Roots, Scryb Ranger | keep | mull | keep | mull (0.13) — Emiel with no white source |

**Unflashy keeps the rollout likes:**

| Hand | A | B | C | D |
|---|---|---|---|---|
| Forest, Mana Vault, Shang-Chi, Llanowar Elves, Wooded Foothills, Mox Diamond, Crop Rotation | keep | keep | keep | keep (0.33) — two lands, Vault, dork, Crop Rotation finds Cradle |
| Eiganjo, Nykthos, Sylvan Tutor, Verdant Catacombs, Voyaging Satyr, Chrome Mox, Mayor Tong | keep | keep | keep | keep (0.25) |
| Magus, Elvish Mystic, Green Sun's Zenith, Concordant Crossroads, … | keep | mull | mull | keep (0.20) — untapper + tutor + haste |

**Everyone agrees to mulligan:** hands of tutors and finishers with no mana (GSZ, Kamahl, Toph, Ancient
Tomb, Flash, Natural Order, Verdant Touch), and hands of dead cards (Animate Land, Nature's Chosen, Veil,
Foothills, Marvin, Scryb Ranger, Kamahl).

---

## 8. Sample traces (`sim/results/traces_seed21.txt`)

**Turn-3 win, verified by hand.** Opener (six cards after one mulligan): Magus, Gaea's Cradle, Forest,
Marsh Flats, Avacyn's Pilgrim, Natural Order. T1 Flats → Savannah, Pilgrim. T2 Forest, Voyaging Satyr,
Magus. T3: play Cradle (3 creatures = GGG), 7 mana total; Natural Order sacrificing Pilgrim → Ashaya;
Magus X=2 untaps itself and Cradle, Cradle makes 3, net +1 per pass; finish via Green Sun's Zenith
(drawn) → Kamahl; five bodies held since turn start.

**Turn-4 Emiel win without Ashaya.** T1 Savannah, Utopia Sprawl, Elvish Mystic. T2 Temple Garden,
Llanowar, Delighted Halfling. T3 Brushland, Sisay, Flash Thompson. T4: Sisay fetches Cradle, Eldritch
Evolution → Emiel, Chord of Calling (convoke) → Badgermole Cub whose earthbend animates Cradle with
haste; Emiel blinks Flash, Flash untaps Cradle, Cradle makes 7+.

**Near miss.** Opener Nature's Chosen, Wall of Roots, Sylvan Tutor, Eiganjo, Mana Vault, Pilgrim,
Boromir. Sisay only on T4, Emiel T5, Selvala T6; never finds an untapper by T6. Classified
"no untapper".

---

## 9. Recommendations

### Mulligan

**At seven, keep when all three hold:**
1. A land that makes green, plus a second land or a *real* fast-mana piece (Lotus Petal, Elvish Spirit
   Guide, Mox Diamond with a spare land, Chrome Mox with an imprint, Sol Ring/Vault with a land).
2. Sisay castable on T3 with a white source that is not only Birds or Pilgrim.
3. A nonlegendary untapper (Hope Tender, Magus, Quirion, Scryb, Flash) **or** a creature tutor that finds
   one (GSZ, Summoner's Pact, Chord, Eldritch Evolution, Eladamri's Call, Survival, Formidable Speaker,
   Ranger-Captain for Magus/Quirion).

Cradle in the opener is not a reason to keep on its own; two of the three flashy keeps above had it.

**Take the free mulligan** on one-landers with dorks, on hands whose only white is a dork, and on hands
with three or more cards from the dead pile (Nature's Chosen, Animate Land, Verdant Touch, Vitalize,
Emerald Charm, Toph, Marvin).

**At six:** two mana sources with green and Sisay by T3. **At five:** any two mana sources and a green
source. Bottom in this order: dead pile, surplus lands beyond three, protection, Kamahl (Sisay finds
him), redundant finishers.

### Deck, from the measured bottlenecks

- Untapper access is the largest failure bucket in every policy (17–21% of games). The strongest
  measured fix is **Argothian Elder** (+2.5 pts T5 wins): a two-card infinite with Ashaya, and another
  body for the creature tutors to find. Any extra cheap creature tutor does the same job.
- **Devoted Druid + Vizier of Remedies** is the only infinite tested that needs neither Ashaya nor
  Emiel (+1.7 pts T5, +1.9 pts T4).
- **Kamahl is the single point of failure for the finish.** Ezuri, Renegade Leader is the only green
  legendary backup tested; it adds nothing while Kamahl is available and restores a third of the wins
  when he is gone. Whether it is worth a slot depends on how often Kamahl gets answered at your tables.
- Walking Ballista: not recommended (not Sisay-fetchable, only matters without Kamahl).
- The white bottleneck (9%) is better fixed by the mulligan rule than by the mana base.

---

## 10. Reproduce

```
python3 sim/tests.py
python3 sim/run.py --games 20000
python3 sim/run.py --ablate --games 3000 --seed 5
python3 sim/run.py --remove "Fal'Cie Paradise" --add "Argothian Elder" --compare --games 3000 --seed 5
python3 sim/experiment.py --games 5000 --policies A B C --jobs 3
python3 sim/experiment.py --games 1500 --policies D --rollouts 5 --calib 100
python3 sim/experiment.py --games 3000 --policies A --islands 1      # also --islands 2, --on-draw
python3 sim/experiment.py --hands 14 --policies A B C D --rollouts 12 --calib 60 --seed 3
python3 sim/run.py --log 40 --seed 21 --turns 6
```

Runtimes on four cores: A–C 5,000 games ≈ 2 min; D 1,500 games ≈ 35 min; ablation ≈ 10 min.
