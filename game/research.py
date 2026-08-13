"""Timed, queued research with continuous Knowledge consumption."""

from game import economy, effects, requirements, state
from game.content import RESEARCH_DEFS
from game.definitions import BASE_RESEARCH_QUEUE_LIMIT


def completed(research_key):
    return bool(state.game["research"]["completed"].get(research_key, False))


def unlocked(research_key):
    definition = RESEARCH_DEFS[research_key]
    return all(completed(key) for key in definition.get("prerequisites", [])) and requirements.requirements_met(
        definition.get("unlock", [])
    )


def queue_limit():
    return BASE_RESEARCH_QUEUE_LIMIT + int(effects.additive("research_queue_add"))


def speed():
    return effects.multiplier("research_speed_multiplier")


def planned_keys():
    research_state = state.game["research"]
    active = research_state.get("active")
    keys = [active["key"]] if active else []
    return keys + list(research_state.get("queue", []))


def can_plan(research_key):
    return (
        research_key in RESEARCH_DEFS
        and not completed(research_key)
        and research_key not in planned_keys()
        and unlocked(research_key)
        and len(planned_keys()) < queue_limit()
        and economy.can_afford(RESEARCH_DEFS[research_key].get("start_cost", {}))
    )


def plan(research_key):
    """Start now when the lectern is idle, otherwise append to its queue."""

    if not can_plan(research_key):
        return False
    definition = RESEARCH_DEFS[research_key]
    if not economy.spend(definition.get("start_cost", {})):
        return False

    research_state = state.game["research"]
    if research_state.get("active") is None:
        research_state["active"] = {
            "key": research_key,
            "progress": 0.0,
            "knowledge_spent": 0.0,
            "paused": False,
        }
        verb = "started"
    else:
        research_state["queue"].append(research_key)
        verb = "queued"
    state.add_log(
        f"Research {verb}: {definition['name']}.",
        category="research",
        subject=research_key,
    )
    return True


def cancel_active():
    active = state.game["research"].get("active")
    if active is None:
        return False
    name = RESEARCH_DEFS[active["key"]]["name"]
    state.game["research"]["active"] = None
    _promote_next()
    state.add_log(
        f"Research cancelled: {name}. Spent Knowledge was not recovered.",
        category="research",
        tone="warning",
    )
    return True


def remove_queued(research_key):
    queue = state.game["research"].get("queue", [])
    if research_key not in queue:
        return False
    queue.remove(research_key)
    state.add_log(
        f"Removed {RESEARCH_DEFS[research_key]['name']} from the research queue.",
        category="research",
    )
    return True


def _promote_next():
    research_state = state.game["research"]
    if research_state.get("active") is not None or not research_state["queue"]:
        return
    key = research_state["queue"].pop(0)
    research_state["active"] = {
        "key": key,
        "progress": 0.0,
        "knowledge_spent": 0.0,
        "paused": False,
    }
    state.add_log(
        f"Research started: {RESEARCH_DEFS[key]['name']}.",
        category="research",
        subject=key,
    )


def knowledge_drain_rate():
    active = state.game["research"].get("active")
    if active is None:
        return 0.0
    definition = RESEARCH_DEFS[active["key"]]
    return (
        float(definition["knowledge_cost"])
        / float(definition["duration"])
        * speed()
    )


def _complete_active(active, definition):
    """Commit completion in one place for live and loaded-at-100% projects."""

    key = active["key"]
    state.game["research"]["completed"][key] = True
    state.game["research"]["active"] = None
    state.game["stats"]["research_completed"] += 1
    state.add_log(
        f"Research completed: {definition['name']}.",
        category="research",
        tone="success",
        subject=key,
    )


def advance(seconds):
    """Advance projects exactly to completion or resource exhaustion."""

    wall_seconds = max(0.0, float(seconds))
    while wall_seconds > 1e-9:
        _promote_next()
        active = state.game["research"].get("active")
        if active is None:
            return

        definition = RESEARCH_DEFS[active["key"]]
        project_speed = speed()
        remaining_work = max(0.0, float(definition["duration"]) - float(active["progress"]))

        # A save can legitimately capture a project at its exact duration.
        # Complete it before the resource-exhaustion branch so it cannot become
        # a permanently paused 100% project after loading.
        if remaining_work <= 1e-9:
            _complete_active(active, definition)
            continue

        knowledge_per_work = float(definition["knowledge_cost"]) / float(definition["duration"])
        possible_work = wall_seconds * project_speed
        if knowledge_per_work > 0:
            affordable_work = float(state.game["resources"]["knowledge"]) / knowledge_per_work
            possible_work = min(possible_work, affordable_work)
        work = min(remaining_work, possible_work)

        if work <= 1e-9:
            active["paused"] = True
            return

        spent = knowledge_per_work * work
        economy.spend_partial("knowledge", spent)
        active["knowledge_spent"] += spent
        active["progress"] += work
        active["paused"] = False
        wall_seconds -= work / project_speed

        if active["progress"] + 1e-7 < float(definition["duration"]):
            if wall_seconds > 1e-9 and state.game["resources"]["knowledge"] <= 1e-9:
                active["paused"] = True
            return

        _complete_active(active, definition)
