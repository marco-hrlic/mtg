# Captain Sisay goldfish simulator

Monte Carlo "goldfish" games (no opponents) to see how often and how fast each combo line comes together.

```
python3 sim/run.py --games 20000        # stats
python3 sim/run.py --log 5 --seed 3     # annotated sample games
python3 sim/run.py --deck other.txt     # try a different 99 + commander
```

## What it does each turn
1. Draw, then ask the planner whether any combo line can be finished **this turn**: every missing piece needs a route
   (cast from hand, Sisay, GSZ, Chord, Natural Order, Eldritch, Pact, Survival, Knight/Crop Rotation for lands, ...).
   The planner also checks total mana and colors, the land drop, haste for pieces that must tap (Concordant, Elixir,
   Shang-Chi, Greaves), and the line's own condition, for example Cradle with at least 2 creatures or devotion of at least 4.
2. Otherwise develop: land, fast mana, dorks, Sisay, pieces for the closest line, tutors toward missing pieces.
3. Check again, then at end of turn: Sisay fetches a missing legend, Worldly/Sylvan stack the top.

Infinite-mana lines only count as a win when an outlet is reachable (Kamahl, Finale, an unused creature tutor, or
Sisay, who Ashaya + Hope Tender/Magus can untap to fetch Kamahl).

## Simplifications
- No interaction, no opposing stax, no free-spell tax: this is an upper bound on speed.
- Mana is abstract units (G / W / either / colorless). Fetches find a G/W dual.
- The pilot is a heuristic, not optimal: it can misspend mana while developing, and it plans only one turn ahead.
- Mulligan: one free mulligan, then London; a 7 is kept with 1–4 lands and 3+ mana sources.
- Cards whose exact text was unverified (Toph, Jennifer Walters) are modelled as vanilla creatures.
