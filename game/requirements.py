"""One requirement language shared by visibility, upgrades, and activities."""

from game import state


def research_completed(game, key):
    research = game.get("research", {})
    completed = research.get("completed", {}) if isinstance(research, dict) else {}
    return bool(completed.get(key, False))


def requirement_met(requirement, game=None):
    """Evaluate one declarative requirement.

    Unknown requirement types fail closed. Startup validation reports them
    during development, and a typo can never silently unlock content in play.
    """

    game = game or state.game
    kind = requirement.get("type")
    target = float(requirement.get("value", 0.0))

    if kind == "total_resource":
        key = requirement.get("resource")
        return float(game["stats"]["total_generated"].get(key, 0.0)) >= target
    if kind == "resource":
        key = requirement.get("resource")
        return float(game["resources"].get(key, 0.0)) >= target
    if kind == "stat":
        return float(game["stats"].get(requirement.get("key"), 0.0)) >= target
    if kind == "flag":
        return bool(game.get(requirement.get("key"), False))
    if kind == "research":
        return research_completed(game, requirement.get("key"))
    return False


def requirements_met(requirements, game=None):
    return all(requirement_met(item, game=game) for item in requirements)
