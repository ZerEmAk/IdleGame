"""Player state.

Only SAVEABLE progress belongs in the ``game`` dictionary.
Definitions such as costs, names and production values belong in
``definitions.py`` instead.
"""

import time

from game.definitions import (
    BUILDING_DEFS,
    BUY_AMOUNTS,
    RESOURCE_DEFS,
    SAVE_SCHEMA_VERSION,
    UPGRADE_DEFS,
)


# ====================================================================
# NEW GAME
# ====================================================================


def new_game_state():
    """Create a fresh save using the current definitions.

    Because keys are generated from the definitions, adding a new resource,
    building, or upgrade usually does NOT require editing this function.
    """

    return {
        "save_schema": SAVE_SCHEMA_VERSION,
        "resources": {
            key: 0.0
            for key in RESOURCE_DEFS
        },
        "buildings": {
            key: 0
            for key in BUILDING_DEFS
        },
        "upgrades": {
            key: False
            for key in UPGRADE_DEFS
        },
        "buy_amount": BUY_AMOUNTS[0],
        "stats": {
            "active_time": 0.0,
            "offline_time": 0.0,
            "manual_actions": 0,
            "total_generated": {
                key: 0.0
                for key in RESOURCE_DEFS
            },
        },
        "log": [],
        "last_save": 0.0,
    }


# All modules access state through ``state.game``.
# This is important because loading/resetting replaces the whole dictionary.
game = new_game_state()


# ====================================================================
# STATE HELPERS
# ====================================================================


def reset_state():
    """Replace the current player state with a fresh game."""

    global game
    game = new_game_state()



def add_log(message):
    """Add one event-log message and keep the log from growing forever."""

    timestamp = time.strftime("%H:%M:%S")
    game["log"].append(f"[{timestamp}] {message}")
    game["log"] = game["log"][-100:]
