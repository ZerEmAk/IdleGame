"""Short active-play systems and generic workshop recipes."""

import random

from game import economy, effects, requirements, state
from game.content import ACTIVITY_DEFS, RECIPE_DEFS, SEANCE_SIGIL_DEFS


def activity_visible(key):
    return requirements.requirements_met(ACTIVITY_DEFS[key].get("visible_when", []))


def recipe_visible(key):
    return requirements.requirements_met(RECIPE_DEFS[key].get("visible_when", []))


def craft_recipe(key):
    if key not in RECIPE_DEFS or not recipe_visible(key):
        return False
    definition = RECIPE_DEFS[key]
    if not economy.spend(definition["cost"]):
        return False
    produced = economy.grant(
        definition["produces"],
        multiplier=effects.multiplier("recipe_yield_multiplier"),
    )
    state.game["stats"]["recipes_crafted"] += 1
    summary = ", ".join(f"+{amount:g} {key}" for key, amount in produced.items())
    state.add_log(
        f"{definition['name']} completed: {summary}.",
        category="activity",
        tone="success",
        subject=key,
    )
    return True


def excavation_marker():
    excavation = state.game["activities"]["excavation"]
    phase = (float(excavation["elapsed"]) * 0.82) % 2.0
    return phase if phase <= 1.0 else 2.0 - phase


def excavation_target_width():
    return min(
        0.5,
        float(ACTIVITY_DEFS["excavation"]["target_width"])
        * effects.multiplier("excavation_target_multiplier"),
    )


def start_excavation():
    excavation = state.game["activities"]["excavation"]
    if not activity_visible("excavation") or excavation["active"]:
        return False
    seed = (
        int(state.game["stats"]["excavations_completed"]) * 977
        + int(state.game["stats"]["graves_opened"]) * 37
        + int(state.game["stats"]["dig_clicks"])
    )
    excavation.update({
        "active": True,
        "elapsed": 0.0,
        "target": random.Random(seed).uniform(0.22, 0.78),
        "stopped_marker": 0.0,
        "result": None,
    })
    return True


def resolve_excavation(grave_callback, marker_override=None):
    excavation = state.game["activities"]["excavation"]
    if not excavation["active"]:
        return False
    marker = (
        max(0.0, min(1.0, float(marker_override)))
        if marker_override is not None
        else excavation_marker()
    )
    distance = abs(marker - float(excavation["target"]))
    half_width = excavation_target_width() / 2.0
    if distance <= half_width * 0.38:
        result, layers, dust, relics = "Perfect", 5.0, 3.0, 1.0
        state.game["stats"]["perfect_excavations"] += 1
    elif distance <= half_width:
        result, layers, dust, relics = "Good", 3.0, 1.0, 0.0
    else:
        result, layers, dust, relics = "Glancing", 1.0, 0.0, 0.0
    reward_multiplier = effects.multiplier("excavation_reward_multiplier")
    economy.add("grave_dust", dust * reward_multiplier)
    economy.add("relics", relics * reward_multiplier)
    grave_callback(layers, source="excavation")
    state.game["stats"]["excavations_completed"] += 1
    state.game["stats"]["relics_found"] += int(relics * reward_multiplier)
    excavation.update({
        "active": False,
        "elapsed": 0.0,
        "stopped_marker": marker,
        "result": result.lower(),
    })
    state.add_log(
        f"{result} excavation: +{layers:g} grave layers, +{dust * reward_multiplier:g} Grave Dust"
        + (f", +{relics * reward_multiplier:g} Relic" if relics else "")
        + ".",
        category="activity",
        tone="success" if result != "Glancing" else "info",
        subject="excavation",
    )
    return True


def start_seance():
    seance = state.game["activities"]["seance"]
    definition = ACTIVITY_DEFS["seance"]
    if not activity_visible("seance") or seance["phase"] != "idle":
        return False
    if not economy.spend(definition["cost"]):
        return False
    keys = list(SEANCE_SIGIL_DEFS)
    seed = int(state.game["stats"]["seances_started"]) * 811 + int(state.game["stats"]["graves_opened"]) * 19
    rng = random.Random(seed)
    sequence = [rng.choice(keys) for _ in range(int(definition["sequence_length"]))]
    reveal_total = float(definition["reveal_seconds"]) * effects.multiplier(
        "seance_reveal_multiplier"
    )
    seance.update({
        "phase": "reveal",
        "sequence": sequence,
        "input_index": 0,
        "reveal_remaining": reveal_total,
        "reveal_total": reveal_total,
        "feedback": "Memorize the sigils.",
        "last_sigil": None,
        "feedback_tone": "reveal",
    })
    state.game["stats"]["seances_started"] += 1
    return True


def choose_seance_sigil(sigil_key):
    seance = state.game["activities"]["seance"]
    if seance["phase"] != "input" or sigil_key not in SEANCE_SIGIL_DEFS:
        return False
    expected = seance["sequence"][seance["input_index"]]
    if sigil_key != expected:
        economy.add("ectoplasm", 0.5)
        seance.update({
            "phase": "result",
            "feedback": "The pattern broke. A trace of Ectoplasm remains.",
            "last_sigil": sigil_key,
            "feedback_tone": "failure",
        })
        state.add_log(
            "The séance pattern broke; +0.5 Ectoplasm recovered.",
            category="activity",
            tone="warning",
            subject="seance",
        )
        return False
    seance["input_index"] += 1
    seance["last_sigil"] = sigil_key
    seance["feedback_tone"] = "correct"
    if seance["input_index"] < len(seance["sequence"]):
        seance["feedback"] = f"Correct. {len(seance['sequence']) - seance['input_index']} sigils remain."
        return True

    multiplier = effects.multiplier("seance_reward_multiplier")
    gained = economy.grant(ACTIVITY_DEFS["seance"]["reward"], multiplier=multiplier)
    state.game["stats"]["seances_completed"] += 1
    seance.update({
        "phase": "result",
        "feedback": "The spirit crossed the circle cleanly.",
        "feedback_tone": "success",
    })
    state.add_log(
        f"Séance completed: +{gained['souls']:g} Bound Souls, +{gained['ectoplasm']:g} Ectoplasm.",
        category="activity",
        tone="success",
        subject="seance",
    )
    return True


def reset_seance():
    seance = state.game["activities"]["seance"]
    if seance["phase"] != "result":
        return False
    seance.update({
        "phase": "idle",
        "sequence": [],
        "input_index": 0,
        "reveal_remaining": 0.0,
        "reveal_total": 0.0,
        "feedback": "Begin when the circle is quiet.",
        "last_sigil": None,
        "feedback_tone": "idle",
    })
    return True


def advance(seconds):
    seconds = max(0.0, float(seconds))
    excavation = state.game["activities"]["excavation"]
    if excavation["active"]:
        excavation["elapsed"] += seconds
        if excavation["elapsed"] >= float(ACTIVITY_DEFS["excavation"]["duration"]):
            # The UI resolves an expired attempt on its next update, preserving
            # the normal grave callback and reward event path.
            excavation["elapsed"] = float(ACTIVITY_DEFS["excavation"]["duration"])

    seance = state.game["activities"]["seance"]
    if seance["phase"] == "reveal":
        seance["reveal_remaining"] = max(0.0, float(seance["reveal_remaining"]) - seconds)
        if seance["reveal_remaining"] <= 0:
            seance["phase"] = "input"
            seance["feedback"] = "Repeat the pattern."
            seance["last_sigil"] = None
            seance["feedback_tone"] = "input"
