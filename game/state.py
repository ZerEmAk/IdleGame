"""Saveable progress and short-lived presentation state.

The shape is deliberately JSON-safe. Systems may mutate ``game`` but must not
store DOM nodes, callbacks, or Python objects inside it.
"""

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
            "part_order": list(PART_DEFS),
            "frame_ready": False,
        },
        "skeletons": [],
        "next_skeleton_id": 1,
        "upgrades": {key: False for key in UPGRADE_DEFS},
        "research": {
            "completed": {key: False for key in RESEARCH_DEFS},
            "active": None,
            "queue": [],
        },
        "activities": {
            "excavation": {
                "active": False,
                "elapsed": 0.0,
                "target": 0.5,
                "stopped_marker": 0.0,
                "result": None,
            },
            "seance": {
                "phase": "idle",
                "sequence": [],
                "input_index": 0,
                "reveal_remaining": 0.0,
                "reveal_total": 0.0,
                "feedback": "Begin when the circle is quiet.",
                "last_sigil": None,
                "feedback_tone": "idle",
            },
        },
        "preferences": {
            "log_filter": "all",
            "reduced_motion": False,
        },
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
            "excavations_completed": 0,
            "perfect_excavations": 0,
            "seances_started": 0,
            "seances_completed": 0,
            "recipes_crafted": 0,
            "relics_found": 0,
            "total_generated": {key: 0.0 for key in RESOURCE_DEFS},
        },
        "log": [],
        "next_log_id": 1,
        "last_save": 0.0,
    }


game = new_game_state()

# Holding, dragging, selection feedback, and the current tab are never saved.
runtime = {
    "channeling": False,
    "dragged_part": None,
    "assembly_feedback": "Drag each part onto its matching slot.",
    "drag_pointer": None,
}


def reset_runtime():
    runtime["channeling"] = False
    runtime["dragged_part"] = None
    runtime["assembly_feedback"] = "Drag each part onto its matching slot."
    runtime["drag_pointer"] = None


def reset_state():
    global game
    game = new_game_state()
    reset_runtime()


def add_log(message, category="system", tone="info", subject=None):
    """Emit a structured event consumed by the categorized event-log UI."""

    event_id = int(game.get("next_log_id", 1))
    game["next_log_id"] = event_id + 1
    game["log"].append({
        "id": event_id,
        "timestamp": time.time(),
        "game_time": float(game.get("stats", {}).get("active_time", 0.0)),
        "category": str(category),
        "tone": str(tone),
        "message": str(message),
        "subject": None if subject is None else str(subject),
    })
    game["log"] = game["log"][-150:]
