"""Core content registries for the idle-game framework.

This file contains definitions, never browser or simulation code. Add a new
resource, recipe, worker job, activity, log category, or assembly part here and
let the generic systems render and simulate it. ``docs/ADDING_CONTENT.md``
documents the supported fields and the few cases that need a new handler.
"""

from game.definitions import (
    BASE_SKELETON_DIG_PROGRESS_PER_SECOND,
    BASE_SKELETON_HAUNT_PER_SECOND,
    BASE_SKELETON_MANA_PER_SECOND,
    BASE_SKELETON_SCAVENGE_PER_SECOND,
    BASE_SKELETON_STUDY_PER_SECOND,
)


RESOURCE_DEFS = {
    "mana": {
        "name": "Mana",
        "description": "Power drawn through the veil.",
        "flavor": "Cold light pools between your fingers.",
        "base_capacity": 120.0,
        "symbol": "✦",
        "theme": "mana",
        "accent": "#9a87cf",
        "accent_rgb": "118, 101, 165",
        "visible_when": [],
    },
    "bones": {
        "name": "Bones",
        "description": "Material for skeletal vessels and workshop tools.",
        "flavor": "Cleaned, counted, and never quite still.",
        "base_capacity": 100.0,
        "symbol": "†",
        "theme": "bones",
        "accent": "#b2aa92",
        "accent_rgb": "178, 170, 146",
        "visible_when": [],
    },
    "souls": {
        "name": "Bound Souls",
        "description": "Spirits held inside the Soul Cage.",
        "flavor": "They remember having names.",
        "base_capacity": 1.0,
        "symbol": "◌",
        "theme": "souls",
        "accent": "#79a287",
        "accent_rgb": "93, 134, 107",
        "visible_when": [{"type": "flag", "key": "soul_trap_crafted"}],
    },
    "knowledge": {
        "name": "Knowledge",
        "description": "Understanding consumed gradually by active research.",
        "flavor": "Every answer leaves a more interesting question.",
        "base_capacity": 100.0,
        "symbol": "⌁",
        "theme": "knowledge",
        "accent": "#c0a66e",
        "accent_rgb": "132, 112, 71",
        "visible_when": [],
    },
    "grave_dust": {
        "name": "Grave Dust",
        "description": "Fine residue recovered by careful excavation.",
        "flavor": "The oldest earth clings to secrets.",
        "base_capacity": 60.0,
        "symbol": "∴",
        "theme": "dust",
        "accent": "#a99376",
        "accent_rgb": "119, 104, 86",
        "visible_when": [{"type": "stat", "key": "graves_opened", "value": 2}],
    },
    "ectoplasm": {
        "name": "Ectoplasm",
        "description": "Spirit matter condensed during successful séances.",
        "flavor": "A mist that recoils from warm hands.",
        "base_capacity": 40.0,
        "symbol": "≈",
        "theme": "ectoplasm",
        "accent": "#75c2b3",
        "accent_rgb": "71, 139, 129",
        "visible_when": [{"type": "flag", "key": "soul_trap_crafted"}],
    },
    "ritual_ink": {
        "name": "Ritual Ink",
        "description": "A durable medium for advanced circles and formulae.",
        "flavor": "It writes best when no one is looking.",
        "base_capacity": 12.0,
        "symbol": "¶",
        "theme": "ink",
        "accent": "#bd8bd5",
        "accent_rgb": "91, 65, 114",
        "visible_when": [{"type": "research", "key": "ritual_alchemy"}],
    },
    "relics": {
        "name": "Relics",
        "description": "Rare grave goods with lingering occult resonance.",
        "flavor": "Someone once loved this enough to be buried with it.",
        "base_capacity": 10.0,
        "symbol": "◇",
        "theme": "relics",
        "accent": "#e3bc63",
        "accent_rgb": "158, 125, 56",
        "visible_when": [{"type": "stat", "key": "perfect_excavations", "value": 1}],
    },
}


TAB_DEFS = (
    {"key": "overview", "label": "Overview", "symbol": "⌂", "scene": "Command Desk"},
    {"key": "rituals", "label": "Rituals", "symbol": "✦", "scene": "Ritual Chamber"},
    {"key": "workshop", "label": "Workshop", "symbol": "⚒", "scene": "Workshop"},
    {"key": "assembly", "label": "Assembly", "symbol": "⬡", "scene": "Ossuary Table"},
    {"key": "skeletons", "label": "Skeletons", "symbol": "☠", "scene": "Bound Roster"},
    {"key": "upgrades", "label": "Upgrades", "symbol": "◆", "scene": "Implements"},
    {"key": "research", "label": "Research", "symbol": "⌁", "scene": "Forbidden Studies"},
    {"key": "stats", "label": "Stats", "symbol": "▥", "scene": "Ledger"},
)


LOG_CATEGORY_DEFS = {
    "all": {"name": "All", "symbol": "•"},
    "progression": {"name": "Progress", "symbol": "✦"},
    "economy": {"name": "Resources", "symbol": "+"},
    "research": {"name": "Research", "symbol": "⌁"},
    "skeleton": {"name": "Skeletons", "symbol": "☠"},
    "activity": {"name": "Activities", "symbol": "◇"},
    "system": {"name": "System", "symbol": "○"},
}


# A job is either direct resource production or progress toward opening graves.
# Add job-specific effects with ``skeleton_work_multiplier`` and a matching job.
SKELETON_JOB_DEFS = {
    "mana": {
        "name": "Channel Mana",
        "short_name": "Channeling",
        "description": "Draws Mana continuously.",
        "flavor": "Its jaw chatters in time with the pulse.",
        "kind": "resource",
        "resource": "mana",
        "base_rate": BASE_SKELETON_MANA_PER_SECOND,
        "visible_when": [],
    },
    "graves": {
        "name": "Dig Graves",
        "short_name": "Digging",
        "description": "Excavates grave layers continuously.",
        "flavor": "It has no lungs, yet somehow whistles while it works.",
        "kind": "grave_progress",
        "base_rate": BASE_SKELETON_DIG_PROGRESS_PER_SECOND,
        "visible_when": [],
    },
    "study": {
        "name": "Study Notes",
        "short_name": "Studying",
        "description": "Produces Knowledge from copied field notes.",
        "flavor": "The handwriting is poor. The insights are not.",
        "kind": "resource",
        "resource": "knowledge",
        "base_rate": BASE_SKELETON_STUDY_PER_SECOND,
        "visible_when": [{"type": "research", "key": "grave_scribes"}],
    },
    "scavenge": {
        "name": "Sift Soil",
        "short_name": "Sifting",
        "description": "Searches spoil heaps for Grave Dust.",
        "flavor": "Patient fingers find what shovels miss.",
        "kind": "resource",
        "resource": "grave_dust",
        "base_rate": BASE_SKELETON_SCAVENGE_PER_SECOND,
        "visible_when": [{"type": "research", "key": "dust_seekers"}],
    },
    "haunt": {
        "name": "Haunt the Veil",
        "short_name": "Haunting",
        "description": "Condenses a slow stream of Ectoplasm.",
        "flavor": "The room grows colder wherever it points.",
        "kind": "resource",
        "resource": "ectoplasm",
        "base_rate": BASE_SKELETON_HAUNT_PER_SECOND,
        "visible_when": [{"type": "research", "key": "veil_cartography"}],
    },
}


SKELETON_NAME_POOL = (
    "Morrow", "Knuckle", "Tallow", "Rattle", "Hush", "Mildew",
    "Crook", "Penny", "Ash", "Sable", "Marrow", "Cinder",
)


PART_DEFS = {
    "head": {"name": "Head", "symbol": "◉", "slot": "head", "shape": "skull"},
    "torso": {"name": "Torso", "symbol": "≋", "slot": "torso", "shape": "ribs"},
    "left_arm": {"name": "Left Arm", "symbol": "╱", "slot": "left_arm", "shape": "long-bone"},
    "right_arm": {"name": "Right Arm", "symbol": "╲", "slot": "right_arm", "shape": "long-bone"},
    "left_leg": {"name": "Left Leg", "symbol": "╱", "slot": "left_leg", "shape": "long-bone"},
    "right_leg": {"name": "Right Leg", "symbol": "╲", "slot": "right_leg", "shape": "long-bone"},
    "soulgem": {"name": "Soulgem", "symbol": "◆", "slot": "soulgem", "shape": "gem"},
}

SLOT_DEFS = {
    key: {"name": definition["name"], "accepts": key, "shape": definition["shape"]}
    for key, definition in PART_DEFS.items()
}


ACTIVITY_DEFS = {
    "excavation": {
        "name": "Focused Excavation",
        "description": "Stop the moving marker inside the marked soil seam.",
        "flavor": "A careful strike can uncover what brute force destroys.",
        "duration": 6.0,
        "target_width": 0.18,
        "visible_when": [{"type": "stat", "key": "graves_opened", "value": 1}],
    },
    "seance": {
        "name": "Séance",
        "description": "Memorize six flashing runes, then repeat them on the 4 × 4 circle.",
        "flavor": "The dead answer patterns more readily than questions.",
        "reveal_seconds": 4.7,
        "reveal_interval": 0.7,
        "sequence_length": 6,
        "cost": {"mana": 18.0},
        "reward": {"souls": 1.0, "ectoplasm": 2.0},
        "visible_when": [{"type": "flag", "key": "soul_trap_crafted"}],
    },
}

SEANCE_SIGIL_DEFS = {
    "fehu": {"name": "Fehu", "symbol": "ᚠ"},
    "uruz": {"name": "Uruz", "symbol": "ᚢ"},
    "thurisaz": {"name": "Thurisaz", "symbol": "ᚦ"},
    "ansuz": {"name": "Ansuz", "symbol": "ᚨ"},
    "raidho": {"name": "Raidho", "symbol": "ᚱ"},
    "kenaz": {"name": "Kenaz", "symbol": "ᚲ"},
    "gebo": {"name": "Gebo", "symbol": "ᚷ"},
    "wunjo": {"name": "Wunjo", "symbol": "ᚹ"},
    "hagalaz": {"name": "Hagalaz", "symbol": "ᚺ"},
    "nauthiz": {"name": "Nauthiz", "symbol": "ᚾ"},
    "isa": {"name": "Isa", "symbol": "ᛁ"},
    "jera": {"name": "Jera", "symbol": "ᛃ"},
    "eihwaz": {"name": "Eihwaz", "symbol": "ᛇ"},
    "perthro": {"name": "Perthro", "symbol": "ᛈ"},
    "algiz": {"name": "Algiz", "symbol": "ᛉ"},
    "sowilo": {"name": "Sowilo", "symbol": "ᛋ"},
}


RECIPE_DEFS = {
    "ritual_ink": {
        "name": "Distill Ritual Ink",
        "description": "Suspend grave minerals in condensed spirit matter.",
        "flavor": "One drop can finish a sentence begun a century ago.",
        "cost": {"mana": 30.0, "grave_dust": 5.0, "ectoplasm": 3.0},
        "produces": {"ritual_ink": 1.0},
        "visible_when": [{"type": "research", "key": "ritual_alchemy"}],
    },
    "polish_relic": {
        "name": "Polish Grave Relic",
        "description": "Restore a relic so its resonance can be studied.",
        "flavor": "The tarnish comes away. The fingerprints do not.",
        "cost": {"mana": 45.0, "grave_dust": 8.0},
        "produces": {"knowledge": 4.0},
        "visible_when": [{"type": "stat", "key": "perfect_excavations", "value": 1}],
    },
}
