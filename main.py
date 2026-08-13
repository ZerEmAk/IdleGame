"""Application entry point.

main.py wires the modules together:

    load state
    -> build UI
    -> attach static events
    -> run the timed game loop

Most game content should NOT be added here.
"""

import asyncio
import time

from pyscript import web, when, window

from game import logic, save, state, ui
from game.definitions import AUTOSAVE_SECONDS, UI_REFRESH_SECONDS


# ====================================================================
# STATIC PAGE EVENTS
# ====================================================================
#
# These elements exist directly in index.html, so @when selectors are safe.
# Dynamic building/upgrade buttons attach handlers as they are created in ui.py.
# ====================================================================


@when("click", "#settings-button")
def open_settings(event):
    web.page["settings-dialog"].showModal()


@when("click", "#close-settings")
def close_settings(event):
    web.page["settings-dialog"].close()


@when("click", "#save-game")
def manual_save(event):
    save.save_game()
    state.add_log("Game saved.")
    ui.set_save_status("Saved")
    ui.render_log()


@when("click", "#load-game")
def manual_load(event):
    loaded, offline_seconds, error = save.load_game()

    if error:
        state.add_log(f"Could not load save: {error}")
        ui.render_log()
        return

    if not loaded:
        state.add_log("No save exists yet.")
        ui.render_log()
        return

    if offline_seconds > 0:
        logic.advance_game(offline_seconds, offline=True)

    state.add_log("Save loaded.")
    ui.set_save_status("Loaded")
    ui.update_ui()
    ui.render_log()


@when("click", "#reset-game")
def reset_game(event):
    confirmed = window.confirm(
        "Delete the local save and reset all current progress?"
    )

    if not confirmed:
        return

    save.delete_save()
    state.reset_state()
    state.add_log("New game started.")

    ui.set_save_status("Not saved yet")
    ui.update_ui()
    ui.render_log()
    web.page["settings-dialog"].close()


@when("click", "#clear-log")
def clear_log(event):
    state.game["log"] = []
    ui.render_log()


# ====================================================================
# STARTUP
# ====================================================================


loaded, offline_seconds, load_error = save.load_game()

if load_error:
    # Keep the fresh game if the save is broken. The bad save is not deleted,
    # so it can still be inspected while debugging.
    state.add_log(f"Save could not be loaded: {load_error}")
elif loaded:
    if offline_seconds > 0:
        logic.advance_game(offline_seconds, offline=True)
        state.add_log(
            f"Processed {ui.format_time(offline_seconds)} of offline progress."
        )

    state.add_log("Save loaded.")
else:
    state.add_log("New game started.")

try:
    ui.build_ui()
    ui.update_ui()
    ui.set_save_status("Ready")
except Exception as error:
    web.page["save-status"].textContent = "ERROR"
    print("STARTUP ERROR:", repr(error))
    raise


# ====================================================================
# MAIN GAME LOOP
# ====================================================================


async def game_loop():
    """Continuously advance production, refresh the UI, and autosave."""

    previous_time = time.time()
    ui_timer = 0.0
    autosave_timer = 0.0

    while True:
        try:
            # Production uses real elapsed time; sleeping avoids a busy loop.
            await asyncio.sleep(0.1)

            current_time = time.time()
            delta = max(0.0, current_time - previous_time)
            previous_time = current_time

            logic.advance_game(delta)

            ui_timer += delta
            autosave_timer += delta

            if ui_timer >= UI_REFRESH_SECONDS:
                ui.update_ui()
                ui_timer = 0.0

            if autosave_timer >= AUTOSAVE_SECONDS:
                save.save_game()
                ui.set_save_status("Autosaved")
                autosave_timer = 0.0
        except Exception as error:
            print("GAME LOOP ERROR:", repr(error))
            raise


asyncio.create_task(game_loop())
