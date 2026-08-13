"""Reusable named-worker helpers.

The simulation stays in ``logic.py`` because grave-progress jobs call the main
grave activity. Naming, assignment, and rate resolution live here so adding a
new direct-resource job remains data-only.
"""

import re

from game import effects, requirements, state
from game.content import SKELETON_JOB_DEFS, SKELETON_NAME_POOL


def default_name(skeleton_id):
    index = max(0, int(skeleton_id) - 1)
    base = SKELETON_NAME_POOL[index % len(SKELETON_NAME_POOL)]
    cycle = index // len(SKELETON_NAME_POOL)
    return base if cycle == 0 else f"{base} {cycle + 1}"


def sanitize_name(value, skeleton_id):
    text = re.sub(r"[\x00-\x1f\x7f]", "", str(value or ""))
    text = " ".join(text.split())[:24].strip()
    return text or f"Skeleton #{int(skeleton_id)}"


def find(skeleton_id):
    for skeleton in state.game["skeletons"]:
        if int(skeleton["id"]) == int(skeleton_id):
            return skeleton
    return None


def rename(skeleton_id, name):
    skeleton = find(skeleton_id)
    if skeleton is None:
        return False
    clean = sanitize_name(name, skeleton_id)
    if skeleton.get("name") == clean:
        return True
    old_name = skeleton.get("name", f"Skeleton #{skeleton_id}")
    skeleton["name"] = clean
    state.add_log(
        f"{old_name} is now called {clean}.",
        category="skeleton",
        subject=str(skeleton_id),
    )
    return True


def job_visible(job_key):
    definition = SKELETON_JOB_DEFS[job_key]
    return requirements.requirements_met(definition.get("visible_when", []))


def available_jobs():
    return [key for key in SKELETON_JOB_DEFS if job_visible(key)]


def set_job(skeleton_id, job):
    if job not in SKELETON_JOB_DEFS or not job_visible(job):
        return False
    skeleton = find(skeleton_id)
    if skeleton is None:
        return False
    skeleton["job"] = job
    state.add_log(
        f"{skeleton['name']} assigned to {SKELETON_JOB_DEFS[job]['name']}.",
        category="skeleton",
        subject=str(skeleton_id),
    )
    return True


def job_rate(job):
    definition = SKELETON_JOB_DEFS.get(job)
    if definition is None:
        return 0.0
    return float(definition["base_rate"]) * effects.multiplier(
        "skeleton_work_multiplier", job=job
    )
