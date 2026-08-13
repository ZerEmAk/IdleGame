# Architecture

## Design goals

The framework separates *what exists* from *how it behaves* and *how it is
shown*. Content definitions are ordinary dictionaries with stable string keys.
Systems interpret those records. The UI dispatches commands and renders state.

```text
content registries
      ↓ validated at startup
requirements → public commands → economy/effects/research/workers/activities
                         ↓
                   JSON-safe state
                   ↙           ↘
             save/migrate      UI render
```

This is a functional-core/browser-shell direction rather than a strict engine.
The pure Python core remains testable without a DOM; `save.py`, `ui*.py`, and
`main.py` are the browser adapters.

## Stable boundaries

- `content_core.py` contains nouns: resources, activities, parts, recipes,
  worker jobs, tabs, and log categories.
- `content_progression.py` contains progression catalogues. Keys are save IDs;
  rename the displayed `name`, not the key.
- `requirements.py` is the only unlock language. Unknown rules fail closed.
- `effects.py` combines completed content. The formula is `(base + additions) ×
  multipliers`; the current helpers expose each stage explicitly.
- `economy.py` owns all balance mutations. Multi-resource prices are atomic.
- `research.py` owns its queue and deterministic partial payment.
- `activities.py` owns short state machines. They grant through the economy.
- `workers.py` owns identity and generic direct-resource job metadata.
- `logic.py` is the public façade and cross-system coordinator.
- `state.py` must remain JSON-safe. DOM nodes and callbacks belong in module
  globals or `state.runtime`, never in `state.game`.

## Simulation order

`logic.advance_game(seconds)` always advances:

1. manual channeling (online only),
2. current Skeleton work and expiration,
3. timed research and Knowledge drain,
4. interactive activity clocks (online only),
5. time statistics and unlock checks.

Long intervals are divided into at most one-second integration steps, using
`MAX_SIMULATION_STEP_SECONDS`. This keeps simultaneous producers, caps,
research drains, queue completions, and worker expiry close to live behavior.
Document and test any future ordering or step-size change.

## Commands, events, and presentation

UI handlers call commands such as `logic.buy_upgrade`, `logic.start_seance`, or
`logic.rename_skeleton`. Commands return `True` only when they changed game
state. Domain events are structured dictionaries created by `state.add_log`;
their category is presentation-independent and can later feed achievements,
tutorials, sound, or analytics.

Tooltips use mechanical `description` plus fictional `flavor`. Essential cost,
status, and requirement information remains visible outside tooltips.

The browser shell builds every panel once, but frequent refreshes update only
global chrome and the selected panel. This prevents hidden research and store
DOM from consuming the frame budget. `visuals.py` resolves replaceable assets;
`ui_components.py` owns shared elements; panel code supplies semantic text.
PyScript-created elements use the wrapper API (`element.style[...]` and
`element.classes`), while raw nodes returned by `cloneNode`, `closest`, or
`elementsFromPoint` use native DOM APIs (`style.setProperty` and `classList`).

## Extension invariants

- Registry keys are unique, lowercase, and stable across releases.
- Every referenced resource, job, effect, and prerequisite must exist.
- Costs and durations are non-negative; timed-project durations are positive.
- Research prerequisites must be acyclic.
- Saved values are JSON-compatible and normalized before simulation.
- New content fields receive defaults so older saves can be merged safely.
- Active minigames have a click/keyboard alternative to dragging or timing.
- Decorative animation uses transforms/opacity and respects reduced motion.

`validation.validate_content()` checks the reference-level rules at startup.
Add a validation branch whenever you add a new definition field that can point
at another registry.

## When to introduce another abstraction

Do not create a generic system for one unusual feature. Add a named handler in
the relevant module, then generalize after a second feature has the same state
and lifecycle. Recipes are generic because both use atomic costs and rewards;
Focused Excavation and Séance stay custom because their inputs differ.

The next useful abstractions, once content needs them, are:

- a reusable timed-process engine for crafting, expeditions, and construction;
- a command registry for moddable actions;
- view models so `ui.py` can split into independent panel modules;
- semantic animation events rather than presentation detecting state deltas;
- a memorial ledger and worker traits/equipment;
- a later prestige layer that changes decisions and automates mastered chores.
