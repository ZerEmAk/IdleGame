"""Browser persistence, ordered migrations, and defensive normalization."""

import json
import math
import time

from pyscript import window

from game import migrations, state
from game.content import (
    LOG_CATEGORY_DEFS,
    PART_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
    SEANCE_SIGIL_DEFS,
    SKELETON_JOB_DEFS,
    UPGRADE_DEFS,
)
from game.definitions import (
    BASE_GRAVE_PROGRESS_REQUIRED,
    OFFLINE_PROGRESS_MAX_SECONDS,
    SAVE_KEY,
    SAVE_SCHEMA_VERSION,
)


def save_game():
    """Persist the current JSON state without allowing storage errors to stop play."""

    try:
        state.game["last_save"] = time.time()
        window.localStorage.setItem(SAVE_KEY, json.dumps(state.game))
        return True, None
    except Exception as error:
        return False, str(error)


def merge_known_keys(default, saved):
    """Merge only fields understood by this build into a fresh state object."""

    if not isinstance(default, dict) or not isinstance(saved, dict):
        return
    for key, saved_value in saved.items():
        if key not in default:
            continue
        default_value = default[key]
        if isinstance(default_value, dict):
            if isinstance(saved_value, dict):
                merge_known_keys(default_value, saved_value)
            # A malformed collection must not replace the known schema shape.
            continue
        default[key] = saved_value


def migrate_saved_data(saved):
    if not isinstance(saved, dict):
        raise ValueError("Save data is not an object.")
    return migrations.migrate(saved, SAVE_SCHEMA_VERSION)


def _number(value, default=0.0, minimum=0.0, maximum=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default)
    if not math.isfinite(result):
        result = float(default)
    result = max(float(minimum), result)
    if maximum is not None:
        result = min(float(maximum), result)
    return result


def _clean_name(value, skeleton_id):
    text = "".join(char for char in str(value or "") if ord(char) >= 32 and ord(char) != 127)
    text = " ".join(text.split())[:24].strip()
    return text or f"Skeleton #{skeleton_id}"


def normalize_state(game):
    """Clamp hostile/corrupt values and restore all content registry keys."""

    game["save_schema"] = SAVE_SCHEMA_VERSION

    for key in RESOURCE_DEFS:
        game["resources"][key] = _number(game["resources"].get(key), maximum=1e300)
    for key in game["unlocks"]:
        game["unlocks"][key] = bool(game["unlocks"].get(key, False))

    game["grave"]["progress"] = _number(
        game["grave"].get("progress"),
        maximum=BASE_GRAVE_PROGRESS_REQUIRED - 0.000001,
    )
    game["soul_trap_crafted"] = bool(game.get("soul_trap_crafted"))

    assembly = game["assembly"]
    assembly["started"] = bool(assembly.get("started"))
    assembly["frame_ready"] = bool(assembly.get("frame_ready"))
    placed = assembly.get("placed") if isinstance(assembly.get("placed"), dict) else {}
    assembly["placed"] = {key: bool(placed.get(key, False)) for key in PART_DEFS}
    raw_order = assembly.get("part_order")
    assembly["part_order"] = (
        list(raw_order)
        if isinstance(raw_order, list)
        and len(raw_order) == len(PART_DEFS)
        and set(raw_order) == set(PART_DEFS)
        else list(PART_DEFS)
    )
    selected = assembly.get("selected_part")
    if selected not in PART_DEFS or assembly["placed"].get(selected, False):
        selected = None
    assembly["selected_part"] = selected
    if all(assembly["placed"].values()):
        assembly["frame_ready"] = True
    if assembly["frame_ready"]:
        assembly["started"] = False
        assembly["selected_part"] = None

    normalized_skeletons = []
    used_ids = set()
    raw_skeletons = game.get("skeletons", [])
    if isinstance(raw_skeletons, list):
        for raw in raw_skeletons[:250]:
            if not isinstance(raw, dict):
                continue
            skeleton_id = int(_number(raw.get("id"), default=len(used_ids) + 1, minimum=1))
            while skeleton_id in used_ids:
                skeleton_id += 1
            remaining = _number(raw.get("remaining_seconds"), maximum=10 * 365 * 86400)
            if remaining <= 0:
                continue
            maximum = max(remaining, _number(raw.get("maximum_seconds"), default=remaining, maximum=10 * 365 * 86400))
            job = raw.get("job") if raw.get("job") in SKELETON_JOB_DEFS else "mana"
            used_ids.add(skeleton_id)
            normalized_skeletons.append({
                "id": skeleton_id,
                "name": _clean_name(raw.get("name"), skeleton_id),
                "remaining_seconds": remaining,
                "maximum_seconds": maximum,
                "job": job,
            })
    game["skeletons"] = normalized_skeletons
    game["next_skeleton_id"] = max(
        int(_number(game.get("next_skeleton_id"), default=1, minimum=1)),
        max(used_ids, default=0) + 1,
    )

    game["upgrades"] = {
        key: bool(game.get("upgrades", {}).get(key, False)) for key in UPGRADE_DEFS
    }
    research_state = game["research"]
    completed = research_state.get("completed") if isinstance(research_state.get("completed"), dict) else {}
    research_state["completed"] = {key: bool(completed.get(key, False)) for key in RESEARCH_DEFS}
    active = research_state.get("active")
    if not isinstance(active, dict) or active.get("key") not in RESEARCH_DEFS or research_state["completed"].get(active.get("key"), False):
        active = None
    else:
        definition = RESEARCH_DEFS[active["key"]]
        active = {
            "key": active["key"],
            "progress": _number(active.get("progress"), maximum=float(definition["duration"])),
            "knowledge_spent": _number(active.get("knowledge_spent"), maximum=float(definition["knowledge_cost"])),
            "paused": bool(active.get("paused")),
        }
    research_state["active"] = active
    active_key = active["key"] if active else None
    queue = []
    for key in research_state.get("queue", []) if isinstance(research_state.get("queue"), list) else []:
        if key in RESEARCH_DEFS and key != active_key and key not in queue and not research_state["completed"].get(key):
            queue.append(key)
    research_state["queue"] = queue[:32]

    activities = game["activities"]
    excavation = activities["excavation"]
    excavation["active"] = bool(excavation.get("active"))
    excavation["elapsed"] = _number(excavation.get("elapsed"), maximum=60)
    excavation["target"] = _number(excavation.get("target"), default=0.5, maximum=1)
    excavation["stopped_marker"] = _number(excavation.get("stopped_marker"), maximum=1)
    excavation["result"] = (
        excavation.get("result")
        if excavation.get("result") in (None, "perfect", "good", "glancing")
        else None
    )
    seance = activities["seance"]
    if seance.get("phase") not in ("idle", "reveal", "input", "result"):
        seance["phase"] = "idle"
    raw_sequence = seance.get("sequence") if isinstance(seance.get("sequence"), list) else []
    seance["sequence"] = [key for key in raw_sequence if key in SEANCE_SIGIL_DEFS][:12]
    seance["input_index"] = int(_number(seance.get("input_index"), maximum=len(seance["sequence"])))
    seance["reveal_remaining"] = _number(seance.get("reveal_remaining"), maximum=60)
    seance["reveal_total"] = max(
        seance["reveal_remaining"],
        _number(seance.get("reveal_total"), maximum=60),
    )
    seance["feedback"] = str(seance.get("feedback", "Begin when the circle is quiet."))[:160]
    seance["last_sigil"] = (
        seance.get("last_sigil") if seance.get("last_sigil") in SEANCE_SIGIL_DEFS else None
    )
    seance["feedback_tone"] = (
        seance.get("feedback_tone")
        if seance.get("feedback_tone")
        in ("idle", "reveal", "input", "correct", "failure", "success")
        else "idle"
    )
    if not seance["sequence"] and seance["phase"] != "idle":
        seance["phase"] = "idle"
        seance["input_index"] = 0
    elif seance["phase"] == "input" and seance["input_index"] >= len(seance["sequence"]):
        # A corrupt/interrupted save must never index beyond the sequence.
        seance["phase"] = "result"
        seance["feedback"] = "The interrupted circle has gone quiet."

    preferences = game["preferences"]
    preferences["log_filter"] = preferences.get("log_filter") if preferences.get("log_filter") in LOG_CATEGORY_DEFS else "all"
    preferences["reduced_motion"] = bool(preferences.get("reduced_motion"))

    stats = game["stats"]
    for key in ("active_time", "offline_time", "channel_seconds"):
        stats[key] = _number(stats.get(key))
    counter_keys = (
        "dig_clicks", "graves_opened", "soul_traps_crafted",
        "assembly_mistakes", "skeletons_summoned", "servants_expired",
        "upgrades_bought", "research_completed", "excavations_completed",
        "perfect_excavations", "seances_started", "seances_completed",
        "recipes_crafted", "relics_found",
    )
    for key in counter_keys:
        stats[key] = int(_number(stats.get(key)))
    for key in RESOURCE_DEFS:
        stats["total_generated"][key] = _number(stats["total_generated"].get(key))

    normalized_log = []
    next_id = 1
    raw_log = game.get("log", []) if isinstance(game.get("log"), list) else []
    for raw in raw_log[-150:]:
        if not isinstance(raw, dict):
            raw = {"message": str(raw)}
        event_id = int(_number(raw.get("id"), default=next_id, minimum=1))
        next_id = max(next_id, event_id + 1)
        category = raw.get("category") if raw.get("category") in LOG_CATEGORY_DEFS and raw.get("category") != "all" else "system"
        normalized_log.append({
            "id": event_id,
            # Windows ``localtime`` cannot render arbitrarily large floats.
            "timestamp": _number(
                raw.get("timestamp"), default=time.time(), maximum=4_102_444_800
            ),
            "game_time": _number(raw.get("game_time")),
            "category": category,
            "tone": str(raw.get("tone", "info"))[:20],
            "message": str(raw.get("message", ""))[:500],
            "subject": None if raw.get("subject") is None else str(raw.get("subject"))[:80],
        })
    game["log"] = normalized_log
    game["next_log_id"] = max(int(_number(game.get("next_log_id"), default=next_id, minimum=1)), next_id)
    game["last_save"] = _number(game.get("last_save"))


def load_game():
    state.reset_runtime()
    raw = window.localStorage.getItem(SAVE_KEY)
    raw_text = "" if raw is None else str(raw).strip()
    if not raw_text or raw_text.lower() in ("none", "null", "undefined"):
        return False, 0.0, None
    try:
        saved_data = migrate_saved_data(json.loads(raw_text))
        fresh = state.new_game_state()
        merge_known_keys(fresh, saved_data)
        normalize_state(fresh)
        previous_save_time = fresh["last_save"]
        state.game = fresh
        offline_seconds = 0.0
        if previous_save_time > 0:
            offline_seconds = max(0.0, min(time.time() - previous_save_time, float(OFFLINE_PROGRESS_MAX_SECONDS)))
        return True, offline_seconds, None
    except Exception as error:
        return False, 0.0, str(error)


def delete_save():
    window.localStorage.removeItem(SAVE_KEY)
