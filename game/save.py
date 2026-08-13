"""Browser persistence, v1 migration, and defensive normalization."""

import json
import math
import time

from pyscript import window

from game import state
from game.content import (
    PART_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
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
    state.game["last_save"] = time.time()
    window.localStorage.setItem(SAVE_KEY, json.dumps(state.game))


def merge_known_keys(default, saved):
    if not isinstance(default, dict) or not isinstance(saved, dict):
        return

    for key, saved_value in saved.items():
        if key not in default:
            continue
        default_value = default[key]
        if isinstance(default_value, dict):
            if isinstance(saved_value, dict):
                merge_known_keys(default_value, saved_value)
            continue
        default[key] = saved_value


def migrate_saved_data(saved):
    """Convert the single-servant, three-part v1 save into schema v2."""

    if not isinstance(saved, dict):
        return saved

    if "skeletons" not in saved:
        old_servant = saved.get("servant", {})
        saved["skeletons"] = []
        if isinstance(old_servant, dict) and bool(old_servant.get("active")):
            saved["skeletons"].append({
                "id": 1,
                "remaining_seconds": old_servant.get("remaining_seconds", 0),
                "job": old_servant.get("job", "mana"),
            })
        saved["next_skeleton_id"] = 2 if saved["skeletons"] else 1

    assembly = saved.get("assembly")
    if isinstance(assembly, dict):
        old_placed = assembly.get("placed")
        if isinstance(old_placed, dict) and any(
            key in old_placed for key in ("skull", "ribcage", "limbs")
        ):
            frame_ready = bool(assembly.get("frame_ready"))
            limbs = bool(old_placed.get("limbs", False))
            assembly["placed"] = {
                "head": frame_ready or bool(old_placed.get("skull", False)),
                "torso": frame_ready or bool(old_placed.get("ribcage", False)),
                "left_arm": frame_ready or limbs,
                "right_arm": frame_ready or limbs,
                "left_leg": frame_ready or limbs,
                "right_leg": frame_ready or limbs,
                "soulgem": frame_ready,
            }
            assembly["selected_part"] = None

    saved["save_schema"] = SAVE_SCHEMA_VERSION
    return saved


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


def normalize_state(game):
    game["save_schema"] = SAVE_SCHEMA_VERSION

    # Permit legitimate overflow from returned bones while still bounding
    # manually edited saves.
    for key, definition in RESOURCE_DEFS.items():
        maximum = float(definition["base_capacity"]) * 1000
        game["resources"][key] = _number(game["resources"].get(key), maximum=maximum)

    for key in game["unlocks"]:
        game["unlocks"][key] = bool(game["unlocks"].get(key, False))

    game["grave"]["progress"] = _number(
        game["grave"].get("progress"),
        maximum=BASE_GRAVE_PROGRESS_REQUIRED - 0.000001,
    )
    game["soul_trap_crafted"] = bool(game["soul_trap_crafted"])

    assembly = game["assembly"]
    assembly["started"] = bool(assembly.get("started"))
    assembly["frame_ready"] = bool(assembly.get("frame_ready"))
    for key in PART_DEFS:
        assembly["placed"][key] = bool(assembly["placed"].get(key, False))

    selected = assembly.get("selected_part")
    if (
        not isinstance(selected, str)
        or selected not in PART_DEFS
        or assembly["placed"].get(selected, False)
    ):
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
        for raw in raw_skeletons[:50]:
            if not isinstance(raw, dict):
                continue
            skeleton_id = int(_number(raw.get("id"), default=len(used_ids) + 1, minimum=1))
            while skeleton_id in used_ids:
                skeleton_id += 1
            remaining = _number(raw.get("remaining_seconds"), maximum=3600)
            if remaining <= 0:
                continue
            job = raw.get("job")
            if job not in SKELETON_JOB_DEFS:
                job = "mana"
            used_ids.add(skeleton_id)
            normalized_skeletons.append({
                "id": skeleton_id,
                "remaining_seconds": remaining,
                "job": job,
            })
    game["skeletons"] = normalized_skeletons
    game["next_skeleton_id"] = max(
        int(_number(game.get("next_skeleton_id"), default=1, minimum=1)),
        max(used_ids, default=0) + 1,
    )

    for key in UPGRADE_DEFS:
        game["upgrades"][key] = bool(game["upgrades"].get(key, False))
    for key in RESEARCH_DEFS:
        game["research"][key] = bool(game["research"].get(key, False))

    stats = game["stats"]
    for key in ("active_time", "offline_time", "channel_seconds"):
        stats[key] = _number(stats.get(key))
    for key in (
        "dig_clicks",
        "graves_opened",
        "soul_traps_crafted",
        "assembly_mistakes",
        "skeletons_summoned",
        "servants_expired",
        "upgrades_bought",
        "research_completed",
    ):
        stats[key] = int(_number(stats.get(key)))
    for key in RESOURCE_DEFS:
        stats["total_generated"][key] = _number(
            stats["total_generated"].get(key)
        )

    if not isinstance(game["log"], list):
        game["log"] = []
    game["log"] = [str(item) for item in game["log"][-100:]]
    game["last_save"] = _number(game.get("last_save"))


def load_game():
    state.reset_runtime()
    raw = window.localStorage.getItem(SAVE_KEY)
    raw_text = "" if raw is None else str(raw).strip()
    if not raw_text or raw_text.lower() in ("none", "null", "undefined"):
        return False, 0.0, None

    try:
        saved_data = json.loads(raw_text)
        if not isinstance(saved_data, dict):
            raise ValueError("Save data is not an object.")

        migrate_saved_data(saved_data)
        fresh = state.new_game_state()
        merge_known_keys(fresh, saved_data)
        normalize_state(fresh)

        previous_save_time = fresh["last_save"]
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


def delete_save():
    window.localStorage.removeItem(SAVE_KEY)
