"""Resource balances, capacities, and atomic transactions."""

from game import effects, state
from game.content import RESOURCE_DEFS


def capacity(resource_key):
    value = float(RESOURCE_DEFS[resource_key]["base_capacity"])
    for effect in effects.purchased_effects("resource_capacity_multiplier"):
        if resource_key in effect.get("resources", []):
            value *= float(effect.get("multiplier", 1.0))
    for effect in effects.purchased_effects("resource_capacity_add"):
        if resource_key == effect.get("resource"):
            value += float(effect.get("amount", 0.0))
    return value


def add(resource_key, amount, *, count_generated=True, allow_overflow=False):
    amount = max(0.0, float(amount))
    current = float(state.game["resources"].get(resource_key, 0.0))
    maximum = float("inf") if allow_overflow else capacity(resource_key)
    new_amount = min(maximum, current + amount)
    gained = max(0.0, new_amount - current)
    state.game["resources"][resource_key] = new_amount
    if count_generated and gained:
        state.game["stats"]["total_generated"][resource_key] += gained
    return gained


def grant(rewards, *, multiplier=1.0, count_generated=True):
    return {
        key: add(key, amount * multiplier, count_generated=count_generated)
        for key, amount in rewards.items()
    }


def can_afford(costs):
    return all(
        float(state.game["resources"].get(key, 0.0)) >= float(amount)
        for key, amount in costs.items()
    )


def spend(costs):
    """Spend an entire cost or nothing; balances can never become negative."""

    if not can_afford(costs):
        return False
    for key, amount in costs.items():
        state.game["resources"][key] -= float(amount)
    return True


def spend_partial(resource_key, requested):
    available = float(state.game["resources"].get(resource_key, 0.0))
    spent = min(available, max(0.0, float(requested)))
    state.game["resources"][resource_key] = available - spent
    return spent
