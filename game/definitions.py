"""Engine configuration and balance constants.

Add resources, upgrades, research, tabs, jobs, and assembly parts in
``content.py``. This file only contains shared tuning values.
"""

GAME_VERSION = "0.2.0"
SAVE_SCHEMA_VERSION = 2
SAVE_KEY = "the_first_rite_save_v1"

AUTOSAVE_SECONDS = 10.0
UI_REFRESH_SECONDS = 1 / 30
OFFLINE_PROGRESS_MAX_SECONDS = 8 * 60 * 60

# Opening loop. The first skeleton now takes several minutes instead of a few
# seconds, while early upgrades noticeably shorten later cycles.
BASE_CHANNEL_MANA_PER_SECOND = 2.0
BASE_GRAVE_PROGRESS_REQUIRED = 15.0
BASE_DIG_PROGRESS_PER_CLICK = 1.0
BASE_BONES_PER_GRAVE = 4.0
KNOWLEDGE_PER_GRAVE = 0.4

GRAVEYARD_UNLOCK_MANA = 8.0
SOUL_TRAP_COST = {"mana": 20.0, "bones": 4.0}
BASE_ASSEMBLY_COST = {"bones": 14.0}
SUMMON_COST = {"mana": 35.0, "souls": 1.0}

BASE_SKELETON_LIMIT = 1
BASE_SKELETON_DURATION_SECONDS = 150.0
BASE_SKELETON_MANA_PER_SECOND = 0.65
BASE_SKELETON_DIG_PROGRESS_PER_SECOND = 0.15
BASE_SKELETON_RETURNED_BONES = 8.0
KNOWLEDGE_PER_EXPIRED_SKELETON = 2.5
