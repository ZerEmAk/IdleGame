"""Game rules and generic progression effects.

The UI never implements costs or production. New content definitions can reuse
the effect types below without adding new DOM code.
"""

from game import state
from game.content import (
    PART_DEFS,
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
    BASE_SKELETON_DIG_PROGRESS_PER_SECOND,
    BASE_SKELETON_DURATION_SECONDS,
    BASE_SKELETON_LIMIT,
    BASE_SKELETON_MANA_PER_SECOND,
    BASE_SKELETON_RETURNED_BONES,
    GRAVEYARD_UNLOCK_MANA,
    KNOWLEDGE_PER_EXPIRED_SKELETON,
    KNOWLEDGE_PER_GRAVE,
    SOUL_TRAP_COST,
    SUMMON_COST,
)


# ====================================================================
# GENERIC EFFECT ENGINE
# ====================================================================


def purchased_effects(effect_type):
    for key, definition in UPGRADE_DEFS.items():
        if state.game["upgrades"].get(key, False):
            for effect in definition.get("effects", []):
                if effect.get("type") == effect_type:
                    yield effect

    for key, definition in RESEARCH_DEFS.items():
        if state.game["research"].get(key, False):
            for effect in definition.get("effects", []):
                if effect.get("type") == effect_type:
                    yield effect


def effect_multiplier(effect_type, job=None):
    multiplier = 1.0
    for effect in purchased_effects(effect_type):
        effect_job = effect.get("job")
        if effect_job is not None and effect_job != job:
            continue
        multiplier *= float(effect.get("multiplier", 1.0))
    return multiplier


def effect_additive(effect_type, job=None):
    total = 0.0
    for effect in purchased_effects(effect_type):
        effect_job = effect.get("job")
        if effect_job is not None and effect_job != job:
            continue
        total += float(effect.get("amount", 0.0))
    return total


# ====================================================================
# DERIVED BALANCE
# ====================================================================


def resource_capacity(resource_key):
    capacity = float(RESOURCE_DEFS[resource_key]["base_capacity"])
    for effect in purchased_effects("resource_capacity_multiplier"):
        if resource_key in effect.get("resources", []):
            capacity *= float(effect.get("multiplier", 1.0))
    for effect in purchased_effects("resource_capacity_add"):
        if resource_key == effect.get("resource"):
            capacity += float(effect.get("amount", 0.0))
    return capacity


def channel_rate():
    return BASE_CHANNEL_MANA_PER_SECOND * effect_multiplier("channel_multiplier")


def dig_click_power():
    return BASE_DIG_PROGRESS_PER_CLICK + effect_additive("dig_click_add")


def bones_per_grave():
    return BASE_BONES_PER_GRAVE * effect_multiplier("bones_per_grave_multiplier")


def grave_progress_required():
    return BASE_GRAVE_PROGRESS_REQUIRED


def assembly_cost():
    multiplier = effect_multiplier("assembly_cost_multiplier")
    return {
        key: max(1.0, round(float(amount) * multiplier))
        for key, amount in BASE_ASSEMBLY_COST.items()
    }


def skeleton_limit():
    return BASE_SKELETON_LIMIT + int(effect_additive("skeleton_limit_add"))


def skeleton_duration():
    return (
        BASE_SKELETON_DURATION_SECONDS
        * effect_multiplier("skeleton_duration_multiplier")
    )


def skeleton_returned_bones():
    return BASE_SKELETON_RETURNED_BONES + effect_additive("skeleton_return_add")


def skeleton_job_rate(job):
    multiplier = effect_multiplier("skeleton_work_multiplier", job=job)
    if job == "mana":
        return BASE_SKELETON_MANA_PER_SECOND * multiplier
    if job == "graves":
        return BASE_SKELETON_DIG_PROGRESS_PER_SECOND * multiplier
    return 0.0


# ====================================================================
# RESOURCES AND COSTS
# ====================================================================


def add_resource(resource_key, amount, count_generated=True):
    current = float(state.game["resources"][resource_key])
    capacity = resource_capacity(resource_key)
    if current >= capacity:
        return 0.0

    new_amount = min(capacity, current + max(0.0, float(amount)))
    gained = max(0.0, new_amount - current)
    state.game["resources"][resource_key] = new_amount

    if count_generated:
        state.game["stats"]["total_generated"][resource_key] += gained
    return gained


def return_resource(resource_key, amount):
    amount = max(0.0, float(amount))
    state.game["resources"][resource_key] += amount
    return amount


def can_afford(costs):
    return all(
        float(state.game["resources"].get(key, 0.0)) >= float(amount)
        for key, amount in costs.items()
    )


def spend_resources(costs):
    if not can_afford(costs):
        return False
    for key, amount in costs.items():
        state.game["resources"][key] -= float(amount)
    return True


def production_rates():
    rates = {key: 0.0 for key in RESOURCE_DEFS}
    if state.runtime["channeling"]:
        rates["mana"] += channel_rate()

    for skeleton in state.game["skeletons"]:
        job = skeleton["job"]
        rate = skeleton_job_rate(job)
        if job == "mana":
            rates["mana"] += rate
        elif job == "graves":
            fraction = rate / grave_progress_required()
            rates["bones"] += fraction * bones_per_grave()
            rates["knowledge"] += fraction * KNOWLEDGE_PER_GRAVE
    return rates


# ====================================================================
# CONTENT REQUIREMENTS AND PURCHASES
# ====================================================================


def requirement_met(requirement):
    kind = requirement.get("type")
    target = float(requirement.get("value", 0.0))

    if kind == "total_resource":
        key = requirement.get("resource")
        return state.game["stats"]["total_generated"].get(key, 0.0) >= target
    if kind == "stat":
        return state.game["stats"].get(requirement.get("key"), 0) >= target
    if kind == "flag":
        return bool(state.game.get(requirement.get("key"), False))
    if kind == "research":
        return bool(state.game["research"].get(requirement.get("key"), False))
    return True


def requirements_met(requirements):
    return all(requirement_met(item) for item in requirements)


def upgrade_unlocked(upgrade_key):
    return requirements_met(UPGRADE_DEFS[upgrade_key].get("unlock", []))


def research_unlocked(research_key):
    definition = RESEARCH_DEFS[research_key]
    return all(
        state.game["research"].get(key, False)
        for key in definition.get("prerequisites", [])
    )


def buy_upgrade(upgrade_key):
    if state.game["upgrades"].get(upgrade_key, False):
        return False
    definition = UPGRADE_DEFS[upgrade_key]
    if not upgrade_unlocked(upgrade_key) or not spend_resources(definition["cost"]):
        return False

    state.game["upgrades"][upgrade_key] = True
    state.game["stats"]["upgrades_bought"] += 1
    state.add_log(f"Upgrade purchased: {definition['name']}.")
    return True


def buy_research(research_key):
    if state.game["research"].get(research_key, False):
        return False
    definition = RESEARCH_DEFS[research_key]
    if not research_unlocked(research_key) or not spend_resources(definition["cost"]):
        return False

    state.game["research"][research_key] = True
    state.game["stats"]["research_completed"] += 1
    state.add_log(f"Research completed: {definition['name']}.")
    return True


# ====================================================================
# OPENING PROGRESSION
# ====================================================================


def update_unlocks():
    unlocks = state.game["unlocks"]
    stats = state.game["stats"]

    if (
        not unlocks["graveyard"]
        and stats["total_generated"]["mana"] >= GRAVEYARD_UNLOCK_MANA
    ):
        unlocks["graveyard"] = True
        state.add_log("The graveyard is now available.")

    if not unlocks["soul_trap"] and stats["graves_opened"] >= 1:
        unlocks["soul_trap"] = True
        state.add_log("Soul Cage crafting is now available.")

    if not unlocks["assembly"] and state.game["soul_trap_crafted"]:
        unlocks["assembly"] = True
        state.add_log("Skeleton assembly is now available.")

    if not unlocks["summoning"] and state.game["assembly"]["frame_ready"]:
        unlocks["summoning"] = True
        state.add_log("Skeleton summoning is now available.")


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

    bones_gained = add_resource("bones", bones_per_grave() * completed)
    knowledge_gained = add_resource("knowledge", KNOWLEDGE_PER_GRAVE * completed)
    souls_gained = 0.0
    if state.game["soul_trap_crafted"]:
        souls_gained = add_resource("souls", completed)

    state.game["stats"]["graves_opened"] += completed
    update_unlocks()

    subject = "Skeletons" if source == "skeleton" else "You"
    message = (
        f"{subject} opened {completed} grave"
        f"{'s' if completed != 1 else ''}: +{bones_gained:g} Bones, "
        f"+{knowledge_gained:g} Knowledge"
    )
    if souls_gained:
        message += f", +{souls_gained:g} Bound Soul"
    state.add_log(message + ".")
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
    if not spend_resources(SOUL_TRAP_COST):
        return False

    state.game["soul_trap_crafted"] = True
    state.game["stats"]["soul_traps_crafted"] += 1
    state.add_log("Soul Cage crafted.")
    update_unlocks()
    return True


# ====================================================================
# SEVEN-PART ASSEMBLY
# ====================================================================


def start_assembly():
    assembly = state.game["assembly"]
    if not state.game["unlocks"]["assembly"]:
        return False
    if assembly["started"] or assembly["frame_ready"]:
        return False
    if not spend_resources(assembly_cost()):
        return False

    assembly["started"] = True
    assembly["selected_part"] = None
    assembly["placed"] = {key: False for key in PART_DEFS}
    state.runtime["assembly_feedback"] = "Drag each part onto its matching slot."
    state.add_log("Bones prepared for assembly.")
    return True


def select_assembly_part(part_key):
    assembly = state.game["assembly"]
    if not assembly["started"] or part_key not in PART_DEFS:
        return False
    if assembly["placed"].get(part_key, False):
        return False

    assembly["selected_part"] = part_key
    state.runtime["assembly_feedback"] = (
        f"{PART_DEFS[part_key]['name']} selected. Choose a matching slot."
    )
    return True


def place_assembly_part(part_key, slot_key):
    assembly = state.game["assembly"]
    if not assembly["started"] or part_key not in PART_DEFS or slot_key not in SLOT_DEFS:
        return False
    if assembly["placed"].get(part_key, False):
        return False

    if SLOT_DEFS[slot_key]["accepts"] != part_key:
        state.game["stats"]["assembly_mistakes"] += 1
        state.runtime["assembly_feedback"] = (
            f"{PART_DEFS[part_key]['name']} does not fit the "
            f"{SLOT_DEFS[slot_key]['name'].lower()} slot."
        )
        return False

    assembly["placed"][part_key] = True
    assembly["selected_part"] = None
    state.runtime["dragged_part"] = None
    state.runtime["assembly_feedback"] = f"{PART_DEFS[part_key]['name']} placed."

    if all(assembly["placed"].values()):
        assembly["started"] = False
        assembly["frame_ready"] = True
        state.runtime["assembly_feedback"] = "The seven-part vessel is complete."
        state.add_log("Skeleton frame completed.")
        update_unlocks()
    return True


def place_selected_part(slot_key):
    part_key = state.game["assembly"].get("selected_part")
    if part_key is None:
        state.runtime["assembly_feedback"] = "Select or drag a part first."
        return False
    return place_assembly_part(part_key, slot_key)


# ====================================================================
# MULTIPLE SKELETONS
# ====================================================================


def summon_skeleton():
    assembly = state.game["assembly"]
    if not assembly["frame_ready"] or not state.game["unlocks"]["summoning"]:
        return False
    if len(state.game["skeletons"]) >= skeleton_limit():
        return False
    if not spend_resources(SUMMON_COST):
        return False

    skeleton_id = int(state.game["next_skeleton_id"])
    state.game["next_skeleton_id"] = skeleton_id + 1
    state.game["skeletons"].append({
        "id": skeleton_id,
        "remaining_seconds": skeleton_duration(),
        "job": "mana",
    })

    assembly["frame_ready"] = False
    assembly["started"] = False
    assembly["selected_part"] = None
    assembly["placed"] = {key: False for key in PART_DEFS}
    state.game["stats"]["skeletons_summoned"] += 1
    state.runtime["assembly_feedback"] = "Prepare another set of bones when ready."
    state.add_log(f"Skeleton #{skeleton_id} summoned.")
    return True


def find_skeleton(skeleton_id):
    for skeleton in state.game["skeletons"]:
        if int(skeleton["id"]) == int(skeleton_id):
            return skeleton
    return None


def set_skeleton_job(skeleton_id, job):
    if job not in SKELETON_JOB_DEFS:
        return False
    skeleton = find_skeleton(skeleton_id)
    if skeleton is None:
        return False
    skeleton["job"] = job
    state.add_log(f"Skeleton #{skeleton_id} assigned to {SKELETON_JOB_DEFS[job]['name']}.")
    return True


def expire_skeleton(skeleton_id):
    skeleton = find_skeleton(skeleton_id)
    if skeleton is None:
        return False

    state.game["skeletons"].remove(skeleton)
    returned = skeleton_returned_bones()
    return_resource("bones", returned)
    gained_knowledge = add_resource("knowledge", KNOWLEDGE_PER_EXPIRED_SKELETON)
    state.game["stats"]["servants_expired"] += 1
    state.add_log(
        f"Skeleton #{skeleton_id} expired: +{returned:g} Bones, "
        f"+{gained_knowledge:g} Knowledge."
    )
    return True


# ====================================================================
# ELAPSED TIME
# ====================================================================


def advance_game(seconds, offline=False):
    seconds = max(0.0, float(seconds))

    if not offline and state.runtime["channeling"]:
        add_resource("mana", channel_rate() * seconds)
        state.game["stats"]["channel_seconds"] += seconds

    expired_ids = []
    for skeleton in list(state.game["skeletons"]):
        active_seconds = min(seconds, float(skeleton["remaining_seconds"]))
        job = skeleton["job"]
        rate = skeleton_job_rate(job)

        if job == "mana":
            add_resource("mana", rate * active_seconds)
        elif job == "graves":
            advance_grave(rate * active_seconds, source="skeleton")

        skeleton["remaining_seconds"] = max(
            0.0,
            float(skeleton["remaining_seconds"]) - active_seconds,
        )
        if skeleton["remaining_seconds"] <= 0:
            expired_ids.append(skeleton["id"])

    for skeleton_id in expired_ids:
        expire_skeleton(skeleton_id)

    stats_key = "offline_time" if offline else "active_time"
    state.game["stats"][stats_key] += seconds
    update_unlocks()
