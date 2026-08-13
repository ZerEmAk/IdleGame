# Balance Notes

## Resource roles

| Resource | Pace | Main sources | Main sinks |
|---|---|---|---|
| Mana | fast | held channeling, Skeleton channelers | upgrades, Soul Cage, Séance, recipes, summons |
| Bones | medium | graves, expired Skeletons | assembly, equipment upgrades |
| Bound Souls | capped | trapped graves, Séance | summoning and late upgrades |
| Knowledge | slow flow | graves, expired Skeletons, Scribes | continuous research |
| Grave Dust | medium specialist | graves, Focused Excavation, Sifters | Ink and relic study |
| Ectoplasm | slow specialist | Séance, Haunters | Ink and spirit upgrades |
| Ritual Ink | processed | Workshop | advanced research start costs and equipment |
| Relics | rare | perfect excavation | unique upgrades and late projects |

Every new resource should eventually have at least two sources and two sinks.
Reveal it only when its first source or use becomes understandable.

## Pacing intent

- First grave: roughly 1 minute of active play.
- Soul Cage: 3–5 minutes.
- First Skeleton: 6–10 minutes.
- First timed study: 15–25 minutes of mixed play.
- Two simultaneous Skeletons: around 1 hour.
- Ritual Ink and specialist jobs: 2–4 hours.
- Late command projects: a 10–15 hour first content layer.

The current constants are intentionally readable prototypes, not a final live-
ops economy. Measure real sessions before extending the curve.

## Tuning method

1. Write a milestone target and the expected active/idle mix.
2. Calculate the resources produced by the previous loop in that time.
3. Price the next unlock at 60–80% of that production so choices remain.
4. Give upgrades noticeable 25–100% effects early; tiny bonuses teach players
   that buying is pointless.
5. Simulate large ticks and many small ticks, then play the UI without debug
   resources.
6. Track sources, sinks, caps, and time-to-afford in a spreadsheet before adding
   another currency.

For exponential producer costs and reset math, follow the articles linked in
`LEARNING_PATH.md`. Prefer finite phase changes and new decisions over endlessly
adding zeroes.
