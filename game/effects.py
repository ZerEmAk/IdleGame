"""Generic modifier resolver for purchased upgrades and completed research."""

from game import state
from game.content import RESEARCH_DEFS, UPGRADE_DEFS


def purchased_effects(effect_type):
    """Yield active effect records of ``effect_type`` from every content source."""

    for key, definition in UPGRADE_DEFS.items():
        if state.game["upgrades"].get(key, False):
            for effect in definition.get("effects", []):
                if effect.get("type") == effect_type:
                    yield effect

    completed = state.game["research"]["completed"]
    for key, definition in RESEARCH_DEFS.items():
        if completed.get(key, False):
            for effect in definition.get("effects", []):
                if effect.get("type") == effect_type:
                    yield effect


def multiplier(effect_type, **filters):
    value = 1.0
    for effect in purchased_effects(effect_type):
        if any(
            effect.get(name) is not None and effect.get(name) != expected
            for name, expected in filters.items()
        ):
            continue
        value *= float(effect.get("multiplier", 1.0))
    return value


def additive(effect_type, **filters):
    value = 0.0
    for effect in purchased_effects(effect_type):
        if any(
            effect.get(name) is not None and effect.get(name) != expected
            for name, expected in filters.items()
        ):
            continue
        value += float(effect.get("amount", 0.0))
    return value
