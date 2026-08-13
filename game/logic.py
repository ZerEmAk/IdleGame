"""Public gameplay façade.

Browser code calls this module instead of mutating state directly. Reusable
economy, requirement, modifier, research, activity, and worker behavior lives
in focused modules; this façade coordinates cross-system rules such as grave
rewards and elapsed-time ordering.
"""

import random

from game import activities, economy, effects, requirements, research, state, workers
from game.content import (
    ACTIVITY_DEFS,
    PART_DEFS,
    RECIPE_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
    SKELETON_JOB_DEFS,
    SLOT_DEFS,
    UPGRADE_DEFS,
)
from game.definitions import (
    BASE_ASSEMBLY_COST,
    BASE_BONES_PER_GRAVE,
    BASE_CHANNEL_MANA_PER_SECOND,
    BASE_DIG_PROGRESS_PER_CLICK,
    BASE_GRAVE_PROGRESS_REQUIRED,
    BASE_SKELETON_DURATION_SECONDS,
    BASE_SKELETON_LIMIT,
    BASE_SKELETON_RETURNED_BONES,
    GRAVEYARD_UNLOCK_MANA,
    KNOWLEDGE_PER_EXPIRED_SKELETON,
    KNOWLEDGE_PER_GRAVE,
    MAX_SIMULATION_STEP_SECONDS,
    SOUL_TRAP_COST,
    SUMMON_COST,
)


# --------------------------------------------------------------------
# Compatibility aliases and derived balance
# --------------------------------------------------------------------


def purchased_effects(effect_type):
    return effects.purchased_effects(effect_type)


def effect_multiplier(effect_type, job=None):
    filters = {} if job is None else {"job": job}
    return effects.multiplier(effect_type, **filters)


def effect_additive(effect_type, job=None):
    filters = {} if job is None else {"job": job}
    return effects.additive(effect_type, **filters)


def resource_capacity(resource_key):
    return economy.capacity(resource_key)


def channel_rate():
    return BASE_CHANNEL_MANA_PER_SECOND * effects.multiplier("channel_multiplier")


def dig_click_power():
    return BASE_DIG_PROGRESS_PER_CLICK + effects.additive("dig_click_add")


def bones_per_grave():
    return BASE_BONES_PER_GRAVE * effects.multiplier("bones_per_grave_multiplier")


def knowledge_per_grave():
    return KNOWLEDGE_PER_GRAVE * effects.multiplier("knowledge_per_grave_multiplier")


def grave_dust_per_grave():
    return 0.5


def grave_progress_required():
    return BASE_GRAVE_PROGRESS_REQUIRED


def assembly_cost():
    multiplier = effects.multiplier("assembly_cost_multiplier")
    return {
        key: max(1.0, round(float(amount) * multiplier))
        for key, amount in BASE_ASSEMBLY_COST.items()
    }


def skeleton_limit():
    return BASE_SKELETON_LIMIT + int(effects.additive("skeleton_limit_add"))


def skeleton_duration():
    return BASE_SKELETON_DURATION_SECONDS * effects.multiplier("skeleton_duration_multiplier")


def skeleton_returned_bones():
    return BASE_SKELETON_RETURNED_BONES + effects.additive("skeleton_return_add")


def skeleton_job_rate(job):
    return workers.job_rate(job)


# --------------------------------------------------------------------
# Resources, visibility, requirements, and purchases
# --------------------------------------------------------------------


def add_resource(resource_key, amount, count_generated=True):
    return economy.add(resource_key, amount, count_generated=count_generated)


def return_resource(resource_key, amount):
    return economy.add(resource_key, amount, count_generated=False)


def can_afford(costs):
    return economy.can_afford(costs)


def spend_resources(costs):
    return economy.spend(costs)


def requirement_met(requirement):
    return requirements.requirement_met(requirement)


def requirements_met(items):
    return requirements.requirements_met(items)


def content_visible(definition):
    return requirements.requirements_met(definition.get("visible_when", []))


def upgrade_unlocked(upgrade_key):
    return requirements.requirements_met(UPGRADE_DEFS[upgrade_key].get("unlock", []))


def research_unlocked(research_key):
    return research.unlocked(research_key)


def buy_upgrade(upgrade_key):
    if upgrade_key not in UPGRADE_DEFS or state.game["upgrades"].get(upgrade_key, False):
        return False
    definition = UPGRADE_DEFS[upgrade_key]
    if not upgrade_unlocked(upgrade_key) or not economy.spend(definition["cost"]):
        return False
    state.game["upgrades"][upgrade_key] = True
    state.game["stats"]["upgrades_bought"] += 1
    state.add_log(
        f"Upgrade purchased: {definition['name']}.",
        category="progression",
        tone="success",
        subject=upgrade_key,
    )
    return True


def buy_research(research_key):
    """Compatibility name: research is now planned, timed, and continuously paid."""

    return research.plan(research_key)


def cancel_research():
    return research.cancel_active()


def remove_queued_research(research_key):
    return research.remove_queued(research_key)


def research_queue_limit():
    return research.queue_limit()


def research_speed():
    return research.speed()


def research_drain_rate():
    return research.knowledge_drain_rate()


def production_rates():
    """Estimated net rates shown in the sidebar and overview."""

    rates = {key: 0.0 for key in RESOURCE_DEFS}
    if state.runtime["channeling"]:
        rates["mana"] += channel_rate()

    for skeleton in state.game["skeletons"]:
        job = skeleton["job"]
        definition = SKELETON_JOB_DEFS[job]
        rate = skeleton_job_rate(job)
        if definition["kind"] == "resource":
            rates[definition["resource"]] += rate
        elif definition["kind"] == "grave_progress":
            fraction = rate / grave_progress_required()
            rates["bones"] += fraction * bones_per_grave()
            rates["knowledge"] += fraction * knowledge_per_grave()
            rates["grave_dust"] += fraction * grave_dust_per_grave()
            if state.game["soul_trap_crafted"]:
                rates["souls"] += fraction
    rates["knowledge"] -= research.knowledge_drain_rate()
    return rates


# --------------------------------------------------------------------
# Opening progression and graves
# --------------------------------------------------------------------


def update_unlocks():
    unlocks = state.game["unlocks"]
    stats = state.game["stats"]
    if not unlocks["graveyard"] and stats["total_generated"]["mana"] >= GRAVEYARD_UNLOCK_MANA:
        unlocks["graveyard"] = True
        state.add_log("The graveyard is now available.", category="progression", tone="success")
    if not unlocks["soul_trap"] and stats["graves_opened"] >= 1:
        unlocks["soul_trap"] = True
        state.add_log("Soul Cage crafting is now available.", category="progression", tone="success")
    if not unlocks["assembly"] and state.game["soul_trap_crafted"]:
        unlocks["assembly"] = True
        state.add_log("Skeleton assembly is now available.", category="progression", tone="success")
    if not unlocks["summoning"] and state.game["assembly"]["frame_ready"]:
        unlocks["summoning"] = True
        state.add_log("Skeleton summoning is now available.", category="progression", tone="success")


def set_channeling(active):
    state.runtime["channeling"] = bool(active)


def advance_grave(progress, source="manual"):
    progress = max(0.0, float(progress))
    if progress <= 0:
        return 0
    required = grave_progress_required()
    total = float(state.game["grave"]["progress"]) + progress
    completed = int(total // required)
    state.game["grave"]["progress"] = total % required
    if completed <= 0:
        return 0

    bones = economy.add("bones", bones_per_grave() * completed)
    knowledge = economy.add("knowledge", knowledge_per_grave() * completed)
    dust = economy.add("grave_dust", grave_dust_per_grave() * completed)
    souls = economy.add("souls", completed) if state.game["soul_trap_crafted"] else 0.0
    state.game["stats"]["graves_opened"] += completed
    update_unlocks()

    subject = "Your skeletons" if source == "skeleton" else "You"
    message = (
        f"{subject} opened {completed} grave{'s' if completed != 1 else ''}: "
        f"+{bones:g} Bones, +{knowledge:g} Knowledge, +{dust:g} Grave Dust"
    )
    if souls:
        message += f", +{souls:g} Bound Soul{'s' if souls != 1 else ''}"
    state.add_log(message + ".", category="economy", tone="success")
    return completed


def dig_grave():
    if not state.game["unlocks"]["graveyard"]:
        return False
    state.game["stats"]["dig_clicks"] += 1
    advance_grave(dig_click_power())
    return True


def craft_soul_trap():
    if state.game["soul_trap_crafted"] or not state.game["unlocks"]["soul_trap"]:
        return False
    if not economy.spend(SOUL_TRAP_COST):
        return False
    state.game["soul_trap_crafted"] = True
    state.game["stats"]["soul_traps_crafted"] += 1
    state.add_log("Soul Cage crafted.", category="progression", tone="success")
    update_unlocks()
    return True


# --------------------------------------------------------------------
# Active-play activities and workshop recipes
# --------------------------------------------------------------------


def start_excavation():
    return activities.start_excavation()


def resolve_excavation(marker_override=None):
    return activities.resolve_excavation(advance_grave, marker_override)


def excavation_marker():
    return activities.excavation_marker()


def excavation_target_width():
    return activities.excavation_target_width()


def start_seance():
    return activities.start_seance()


def choose_seance_sigil(sigil_key):
    return activities.choose_seance_sigil(sigil_key)


def reset_seance():
    return activities.reset_seance()


def craft_recipe(recipe_key):
    return activities.craft_recipe(recipe_key)


def recipe_visible(recipe_key):
    return activities.recipe_visible(recipe_key)


# --------------------------------------------------------------------
# Seven-part assembly and named skeleton workers
# --------------------------------------------------------------------


def start_assembly():
    assembly = state.game["assembly"]
    if not state.game["unlocks"]["assembly"] or assembly["started"] or assembly["frame_ready"]:
        return False
    if not economy.spend(assembly_cost()):
        return False
    assembly["started"] = True
    assembly["selected_part"] = None
    assembly["placed"] = {key: False for key in PART_DEFS}
    order = list(PART_DEFS)
    # A deterministic per-frame seed avoids reordering on reload while still
    # making each new body a different visual sorting challenge.
    seed = (
        int(state.game["stats"]["skeletons_summoned"]) * 101
        + int(state.game["stats"]["assembly_mistakes"]) * 17
        + int(state.game["stats"]["graves_opened"]) * 7
    )
    random.Random(seed).shuffle(order)
    assembly["part_order"] = order
    state.runtime["assembly_feedback"] = "Drag each part onto its matching slot."
    state.add_log("Bones prepared for assembly.", category="activity")
    return True


def select_assembly_part(part_key):
    assembly = state.game["assembly"]
    if not assembly["started"] or part_key not in PART_DEFS or assembly["placed"].get(part_key, False):
        return False
    assembly["selected_part"] = part_key
    state.runtime["assembly_feedback"] = f"{PART_DEFS[part_key]['name']} selected. Choose a matching slot."
    return True


def place_assembly_part(part_key, slot_key):
    assembly = state.game["assembly"]
    if not assembly["started"] or part_key not in PART_DEFS or slot_key not in SLOT_DEFS:
        return False
    if assembly["placed"].get(part_key, False):
        return False
    if SLOT_DEFS[slot_key]["accepts"] != part_key:
        state.game["stats"]["assembly_mistakes"] += 1
        state.runtime["assembly_feedback"] = f"{PART_DEFS[part_key]['name']} does not fit the {SLOT_DEFS[slot_key]['name'].lower()} slot."
        return False
    assembly["placed"][part_key] = True
    assembly["selected_part"] = None
    state.runtime["dragged_part"] = None
    state.runtime["assembly_feedback"] = f"{PART_DEFS[part_key]['name']} placed."
    if all(assembly["placed"].values()):
        assembly["started"] = False
        assembly["frame_ready"] = True
        state.runtime["assembly_feedback"] = "The seven-part vessel is complete."
        state.add_log("Skeleton frame completed.", category="activity", tone="success")
        update_unlocks()
    return True


def place_selected_part(slot_key):
    part_key = state.game["assembly"].get("selected_part")
    if part_key is None:
        state.runtime["assembly_feedback"] = "Select or drag a part first."
        return False
    return place_assembly_part(part_key, slot_key)


def summon_skeleton():
    assembly = state.game["assembly"]
    if not assembly["frame_ready"] or not state.game["unlocks"]["summoning"]:
        return False
    if len(state.game["skeletons"]) >= skeleton_limit() or not economy.spend(SUMMON_COST):
        return False
    skeleton_id = int(state.game["next_skeleton_id"])
    state.game["next_skeleton_id"] = skeleton_id + 1
    duration = skeleton_duration()
    name = workers.default_name(skeleton_id)
    state.game["skeletons"].append({
        "id": skeleton_id,
        "name": name,
        "remaining_seconds": duration,
        "maximum_seconds": duration,
        "job": "mana",
    })
    assembly.update({
        "frame_ready": False,
        "started": False,
        "selected_part": None,
        "placed": {key: False for key in PART_DEFS},
        "part_order": list(PART_DEFS),
    })
    state.game["stats"]["skeletons_summoned"] += 1
    state.runtime["assembly_feedback"] = "Prepare another set of bones when ready."
    state.add_log(f"{name} was summoned.", category="skeleton", tone="success", subject=str(skeleton_id))
    return True


def find_skeleton(skeleton_id):
    return workers.find(skeleton_id)


def rename_skeleton(skeleton_id, name):
    return workers.rename(skeleton_id, name)


def set_skeleton_job(skeleton_id, job):
    return workers.set_job(skeleton_id, job)


def expire_skeleton(skeleton_id):
    skeleton = workers.find(skeleton_id)
    if skeleton is None:
        return False
    state.game["skeletons"].remove(skeleton)
    returned = economy.add("bones", skeleton_returned_bones(), count_generated=False)
    knowledge = economy.add("knowledge", KNOWLEDGE_PER_EXPIRED_SKELETON)
    state.game["stats"]["servants_expired"] += 1
    state.add_log(
        f"{skeleton['name']}'s binding expired: +{returned:g} Bones, +{knowledge:g} Knowledge.",
        category="skeleton",
        tone="warning",
        subject=str(skeleton_id),
    )
    return True


# --------------------------------------------------------------------
# Elapsed-time orchestration
# --------------------------------------------------------------------


def _advance_game_step(seconds, offline=False):
    """Advance systems in a stable order.

    1. Manual channeling (online only)
    2. Existing workers and expirations
    3. Timed research and its Knowledge drain
    4. Interactive activity clocks (online only)
    5. Unlock checks and time statistics
    """

    seconds = max(0.0, float(seconds))
    if not offline and state.runtime["channeling"]:
        economy.add("mana", channel_rate() * seconds)
        state.game["stats"]["channel_seconds"] += seconds

    expired_ids = []
    for skeleton in list(state.game["skeletons"]):
        active_seconds = min(seconds, float(skeleton["remaining_seconds"]))
        job = skeleton["job"]
        definition = SKELETON_JOB_DEFS[job]
        rate = skeleton_job_rate(job)
        if definition["kind"] == "resource":
            economy.add(definition["resource"], rate * active_seconds)
        elif definition["kind"] == "grave_progress":
            advance_grave(rate * active_seconds, source="skeleton")
        skeleton["remaining_seconds"] = max(0.0, float(skeleton["remaining_seconds"]) - active_seconds)
        if skeleton["remaining_seconds"] <= 0:
            expired_ids.append(skeleton["id"])
    for skeleton_id in expired_ids:
        expire_skeleton(skeleton_id)

    research.advance(seconds)
    if not offline:
        activities.advance(seconds)
        excavation = state.game["activities"]["excavation"]
        if (
            excavation["active"]
            and excavation["elapsed"] >= float(ACTIVITY_DEFS["excavation"]["duration"])
        ):
            resolve_excavation()

    stats_key = "offline_time" if offline else "active_time"
    state.game["stats"][stats_key] += seconds
    update_unlocks()


def advance_game(seconds, offline=False):
    """Advance elapsed time using bounded, deterministic integration steps.

    Browser ticks are already small, while offline loads can cover hours. A
    bounded step prevents a producer from filling a resource cap for the whole
    offline interval before a simultaneous consumer (notably research) runs.
    It also gives queued completions and worker expiry consistent boundaries.
    """

    remaining = max(0.0, float(seconds))
    while remaining > 1e-9:
        step = min(remaining, float(MAX_SIMULATION_STEP_SECONDS))
        _advance_game_step(step, offline=offline)
        remaining -= step
