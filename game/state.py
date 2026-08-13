"""Saveable progress and short-lived input state."""

import time

from game.content import PART_DEFS, RESEARCH_DEFS, RESOURCE_DEFS, UPGRADE_DEFS
from game.definitions import SAVE_SCHEMA_VERSION


def new_game_state():
    return {
        "save_schema": SAVE_SCHEMA_VERSION,
        "resources": {key: 0.0 for key in RESOURCE_DEFS},
        "unlocks": {
            "graveyard": False,
            "soul_trap": False,
            "assembly": False,
            "summoning": False,
        },
        "grave": {"progress": 0.0},
        "soul_trap_crafted": False,
        "assembly": {
            "started": False,
            "selected_part": None,
            "placed": {key: False for key in PART_DEFS},
            "frame_ready": False,
        },
        "skeletons": [],
        "next_skeleton_id": 1,
        "upgrades": {key: False for key in UPGRADE_DEFS},
        "research": {key: False for key in RESEARCH_DEFS},
        "stats": {
            "active_time": 0.0,
            "offline_time": 0.0,
            "channel_seconds": 0.0,
            "dig_clicks": 0,
            "graves_opened": 0,
            "soul_traps_crafted": 0,
            "assembly_mistakes": 0,
            "skeletons_summoned": 0,
            "servants_expired": 0,
            "upgrades_bought": 0,
            "research_completed": 0,
            "total_generated": {key: 0.0 for key in RESOURCE_DEFS},
        },
        "log": [],
        "last_save": 0.0,
    }


game = new_game_state()

# Holding, dragging, selection feedback, and the current tab are never saved.
runtime = {
    "channeling": False,
    "dragged_part": None,
    "assembly_feedback": "Drag each part onto its matching slot.",
}


def reset_runtime():
    runtime["channeling"] = False
    runtime["dragged_part"] = None
    runtime["assembly_feedback"] = "Drag each part onto its matching slot."


def reset_state():
    global game
    game = new_game_state()
    reset_runtime()


def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    game["log"].append(f"[{timestamp}] {message}")
    game["log"] = game["log"][-100:]
