# Adding Content

Run `python -m unittest discover -s tests -v` and load the game once after every
registry edit. Startup validation catches most broken references immediately.

## Resource

Add to `RESOURCE_DEFS` in `content_core.py`:

```python
"candle_wax": {
    "name": "Candle Wax",
    "description": "Fuel for long rituals.",
    "flavor": "It remembers every flame.",
    "base_capacity": 50.0,
    "symbol": "▰",
    "theme": "wax",
    "accent": "#d2ae69",
    "accent_rgb": "210, 174, 105",
    "visible_when": [{"type": "research", "key": "ritual_alchemy"}],
},
```

The state factory, save normalizer, statistics, resource sidebar, rates, costs,
tooltips, icon tint, and meter fill discover it automatically.

## Placeholder and final art

All content art resolves through `game/visuals.py`. Put a finished asset under
`assets/art/`, then add one override without changing panel code:

```python
ART_OVERRIDES["resource"]["candle_wax"] = "assets/art/resources/candle-wax.svg"
```

The six files in `assets/placeholders/` are intentionally generic SVGs. Keep
the same slot dimensions or adjust the shared `.art-*` classes in `style.css`.
Icons beside visible text are decorative; the text remains the accessible name.

## Upgrade

Add to `UPGRADE_DEFS` in `content_progression.py`:

```python
"wax_seal": {
    "name": "Wax Seal",
    "description": "Skeleton bindings last 20% longer.",
    "flavor": "Signed by a hand no longer attached.",
    "cost": {"candle_wax": 10, "mana": 100},
    "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 4}],
    "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 1.2}],
},
```

The store renders it automatically. Reuse a supported effect when possible.

## Timed research

Use the `project()` constructor:

```python
"patient_flames": project(
    "Patient Flames",
    "Spirit",
    "Unlocks slow-burning ritual candles.",
    "A steady light invites steady visitors.",
    knowledge=20,
    duration=120,
    prerequisites=["ritual_alchemy"],
    effects=[{"type": "resource_capacity_add", "resource": "candle_wax", "amount": 50}],
    start_cost={"ritual_ink": 2},
),
```

`knowledge_cost` is the total continuous drain. Research speed changes wall
time but never changes total Knowledge. Queued projects spend their optional
start cost when planned; cancelling does not refund it or spent Knowledge.

## Skeleton job

Direct-resource jobs are data-only:

```python
"render_wax": {
    "name": "Render Wax",
    "short_name": "Rendering",
    "description": "Produces Candle Wax continuously.",
    "flavor": "The cauldron is best left undescribed.",
    "kind": "resource",
    "resource": "candle_wax",
    "base_rate": 0.04,
    "visible_when": [{"type": "research", "key": "patient_flames"}],
},
```

The roster, tooltips, production estimate, offline simulation, and assignment
buttons discover it. A job that advances a special activity needs one new
`kind` branch in validation, `logic.production_rates`, and `advance_game`.

## Workshop recipe

Add to `RECIPE_DEFS`:

```python
"black_candle": {
    "name": "Pour Black Candle",
    "description": "Turns wax and Ink into a ritual catalyst.",
    "flavor": "It casts its shadow before being lit.",
    "cost": {"candle_wax": 5, "ritual_ink": 1},
    "produces": {"ectoplasm": 2},
    "visible_when": [{"type": "research", "key": "patient_flames"}],
},
```

Recipes use one generic handler and card renderer. For recipes that take time,
create a timed-process system instead of putting timers in the click handler.

## New effect type

1. Choose whether it adds or multiplies and document its stacking rule.
2. Add the identifier to `SUPPORTED_EFFECT_TYPES` in `validation.py`.
3. Resolve it at the one derived-value function that owns the behavior.
4. Add unit tests for no effect, one effect, and stacked effects.
5. Add exact before/after wording to the tooltip if the effect is not obvious.

Avoid an `if` branch in every panel. The UI should consume the resolved value.

## New minigame

Use a small finite-state machine:

```text
idle → setup/reveal → player input → result → idle
```

Store serializable progress under `game["activities"]`; put its mechanics in
`activities.py`; expose commands through `logic.py`; build/update its custom
panel in `ui.py`. It must have clear input/output text, a bounded advantage, an
idle/manual fallback, keyboard controls, save normalization, and regression
tests. Promote shared lifecycle code only after a second minigame truly matches
it.

## New tab

Add `key`, `label`, `symbol`, and `scene` metadata to `TAB_DEFS`, then register its build/update pair in
`PANEL_BUILDERS` and `PANEL_UPDATERS`. Navigation, ARIA state, badges, and the
update traversal remain generic.

## New saved field

1. Increment `SAVE_SCHEMA_VERSION`.
2. Add the default to `state.new_game_state()`.
3. Add an ordered migration in `migrations.py` and register it.
4. Normalize hostile/missing values in `save.normalize_state()`.
5. Add a migration test using the previous schema.
6. Never rename or delete an old migration after releasing it.
7. Map every new Python file in `pyscript.json`.
