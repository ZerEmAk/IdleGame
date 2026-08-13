"""Game definitions and configuration.

Most normal content additions should start in this file.

The important idea is to separate:

    definitions = what things ARE
    state       = what the player OWNS / HAS

For example, the Generator's cost belongs here, while the number of
Generators the player owns belongs in state.py.
"""


# ====================================================================
# PROJECT / SAVE CONFIGURATION
# ====================================================================

# Change this whenever you want the displayed game version to change.
GAME_VERSION = "0.1.0"

# Change this only when the save-file STRUCTURE becomes incompatible.
# Normal balance/content changes do not require changing it.
SAVE_SCHEMA_VERSION = 1

SAVE_KEY = "idle_framework_save_v1"
AUTOSAVE_SECONDS = 10.0
UI_REFRESH_SECONDS = 0.2

# Offline production is intentionally capped so leaving for months does
# not instantly fill every future system. Change or remove the cap later.
OFFLINE_PROGRESS_MAX_SECONDS = 8 * 60 * 60

# These become the bulk-buy buttons in the Buildings tab.
BUY_AMOUNTS = ("1", "10", "max")


# ====================================================================
# MANUAL ACTION
# ====================================================================

# A simple starter action. Replace it when the real game has its own
# opening mechanic, or remove the button entirely later.
MANUAL_ACTION = {
    "label": "Gain Credit",
    "resource": "credits",
    "amount": 1.0,
}


# ====================================================================
# RESOURCES
# ====================================================================

# Add a resource here and the framework automatically:
# - creates its player state
# - creates its left-side UI row
# - tracks total generated in stats
#
# Building production and upgrade effects can then refer to its key.
RESOURCE_DEFS = {
    "credits": {
        "name": "Credits",
        "description": "Example primary resource.",
        "base_capacity": 100.0,
    },
    "parts": {
        "name": "Parts",
        "description": "Example secondary resource.",
        "base_capacity": 100.0,
    },
    "knowledge": {
        "name": "Knowledge",
        "description": "Example progression resource.",
        "base_capacity": 50.0,
    },
}


# ====================================================================
# BUILDINGS
# ====================================================================

# A building can produce one or several resources.
# Cost grows every time another copy is bought.
BUILDING_DEFS = {
    "generator": {
        "name": "Generator",
        "description": "Basic automatic production.",
        "cost_resource": "credits",
        "base_cost": 10.0,
        "cost_growth": 1.15,
        "produces": {
            "credits": 1.0,
        },
    },
    "collector": {
        "name": "Collector",
        "description": "Introduces a second production chain.",
        "cost_resource": "credits",
        "base_cost": 25.0,
        "cost_growth": 1.15,
        "produces": {
            "parts": 0.5,
        },
    },
    "laboratory": {
        "name": "Laboratory",
        "description": "Produces a resource used for upgrades.",
        "cost_resource": "parts",
        "base_cost": 30.0,
        "cost_growth": 1.18,
        "produces": {
            "knowledge": 0.1,
        },
    },
}


# ====================================================================
# UPGRADES
# ====================================================================

# Upgrades are one-time purchases.
#
# The framework currently understands these effect types:
#
#   building_production_multiplier
#   resource_capacity_multiplier
#
# To invent a NEW kind of upgrade effect, add a new effect type here,
# then teach logic.py how that effect should change the game.
UPGRADE_DEFS = {
    "efficient_generators": {
        "name": "Efficient Generators",
        "description": "Generators produce twice as much.",
        "cost_resource": "knowledge",
        "cost": 10.0,
        "effects": [
            {
                "type": "building_production_multiplier",
                "building": "generator",
                "multiplier": 2.0,
            }
        ],
    },
    "expanded_storage": {
        "name": "Expanded Storage",
        "description": "Doubles Credits and Parts capacity.",
        "cost_resource": "parts",
        "cost": 50.0,
        "effects": [
            {
                "type": "resource_capacity_multiplier",
                "resources": ["credits", "parts"],
                "multiplier": 2.0,
            }
        ],
    },
}


# ====================================================================
# TABS
# ====================================================================

# The UI module knows how to render these built-in tab keys.
# Reorder this list to reorder the tabs.
TAB_DEFS = [
    {"key": "overview", "label": "Overview"},
    {"key": "buildings", "label": "Buildings"},
    {"key": "upgrades", "label": "Upgrades"},
    {"key": "stats", "label": "Stats"},
]
