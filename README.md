# The First Rite

A browser idle game about learning necromancy. It runs entirely in the browser
with Python through PyScript and saves progress to `localStorage`.

## Game loop

1. Hold **Channel Mana** to draw power.
2. Dig graves repeatedly for Bones and Knowledge.
3. Craft a reusable Soul Cage and capture Bound Souls.
4. Prepare a frame and drag seven parts into place: Head, Torso, two Arms,
   two Legs, and a Soulgem.
5. Summon temporary Skeletons and assign each one to channel Mana or dig graves.
6. Purchase resource upgrades and complete prerequisite-based research.
7. Research a larger binding limit to run several Skeletons at once.

Skeletons eventually expire, returning some Bones and generating additional
Knowledge. Upgrades and research significantly improve manual actions,
production, storage, assembly costs, binding duration, and army size.

## Run locally

The game must be served over HTTP so PyScript can load its Python modules:

```powershell
py -m http.server 8000
```

Then open `http://localhost:8000/`.

## Modular content

Most new content can be added without editing the UI:

- `game/content.py` contains resources, tabs, jobs, assembly parts, upgrades,
  research, costs, prerequisites, and effects.
- `game/definitions.py` contains engine settings and base balance values.
- `game/logic.py` contains the generic effect engine and all game rules.
- `game/state.py` defines saveable progress and temporary input state.
- `game/ui.py` generically renders upgrade/research definitions and manages the
  tabbed interface.
- `game/save.py` migrates v1 saves, validates loaded data, and stores progress.
- `main.py` handles static controls, startup, elapsed time, and autosaving.
- `index.html` and `style.css` contain the page shell and responsive theme.

Supported effect types include channel multipliers, click power, grave yield,
resource capacity, assembly cost, Skeleton duration, work rate, returned Bones,
and binding-limit increases.

## Save behavior

Progress autosaves every 10 seconds and at major progression purchases.
Skeletons continue working during offline time only until their individual
bindings expire. Holding the channel button never generates offline Mana.
