"""Application entry point for The First Rite."""

import asyncio
import time

from pyscript import web, when, window

from game import logic, save, state, ui, validation
from game.definitions import AUTOSAVE_SECONDS, UI_REFRESH_SECONDS


def apply_offline_progress(offline_seconds):
    """Simulate a load interval once, then stamp it as consumed immediately."""

    logic.advance_game(offline_seconds, offline=True)
    return save.save_game()


# ====================================================================
# STATIC PAGE EVENTS
# ====================================================================
#
# These elements exist directly in index.html, so @when selectors are safe.
# Dynamic building/upgrade buttons attach handlers as they are created in ui.py.
# ====================================================================


@when("click", "#settings-button")
def open_settings(event):
    logic.set_channeling(False)
    web.page["settings-dialog"].showModal()


@when("click", "#patch-notes-button")
def open_patch_notes(event):
    logic.set_channeling(False)
    web.page["patch-notes-dialog"].showModal()


@when("click", "#close-settings")
def close_settings(event):
    web.page["settings-dialog"].close()


@when("click", "#close-patch-notes")
def close_patch_notes(event):
    web.page["patch-notes-dialog"].close()


@when("click", "#open-skeletons-tab")
def open_skeletons_tab(event):
    ui.switch_tab("skeletons")


@when("change", "#reduced-motion")
def reduced_motion_changed(event):
    state.game["preferences"]["reduced_motion"] = bool(event.currentTarget.checked)
    ui.apply_preferences()
    save.save_game()


@when("click", "#save-game")
def manual_save(event):
    saved, error = save.save_game()
    if saved:
        state.add_log("Game saved.", category="system", tone="success")
        ui.set_save_status("Saved")
    else:
        state.add_log(f"Could not save game: {error}", category="system", tone="warning")
        ui.set_save_status("Save failed")
    ui.render_log()


@when("click", "#load-game")
def manual_load(event):
    loaded, offline_seconds, error = save.load_game()

    if error:
        state.add_log(f"Could not load save: {error}", category="system", tone="warning")
        ui.render_log()
        return

    if not loaded:
        state.add_log("No save exists yet.", category="system")
        ui.render_log()
        return

    offline_saved = True
    if offline_seconds > 0:
        offline_saved, offline_error = apply_offline_progress(offline_seconds)
        if not offline_saved:
            state.add_log(
                f"Offline progress was applied but could not be saved: {offline_error}",
                category="system",
                tone="warning",
            )

    state.add_log("Save loaded.", category="system", tone="success")
    ui.set_save_status("Loaded" if offline_saved else "Loaded; save failed")
    ui.apply_preferences()
    ui.render_skeleton_lists(force=True)
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
    state.add_log("New game started.", category="system")

    ui.set_save_status("Not saved yet")
    ui.apply_preferences()
    ui.render_skeleton_lists(force=True)
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


validation.validate_content()
loaded, offline_seconds, load_error = save.load_game()

if load_error:
    # Keep the fresh game if the save is broken. The bad save is not deleted,
    # so it can still be inspected while debugging.
    state.add_log(f"Save could not be loaded: {load_error}", category="system", tone="warning")
elif loaded:
    if offline_seconds > 0:
        offline_saved, offline_error = apply_offline_progress(offline_seconds)
        state.add_log(
            f"Processed {ui.format_time(offline_seconds)} of offline progress.",
            category="system",
        )
        if not offline_saved:
            state.add_log(
                f"Offline progress could not be persisted: {offline_error}",
                category="system",
                tone="warning",
            )

    state.add_log("Save loaded.", category="system", tone="success")
else:
    state.add_log("New game started.", category="system")

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

    previous_time = time.perf_counter()
    ui_timer = 0.0
    slow_ui_timer = 0.0
    autosave_timer = 0.0

    while True:
        try:
            # Production uses real elapsed time; sleeping avoids a busy loop.
            # Keep the game tick at least as responsive as the configured UI
            # refresh. Previously the fixed 0.1 second sleep limited all
            # counters and bars to ten visible updates per second.
            await asyncio.sleep(min(0.05, UI_REFRESH_SECONDS))

            current_time = time.perf_counter()
            delta = max(0.0, current_time - previous_time)
            previous_time = current_time

            if bool(window.document.hidden):
                logic.set_channeling(False)

            logic.advance_game(delta)

            ui_timer += delta
            slow_ui_timer += delta
            autosave_timer += delta

            if ui_timer >= UI_REFRESH_SECONDS:
                ui.update_fast_ui()
                ui_timer = 0.0

            if slow_ui_timer >= 0.25:
                ui.update_ui()
                slow_ui_timer = 0.0

            if autosave_timer >= AUTOSAVE_SECONDS:
                saved, _error = save.save_game()
                ui.set_save_status("Autosaved" if saved else "Autosave failed")
                autosave_timer = 0.0
        except Exception as error:
            print("GAME LOOP ERROR:", repr(error))
            raise


asyncio.create_task(game_loop())
