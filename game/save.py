"""Browser save/load helpers.

The framework uses localStorage because it is synchronous and easy to inspect
while learning. Saves are local to the website/origin in the current browser.
"""

import json
import time

from pyscript import window

from game import state
from game.definitions import (
    BUY_AMOUNTS,
    OFFLINE_PROGRESS_MAX_SECONDS,
    SAVE_KEY,
)


# ====================================================================
# SAVE
# ====================================================================


def save_game():
    """Serialize the current state to browser localStorage."""

    state.game["last_save"] = time.time()
    window.localStorage.setItem(
        SAVE_KEY,
        json.dumps(state.game),
    )


# ====================================================================
# SAFE MERGE
# ====================================================================


def merge_known_keys(default, saved):
    """Merge saved values into a fresh state without importing unknown keys.

    This is useful during development. If you add a NEW resource later, the
    fresh state contains it even when an older save did not.
    """

    if not isinstance(default, dict) or not isinstance(saved, dict):
        return

    for key, saved_value in saved.items():
        if key not in default:
            continue

        default_value = default[key]

        if isinstance(default_value, dict) and isinstance(saved_value, dict):
            merge_known_keys(default_value, saved_value)
        else:
            default[key] = saved_value


# ====================================================================
# LOAD
# ====================================================================


def load_game():
    """Load a save.

    Returns:
        (loaded, offline_seconds, error_message)

    Invalid saves are NOT automatically deleted, which makes debugging safer.
    """

    raw = window.localStorage.getItem(SAVE_KEY)

    if raw is None:
        return False, 0.0, None

    raw = str(raw).strip()

    if not raw:
        return False, 0.0, None

    try:
        saved_data = json.loads(raw)

        if not isinstance(saved_data, dict):
            raise ValueError("Save data is not an object/dictionary.")

        fresh = state.new_game_state()
        merge_known_keys(fresh, saved_data)

        # Prevent an old/edited save from putting the selector into a value
        # the purchase code does not understand.
        if str(fresh.get("buy_amount")) not in BUY_AMOUNTS:
            fresh["buy_amount"] = BUY_AMOUNTS[0]

        previous_save_time = float(fresh.get("last_save", 0.0) or 0.0)
        state.game = fresh

        offline_seconds = 0.0

        if previous_save_time > 0:
            offline_seconds = max(
                0.0,
                min(
                    time.time() - previous_save_time,
                    float(OFFLINE_PROGRESS_MAX_SECONDS),
                ),
            )

        return True, offline_seconds, None

    except Exception as error:
        return False, 0.0, str(error)


# ====================================================================
# DELETE
# ====================================================================


def delete_save():
    """Delete this game's local browser save."""

    window.localStorage.removeItem(SAVE_KEY)
