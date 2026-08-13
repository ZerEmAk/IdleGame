"""Core game rules.

This module knows nothing about HTML. That is intentional.
The UI asks these functions what the game state means, and actions here
change state. Keeping game rules separate from visuals makes later redesigns
much easier.
"""

from game import state
from game.definitions import (
    BUILDING_DEFS,
    MANUAL_ACTION,
    RESOURCE_DEFS,
    UPGRADE_DEFS,
)


# ====================================================================
# UPGRADE EFFECT HELPERS
# ====================================================================


def purchased_effects(effect_type):
    """Yield purchased upgrade effects of a specific type."""

    for upgrade_key, upgrade_def in UPGRADE_DEFS.items():
        if not state.game["upgrades"].get(upgrade_key, False):
            continue

        for effect in upgrade_def.get("effects", []):
            if effect.get("type") == effect_type:
                yield effect



def building_production_multiplier(building_key):
    """Return the combined production multiplier for one building."""

    multiplier = 1.0

    for effect in purchased_effects("building_production_multiplier"):
        if effect.get("building") == building_key:
            multiplier *= float(effect.get("multiplier", 1.0))

    return multiplier


# ====================================================================
# RESOURCE CALCULATIONS
# ====================================================================


def resource_capacity(resource_key):
    """Return the player's current capacity for a resource."""

    capacity = float(RESOURCE_DEFS[resource_key]["base_capacity"])

    for effect in purchased_effects("resource_capacity_multiplier"):
        if resource_key in effect.get("resources", []):
            capacity *= float(effect.get("multiplier", 1.0))

    return capacity



def production_rates():
    """Return a dict containing production per second for every resource."""

    rates = {
        resource_key: 0.0
        for resource_key in RESOURCE_DEFS
    }

    for building_key, owned in state.game["buildings"].items():
        definition = BUILDING_DEFS[building_key]
        multiplier = building_production_multiplier(building_key)

        for resource_key, base_rate in definition.get("produces", {}).items():
            rates[resource_key] += (
                int(owned)
                * float(base_rate)
                * multiplier
            )

    return rates



def add_resource(resource_key, amount, count_generated=True):
    """Add a resource while respecting capacity.

    Returns the amount that was ACTUALLY added. If storage is full, the
    returned value can be smaller than the requested amount.
    """

    current = float(state.game["resources"][resource_key])
    capacity = resource_capacity(resource_key)
    new_amount = min(current + float(amount), capacity)
    gained = max(0.0, new_amount - current)

    state.game["resources"][resource_key] = new_amount

    if count_generated:
        state.game["stats"]["total_generated"][resource_key] += gained

    return gained


# ====================================================================
# BUILDING COSTS / BUYING
# ====================================================================


def building_unit_cost(building_key, owned_number):
    """Cost of the next building at a specific owned count."""

    definition = BUILDING_DEFS[building_key]
    base_cost = float(definition["base_cost"])
    growth = float(definition["cost_growth"])

    return round(base_cost * (growth ** int(owned_number)))



def building_purchase_info(building_key):
    """Return ``(quantity, total_cost)`` for the selected buy amount.

    The same function powers Buy 1, Buy 10, and Buy Max.
    """

    definition = BUILDING_DEFS[building_key]
    resource_key = definition["cost_resource"]
    available = float(state.game["resources"][resource_key])
    owned = int(state.game["buildings"][building_key])
    selected = str(state.game["buy_amount"])

    if selected == "max":
        quantity = 0
        total_cost = 0

        # A loop is easy to understand and perfectly fine for this starter.
        # If your late game eventually buys millions at once, replace this
        # with a geometric-series calculation.
        while quantity < 10000:
            next_cost = building_unit_cost(
                building_key,
                owned + quantity,
            )

            if total_cost + next_cost > available:
                break

            total_cost += next_cost
            quantity += 1

        return quantity, total_cost

    quantity = max(1, int(selected))
    total_cost = 0

    for offset in range(quantity):
        total_cost += building_unit_cost(
            building_key,
            owned + offset,
        )

    return quantity, total_cost



def buy_building(building_key):
    """Try to buy the selected amount of a building.

    Returns True when a purchase happened, otherwise False.
    """

    definition = BUILDING_DEFS[building_key]
    resource_key = definition["cost_resource"]
    quantity, total_cost = building_purchase_info(building_key)

    if quantity <= 0:
        return False

    if state.game["resources"][resource_key] < total_cost:
        return False

    state.game["resources"][resource_key] -= total_cost
    state.game["buildings"][building_key] += quantity

    state.add_log(
        f"Bought {quantity} {definition['name']}"
        + ("." if quantity == 1 else "s.")
    )

    return True


# ====================================================================
# UPGRADES
# ====================================================================


def buy_upgrade(upgrade_key):
    """Try to purchase a one-time upgrade."""

    if state.game["upgrades"].get(upgrade_key, False):
        return False

    definition = UPGRADE_DEFS[upgrade_key]
    resource_key = definition["cost_resource"]
    cost = float(definition["cost"])

    if state.game["resources"][resource_key] < cost:
        return False

    state.game["resources"][resource_key] -= cost
    state.game["upgrades"][upgrade_key] = True
    state.add_log(f"Purchased upgrade: {definition['name']}.")

    return True


# ====================================================================
# MANUAL ACTION
# ====================================================================


def perform_manual_action():
    """Perform the starter manual action defined in definitions.py."""

    resource_key = MANUAL_ACTION["resource"]
    amount = float(MANUAL_ACTION["amount"])

    gained = add_resource(resource_key, amount)
    state.game["stats"]["manual_actions"] += 1

    return gained


# ====================================================================
# GAME TIME / PRODUCTION
# ====================================================================


def advance_game(seconds, offline=False):
    """Advance production by a real amount of elapsed time.

    Using elapsed time instead of "add 1 every tick" keeps production correct
    when the browser runs slowly or a tab is throttled.
    """

    seconds = max(0.0, float(seconds))
    rates = production_rates()

    for resource_key, rate in rates.items():
        add_resource(
            resource_key,
            float(rate) * seconds,
        )

    if offline:
        state.game["stats"]["offline_time"] += seconds
    else:
        state.game["stats"]["active_time"] += seconds
