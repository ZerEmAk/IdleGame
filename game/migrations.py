"""Ordered, pure save migrations.

Never edit an old migration after release. Add the next ``vN_to_vN+1``
function and register it in ``MIGRATIONS`` so every historical save follows
the same explicit path.
"""

import time

from game.content import PART_DEFS, SKELETON_NAME_POOL


def v1_to_v2(saved):
    old_servant = saved.get("servant", {})
    saved.setdefault("skeletons", [])
    if not saved["skeletons"] and isinstance(old_servant, dict) and old_servant.get("active"):
        saved["skeletons"].append({
            "id": 1,
            "remaining_seconds": old_servant.get("remaining_seconds", 0),
            "job": old_servant.get("job", "mana"),
        })
    saved.setdefault("next_skeleton_id", 2 if saved["skeletons"] else 1)

    assembly = saved.get("assembly")
    if isinstance(assembly, dict):
        old_placed = assembly.get("placed")
        if isinstance(old_placed, dict) and any(key in old_placed for key in ("skull", "ribcage", "limbs")):
            ready = bool(assembly.get("frame_ready"))
            limbs = bool(old_placed.get("limbs"))
            assembly["placed"] = {
                "head": ready or bool(old_placed.get("skull")),
                "torso": ready or bool(old_placed.get("ribcage")),
                "left_arm": ready or limbs,
                "right_arm": ready or limbs,
                "left_leg": ready or limbs,
                "right_leg": ready or limbs,
                "soulgem": ready,
            }
            assembly["selected_part"] = None
    saved["save_schema"] = 2
    return saved


def v2_to_v3(saved):
    old_research = saved.get("research", {})
    if isinstance(old_research, dict) and "completed" not in old_research:
        saved["research"] = {
            "completed": {key: bool(value) for key, value in old_research.items()},
            "active": None,
            "queue": [],
        }

    for index, skeleton in enumerate(saved.get("skeletons", [])):
        if not isinstance(skeleton, dict):
            continue
        skeleton_id = int(skeleton.get("id", index + 1))
        skeleton.setdefault("name", SKELETON_NAME_POOL[(skeleton_id - 1) % len(SKELETON_NAME_POOL)])
        skeleton.setdefault("maximum_seconds", skeleton.get("remaining_seconds", 0))

    migrated_log = []
    next_id = 1
    raw_log = saved.get("log", [])
    if not isinstance(raw_log, list):
        raw_log = []
    for entry in raw_log:
        if isinstance(entry, dict):
            migrated_log.append(entry)
            next_id = max(next_id, int(entry.get("id", 0)) + 1)
        else:
            migrated_log.append({
                "id": next_id,
                "timestamp": time.time(),
                "game_time": 0.0,
                "category": "system",
                "tone": "info",
                "message": str(entry),
                "subject": None,
            })
            next_id += 1
    saved["log"] = migrated_log
    saved["next_log_id"] = next_id
    saved["save_schema"] = 3
    return saved


def v3_to_v4(saved):
    """Persist the shuffled assembly tray without disturbing active frames."""

    assembly = saved.get("assembly")
    if isinstance(assembly, dict):
        assembly.setdefault("part_order", list(PART_DEFS))
    saved["save_schema"] = 4
    return saved


MIGRATIONS = {
    1: v1_to_v2,
    2: v2_to_v3,
    3: v3_to_v4,
}


def migrate(saved, target_version):
    version = int(saved.get("save_schema", 1))
    if version > target_version:
        raise ValueError(
            f"Save schema {version} is newer than supported schema {target_version}."
        )
    while version < target_version:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No migration exists for save schema {version}.")
        saved = migration(saved)
        version = int(saved.get("save_schema", version + 1))
    return saved
