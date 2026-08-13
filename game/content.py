"""Stable import façade for all data-driven game content.

Existing code can keep importing ``game.content``. New definitions live in
``content_core.py`` or ``content_progression.py`` so neither file becomes an
unmanageable catalogue.
"""

from game.content_core import (  # noqa: F401
    ACTIVITY_DEFS,
    LOG_CATEGORY_DEFS,
    PART_DEFS,
    RECIPE_DEFS,
    RESOURCE_DEFS,
    SEANCE_SIGIL_DEFS,
    SKELETON_JOB_DEFS,
    SKELETON_NAME_POOL,
    SLOT_DEFS,
    TAB_DEFS,
)
from game.content_progression import RESEARCH_DEFS, UPGRADE_DEFS  # noqa: F401


__all__ = (
    "ACTIVITY_DEFS",
    "LOG_CATEGORY_DEFS",
    "PART_DEFS",
    "RECIPE_DEFS",
    "RESEARCH_DEFS",
    "RESOURCE_DEFS",
    "SEANCE_SIGIL_DEFS",
    "SKELETON_JOB_DEFS",
    "SKELETON_NAME_POOL",
    "SLOT_DEFS",
    "TAB_DEFS",
    "UPGRADE_DEFS",
)
