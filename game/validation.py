"""Startup validation for declarative content registries.

Failing early with a precise content key is much easier to debug than a card
that unlocks incorrectly several hours into a save.
"""

from game.content import (
    ACTIVITY_DEFS,
    PART_DEFS,
    RECIPE_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
    SKELETON_JOB_DEFS,
    SLOT_DEFS,
    TAB_DEFS,
    UPGRADE_DEFS,
)


SUPPORTED_EFFECT_TYPES = {
    "assembly_cost_multiplier",
    "bones_per_grave_multiplier",
    "channel_multiplier",
    "dig_click_add",
    "excavation_reward_multiplier",
    "excavation_target_multiplier",
    "knowledge_per_grave_multiplier",
    "recipe_yield_multiplier",
    "research_queue_add",
    "research_speed_multiplier",
    "resource_capacity_add",
    "resource_capacity_multiplier",
    "seance_reveal_multiplier",
    "seance_reward_multiplier",
    "skeleton_duration_multiplier",
    "skeleton_limit_add",
    "skeleton_return_add",
    "skeleton_work_multiplier",
}

SUPPORTED_REQUIREMENTS = {"flag", "research", "resource", "stat", "total_resource"}


def _validate_cost(cost, owner):
    if not isinstance(cost, dict):
        raise ValueError(f"{owner}: cost/reward must be a dictionary")
    for resource, amount in cost.items():
        if resource not in RESOURCE_DEFS:
            raise ValueError(f"{owner}: unknown resource {resource!r}")
        if float(amount) < 0:
            raise ValueError(f"{owner}: negative amount for {resource!r}")


def _validate_requirements(items, owner):
    for item in items:
        kind = item.get("type")
        if kind not in SUPPORTED_REQUIREMENTS:
            raise ValueError(f"{owner}: unsupported requirement {kind!r}")
        if kind == "research" and item.get("key") not in RESEARCH_DEFS:
            raise ValueError(f"{owner}: unknown research {item.get('key')!r}")
        if kind in ("resource", "total_resource") and item.get("resource") not in RESOURCE_DEFS:
            raise ValueError(f"{owner}: unknown resource {item.get('resource')!r}")


def _validate_effects(items, owner):
    for effect in items:
        kind = effect.get("type")
        if kind not in SUPPORTED_EFFECT_TYPES:
            raise ValueError(f"{owner}: unsupported effect {kind!r}")
        resource = effect.get("resource")
        if resource is not None and resource not in RESOURCE_DEFS:
            raise ValueError(f"{owner}: effect references unknown resource {resource!r}")
        for resource_key in effect.get("resources", []):
            if resource_key not in RESOURCE_DEFS:
                raise ValueError(f"{owner}: effect references unknown resource {resource_key!r}")
        job = effect.get("job")
        if job is not None and job not in SKELETON_JOB_DEFS:
            raise ValueError(f"{owner}: effect references unknown job {job!r}")


def _validate_research_graph():
    visiting = set()
    visited = set()

    def visit(key):
        if key in visiting:
            raise ValueError(f"Research prerequisite cycle reaches {key!r}")
        if key in visited:
            return
        visiting.add(key)
        for prerequisite in RESEARCH_DEFS[key].get("prerequisites", []):
            if prerequisite not in RESEARCH_DEFS:
                raise ValueError(f"Research {key!r}: unknown prerequisite {prerequisite!r}")
            visit(prerequisite)
        visiting.remove(key)
        visited.add(key)

    for key in RESEARCH_DEFS:
        visit(key)


def validate_content():
    if len({tab["key"] for tab in TAB_DEFS}) != len(TAB_DEFS):
        raise ValueError("Duplicate tab key")
    for tab in TAB_DEFS:
        if not all(str(tab.get(field, "")).strip() for field in ("label", "symbol", "scene")):
            raise ValueError(f"Tab {tab.get('key')!r}: missing label, symbol, or scene")
    for key, definition in RESOURCE_DEFS.items():
        if float(definition["base_capacity"]) <= 0:
            raise ValueError(f"Resource {key!r}: capacity must be positive")
        if not definition.get("accent") or not definition.get("accent_rgb"):
            raise ValueError(f"Resource {key!r}: missing visual accent")
        _validate_requirements(definition.get("visible_when", []), f"Resource {key!r}")
    for key, definition in SKELETON_JOB_DEFS.items():
        if definition.get("kind") not in ("resource", "grave_progress"):
            raise ValueError(f"Job {key!r}: unsupported kind")
        if definition.get("kind") == "resource" and definition.get("resource") not in RESOURCE_DEFS:
            raise ValueError(f"Job {key!r}: unknown output resource")
        if float(definition.get("base_rate", 0)) < 0:
            raise ValueError(f"Job {key!r}: rate cannot be negative")
        _validate_requirements(definition.get("visible_when", []), f"Job {key!r}")
    for key, definition in UPGRADE_DEFS.items():
        _validate_cost(definition.get("cost", {}), f"Upgrade {key!r}")
        _validate_requirements(definition.get("unlock", []), f"Upgrade {key!r}")
        _validate_effects(definition.get("effects", []), f"Upgrade {key!r}")
    for key, definition in RESEARCH_DEFS.items():
        if float(definition.get("duration", 0)) <= 0 or float(definition.get("knowledge_cost", 0)) < 0:
            raise ValueError(f"Research {key!r}: invalid duration or Knowledge cost")
        _validate_cost(definition.get("start_cost", {}), f"Research {key!r}")
        _validate_requirements(definition.get("unlock", []), f"Research {key!r}")
        _validate_effects(definition.get("effects", []), f"Research {key!r}")
    for key, definition in RECIPE_DEFS.items():
        _validate_cost(definition.get("cost", {}), f"Recipe {key!r}")
        _validate_cost(definition.get("produces", {}), f"Recipe {key!r}")
        _validate_requirements(definition.get("visible_when", []), f"Recipe {key!r}")
    for key, definition in ACTIVITY_DEFS.items():
        _validate_cost(definition.get("cost", {}), f"Activity {key!r}")
        _validate_cost(definition.get("reward", {}), f"Activity {key!r}")
        _validate_requirements(definition.get("visible_when", []), f"Activity {key!r}")
    if set(PART_DEFS) != set(SLOT_DEFS):
        raise ValueError("Assembly part and slot keys must match")
    _validate_research_graph()
    return True
