# Captain Sisay goldfish simulator

Monte Carlo "goldfish" games (no opponents) to see how often and how fast each combo line comes together.

```
python3 sim/run.py --games 20000        # stats
python3 sim/run.py --log 5 --seed 3     # annotated sample games
python3 sim/run.py --deck other.txt     # try a different 99 + commander
python3 sim/run.py --remove "Vitalize" --add "Argothian Elder" --compare   # test a swap
python3 sim/run.py --ablate --games 3000                                   # value of every card
```

Swaps replace the card in place and every game uses a fixed seed, so baseline and variant play
identical shuffles: the difference is the card, not luck. `--add` accepts any card in `cards.py`
(the list plus the `CANDIDATES` block: Argothian Elder, Devoted Druid, Vizier of Remedies,
Umbral Mantle, Elvish Reclaimer, Gilded Goose, Walking Ballista, Ezuri, Renegade Leader).

## Mulligan experiment and rules tests

```
python3 sim/tests.py                                   # golden rulings the planner must honour
python3 sim/experiment.py --games 5000 --policies A B C   # London-mulligan policies, same seeds
python3 sim/experiment.py --games 1500 --policies D       # rollout policy (slow: plays rollouts per decision)
python3 sim/experiment.py --hands 12                      # the same openers shown to every policy
python3 sim/experiment.py --islands 1 --on-draw           # Carpet of Flowers / Gemstone Caverns scenarios
```

Milestones recorded per game: Sisay cast, first Sisay activation, Cradle making 3+, two activations in a turn,
infinite mana, lethal (needs Kamahl or Finale **and** 3 bodies held since the turn began), protection-ready
lethal (Abolisher/Voice/Walters/Boromir/Ranger-Captain in play, or Silence/Veil castable from spare mana).
Games without a T4 lethal get one primary failure reason. Policies live in `mulligan.py`.

## First Sisay activation: Cradle vs Selvala

```
python3 sim/first_tutor.py --games 5000                  # freeze games at the first activation, run all arms
python3 sim/first_tutor.py --games 800 --policy D        # states reached under the rollout mulligan
python3 sim/first_tutor.py --games 2000 --divergences 12 # traces where cradle/selvala disagree
```

Arms continue identical copies of the frozen state with the same seed: `current` (pilot's choice), `cradle`,
`selvala`, `contextual` (hand-written rule), `lookahead` (rollouts per candidate legend). See FIRST_TUTOR_RESULTS.md.

## What it does each turn
1. Draw, then ask the planner whether any combo line can be finished **this turn**: every missing piece needs a route
   (cast from hand, Sisay, GSZ, Chord, Natural Order, Eldritch, Pact, Survival, Knight/Crop Rotation for lands, ...).
   The planner also checks total mana and colors, the land drop, haste for pieces that must tap (Concordant, Elixir,
   Shang-Chi, Greaves), and the line's own condition, for example Cradle with at least 2 creatures or devotion of at least 4.
2. Otherwise develop: land, fast mana, dorks, Sisay, pieces for the closest line, tutors toward missing pieces.
3. Check again, then at end of turn: Worldly/Sylvan stack the top. An active Sisay tutors in the first main
   phase (before the land drop), so a fetched Cradle is this turn's land and a fetched creature can be cast.

Infinite-mana lines only count as a win when an outlet is reachable (Kamahl, Finale, an unused creature tutor, or
Sisay, who Ashaya + Hope Tender/Magus can untap to fetch Kamahl).

## Simplifications
- Loop detection is line-based: `engine.LINES` lists each infinite with its pieces, which piece must tap, its
  startup cost and its condition (creature count, devotion, power, haste, white permanent, fresh Cradle).
  The planner checks routes, mana, colors, the land drop and haste for that list; it does not derive loops
  from first principles. `tests.py` pins the rulings; a line not in the list is not credited.
- No interaction, no opposing stax, no free-spell tax: this is an upper bound on speed.
- Mana is abstract units (G / W / either / colorless). Fetches find a G/W dual.
- The pilot is a heuristic, not optimal: it can misspend mana while developing, and it plans only one turn ahead.
- Mulligan: one free mulligan, then London; a 7 is kept with 1–4 lands and 3+ mana sources.
- Toph is modelled only as an animator with haste for the Emiel + Flash + Cradle loop; Nature's Chosen as a second
  tap of the enchanted mana creature each turn. Jennifer Walters is protection only. Command tax is not tracked.
