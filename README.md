# Idle Framework

A deliberately simple, data-driven PyScript foundation for an incremental / idle game.

The page uses a familiar three-column structure:

- **Left:** resources with amount, capacity, rate, and a background fill bar.
- **Middle:** tabs for overview, buildings, upgrades, and statistics.
- **Right:** event log.
- **Top-right:** game version and settings.

The repeated UI is generated from Python definitions, so adding normal resources, buildings, and upgrades requires much less hand-written HTML.

---

## Project structure

```text
IdleFramework/
├── index.html
├── style.css
├── pyscript.json
├── main.py
├── .gitignore
├── README.md
└── game/
    ├── __init__.py
    ├── definitions.py
    ├── state.py
    ├── logic.py
    ├── save.py
    └── ui.py
```

### What belongs where?

| File | Responsibility |
|---|---|
| `index.html` | Large page containers and static settings dialog |
| `style.css` | Layout and appearance |
| `pyscript.json` | Makes local Python modules available to PyScript |
| `main.py` | Startup, static events, main timed loop |
| `game/definitions.py` | Resources, buildings, upgrades, balance values, version |
| `game/state.py` | Current saveable player progress |
| `game/logic.py` | Costs, production, buying, upgrade effects |
| `game/save.py` | Browser save/load and offline-time calculation |
| `game/ui.py` | Generates repeated HTML and updates changing values |

A good mental model is:

```text
definitions -> state -> logic -> UI
                  |
                  -> save/load
```

---

## Run locally

Do not open `index.html` directly with a `file:///...` URL. Serve the folder with a local web server.

From the project directory:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

Keep using the same port while testing saves. Browser storage belongs to the website origin, so changing between different hosts/ports can appear to give you a different save.

---

## The normal development workflow

A useful loop is:

1. Decide on **one small change**.
2. Edit the appropriate file.
3. Refresh the local page.
4. Test the normal case and at least one edge case.
5. Check the browser developer console for errors.
6. Run `git diff` and review what actually changed.
7. Commit the working change.
8. Push it to GitHub.
9. Repeat.

Avoid adding five new systems at once. Small working iterations are much easier to debug and balance.

---

# Common changes

## Change the displayed version

Edit this in `game/definitions.py`:

```python
GAME_VERSION = "0.1.0"
```

A simple version pattern while prototyping:

```text
0.1.0  first usable framework
0.1.1  small fixes / balance changes
0.2.0  meaningful new system
0.3.0  another meaningful new system
1.0.0  only when you consider the game genuinely released
```

The displayed version is generated automatically by `ui.py`.

---

## Add a resource

Usually, only edit `RESOURCE_DEFS` in `game/definitions.py`:

```python
"water": {
    "name": "Water",
    "description": "Used by later systems.",
    "base_capacity": 200.0,
},
```

The framework automatically creates:

- save state for it;
- the resource row;
- amount/capacity/rate display;
- the fill bar;
- total-generated statistics.

Then make a building or another mechanic produce/consume that resource.

---

## Add a building

Add another entry to `BUILDING_DEFS`:

```python
"pump": {
    "name": "Pump",
    "description": "Produces Water.",
    "cost_resource": "credits",
    "base_cost": 50.0,
    "cost_growth": 1.15,
    "produces": {
        "water": 2.0,
    },
},
```

The framework automatically gives it:

- an owned count;
- a generated shop card;
- scaling cost;
- Buy 1 / Buy 10 / Buy Max support;
- automatic production;
- save/load support.

This is why definitions and player state are separate.

---

## Add an upgrade

The framework currently understands two generic upgrade effect types:

```text
building_production_multiplier
resource_capacity_multiplier
```

Example:

```python
"better_pumps": {
    "name": "Better Pumps",
    "description": "Pumps produce three times as much.",
    "cost_resource": "knowledge",
    "cost": 25.0,
    "effects": [
        {
            "type": "building_production_multiplier",
            "building": "pump",
            "multiplier": 3.0,
        }
    ],
},
```

If you invent a completely new effect, for example:

```text
manual_action_multiplier
```

then:

1. describe it in `UPGRADE_DEFS`;
2. add the rule for what it means in `logic.py`.

This keeps the content data-driven without turning everything into magic.

---

## Change how the game looks

Edit `style.css` first.

Try to keep game rules out of CSS and visual styling out of `logic.py`.

Good early improvements:

- spacing and typography;
- clearer selected tabs;
- affordable/unaffordable states;
- better mobile layout;
- different visual categories for resources;
- tooltips;
- subtle transitions after the base UI feels good.

Do not start with animations and elaborate artwork. Make the information easy to understand first.

---

## Change the page structure

For large fixed containers, edit `index.html`.

For repeated/generated content, edit `game/ui.py`.

Examples:

```text
Move the event log -> index.html / CSS
Change every building card -> ui.py
Add one new building -> definitions.py
Change a building's production formula -> logic.py
```

---

# Save system

The current framework saves to browser `localStorage`.

The saved state contains player progress, not the entire game definition. On load, the saved values are merged into a fresh state made from the current definitions.

That means adding a new resource/building/upgrade during development normally remains compatible with older saves.

## When to change `SAVE_SCHEMA_VERSION`

Do **not** bump it for ordinary cost changes, new buildings, new upgrades, or text edits.

Consider changing it when you fundamentally restructure save data, for example:

```text
old: game["buildings"]["generator"] = 5
new: game["buildings"]["generator"] = {"amount": 5, "level": 2}
```

At that point, either:

- write a migration from the old structure; or
- intentionally reset incompatible prototype saves.

Do not silently destroy corrupted saves while debugging. The starter loader reports an error and leaves the original browser data in place.

---

# Offline progress

When a save loads, the framework compares the saved timestamp to the current time and processes production for the time away.

The starter caps offline progress at 8 hours:

```python
OFFLINE_PROGRESS_MAX_SECONDS = 8 * 60 * 60
```

Change that in `game/definitions.py` when you decide how generous the real game should be.

---

# Important architecture rules

## 1. Definitions are not player state

Good:

```python
BUILDING_DEFS["generator"]["base_cost"] = 10
state.game["buildings"]["generator"] = 4
```

The first describes the game. The second describes the player.

## 2. Game logic should not know about HTML

`logic.py` should calculate things such as:

```text
production
costs
capacity
purchase validity
upgrade effects
```

It should not change DOM elements.

## 3. Build repeated UI once, update values later

At startup:

```text
read definitions -> create resource/building/upgrade elements
```

During the game loop:

```text
calculate -> update existing text / bars
```

Do not delete and rebuild the entire interface every tick.

## 4. Use elapsed real time

Production is based on:

```text
rate per second * actual elapsed seconds
```

not on an assumption that a timer always runs at exactly the requested interval.

This makes the game more reliable when browsers throttle or lag.

---

# What to build next

A sensible progression from this framework is:

```text
0.1  resources + buildings + upgrades + save/load
0.2  unlock conditions + hidden tabs/resources
0.3  production costs / conversion chains
0.4  research tree
0.5  achievements + notifications
0.6  export/import saves
0.7  prestige/reset layer
0.8  deeper automation and long-term systems
```

Do not treat this sequence as mandatory. The game's actual identity should decide what comes next.

---

# Git workflow

Before changing code:

```bash
git status
git pull
```

After a small working change:

```bash
git status
git diff
git add game/definitions.py
git commit -m "Add water resource"
git push
```

Using `git add <specific files>` is a good habit because it makes you think about what you are committing. `git add .` is fine when you have checked `git status` first and genuinely want every change.

Useful commands:

```bash
git status
git diff
git log --oneline --graph --decorate
git remote -v
git restore <file>
```

`git restore <file>` discards uncommitted changes to that file, so use it carefully.

---

## Use feature branches when changes become larger

For a small solo prototype, committing directly to `main` is acceptable.

When a feature starts taking multiple commits:

```bash
git switch -c feature/research-tree
```

Work and commit normally, then publish the branch:

```bash
git push -u origin feature/research-tree
```

Merge it only when the feature works.

This keeps `main` closer to a playable version.

---

## Mark playable versions with tags

When you reach a version worth preserving:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Later you can easily find exactly what the project looked like at that milestone.

---

## Avoid force-pushing as a normal workflow

Commands such as:

```bash
git push --force
```

rewrite shared history. They are useful for intentional history repair, but they should not be the normal way you publish updates.

Normal development should usually be:

```bash
git add ...
git commit -m "..."
git push
```

---

# GitHub Pages

For a public static PyScript project, GitHub Pages can publish the repository directly.

Typical repository settings:

```text
Settings -> Pages
Source: Deploy from a branch
Branch: main
Folder: /(root)
```

After a successful `git push`, wait for the Pages deployment to finish and refresh the published site.

Remember that the GitHub Pages site and `localhost` are different browser origins, so each has its own local save.

---

# Debugging habits

When something breaks:

1. Read the **first meaningful error**, not only the final line.
2. Check the browser Developer Tools console.
3. Check the Network tab for missing `.py`, `.json`, or CSS files.
4. Run `git diff` to see what changed since the last working state.
5. Temporarily add small `print()` statements around suspicious values.
6. Reduce the problem to the smallest reproducible change.

If PyScript says:

```text
No elements found for selector: #something
```

then Python tried to attach an event to an element that did not exist at that moment. This framework avoids that for generated shop buttons by attaching handlers when those elements are created.

If Python says an imported `game.*` module cannot be found, check `pyscript.json` and the browser Network tab.

---

# General development advice

- Commit working milestones often.
- Keep functions small enough that their purpose is obvious.
- Prefer clear names over clever short names.
- Avoid premature abstractions. Add an abstraction after you have repeated a pattern enough to understand it.
- Keep balance numbers in definitions instead of scattering them throughout functions.
- Do not commit passwords, access tokens, API keys, or private secrets.
- Keep the game playable while adding systems; a giant unfinished rewrite is harder to evaluate.
- Test with a fresh save occasionally. Old developer saves can hide progression problems.
- Test at storage limits, zero resources, exact purchase cost, and Buy Max.
- Back up major milestones with Git tags.
- Write down design decisions when they become important; future-you will forget why a strange rule exists.

---

# PyScript note

This starter pins PyScript to `2026.7.2` in `index.html`.

Do not change the PyScript release number just because a newer one exists. Upgrade deliberately, read the release notes, then test saving, dynamic UI creation, events, and GitHub Pages before committing the upgrade.

Official documentation:

- https://docs.pyscript.net/
- https://docs.pyscript.net/latest/user-guide/configuration/
- https://docs.pyscript.net/2026.3.1/user-guide/dom/
- https://docs.pyscript.net/2026.3.1/user-guide/events/

---

## First recommended edits

1. Rename the project in `index.html`.
2. Replace the example entries in `RESOURCE_DEFS`.
3. Replace the example buildings.
4. Replace the example upgrades.
5. Change `GAME_VERSION` to match your first prototype version.
6. Keep the CSS simple until the actual game loop is enjoyable.

Once the real game has several unique systems, split those systems into additional modules instead of allowing `logic.py` or `ui.py` to become enormous.
