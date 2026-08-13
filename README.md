# The First Rite

A dark, minimalist necromancer incremental game and a reusable PyScript idle-
game framework. It runs entirely in the browser and stores a versioned JSON
save in `localStorage`.

## Current game

- Hold to channel Mana and excavate graves manually.
- Play **Focused Excavation**, a timing minigame with bounded bonus rewards.
- Craft a Soul Cage and play a short sequence-memory **Séance**.
- Assemble a visible seven-part skeleton with pointer, touch, or click controls.
- Summon multiple named Skeletons, rename them, and assign independent jobs.
- Manage eight resources, sixteen upgrades, twenty-five timed research projects,
  workshop recipes, storage limits, and offline progress.
- Filter structured events by Progress, Resources, Research, Skeletons,
  Activities, or System.
- Use definition-driven tooltips, reduced-motion settings, responsive layouts,
  and keyboard alternatives for drag interactions.

Research uses one active lectern and a planning queue. An active project drains
Knowledge continuously, pauses at zero, resumes without losing progress, and
can complete offline if enough Knowledge was saved.

## Run locally

The project must be served over HTTP so PyScript can load its modules:

```powershell
py -m http.server 8000
```

Open `http://localhost:8000/`.

Run the browser-independent regression suite with:

```powershell
py -m unittest discover -s tests -v
```

## Framework map

| Area | File | Responsibility |
|---|---|---|
| Content façade | `game/content.py` | Stable imports for every registry |
| Core content | `game/content_core.py` | Resources, jobs, recipes, tabs, activities, assembly |
| Progression | `game/content_progression.py` | Upgrades and timed research projects |
| Economy | `game/economy.py` | Capacity, grants, and atomic spending |
| Effects | `game/effects.py` | Additive and multiplicative modifier resolution |
| Requirements | `game/requirements.py` | Shared visibility/unlock rule language |
| Research | `game/research.py` | Queue, continuous drain, pause, resume, completion |
| Workers | `game/workers.py` | Names, jobs, availability, and rate resolution |
| Activities | `game/activities.py` | Minigame state machines and generic recipes |
| Coordination | `game/logic.py` | Public commands and stable simulation order |
| State | `game/state.py` | JSON-safe save and transient input state |
| Persistence | `game/save.py`, `game/migrations.py` | Validation, v1→v2→v3→v4 migration, browser storage |
| Visual registry | `game/visuals.py`, `assets/placeholders/` | Replaceable art paths and category fallbacks |
| Registry checks | `game/validation.py` | Broken references, cycles, and invalid content |
| UI | `game/ui.py` | Panel composition and presentation updates |
| UI components | `game/ui_components.py`, `game/ui_tooltips.py` | Shared meters, formatting, headings, tooltips |
| Bootstrap | `main.py` | Static page events, startup, clock, autosave |

The simulation is the authority. UI actions call `game.logic`; panels never
implement prices, rewards, or production formulas themselves.

## Continue the project

- [Adding content](docs/ADDING_CONTENT.md) contains copyable examples for a
  resource, upgrade, timed study, worker job, recipe, minigame, effect, and save
  migration.
- [Architecture](docs/ARCHITECTURE.md) explains data flow, invariants, system
  order, and why the boundaries exist.
- [Save format](docs/SAVE_FORMAT.md) documents schema v4 and safe migrations.
- [Balance guide](docs/BALANCE.md) lists source/sink roles and pacing targets.
- [26-game research](docs/INCREMENTAL_GAME_RESEARCH.md) records the comparative
  design study behind this framework.
- [Learning path](docs/LEARNING_PATH.md) links the browser, accessibility,
  architecture, testing, and idle-math material worth learning next.

When adding a Python module, also map it in `pyscript.json`; otherwise it will
compile locally but will not exist inside PyScript's browser filesystem.
