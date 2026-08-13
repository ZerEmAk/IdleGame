"""Data-driven game content.

New upgrades and research should normally require only another definition in
this file. Effect types are interpreted centrally by ``logic.py`` and rendered
generically by ``ui.py``.
"""

RESOURCE_DEFS = {
    "mana": {
        "name": "Mana",
        "description": "Power drawn through the veil.",
        "base_capacity": 120.0,
        "symbol": "✦",
        "theme": "mana",
    },
    "bones": {
        "name": "Bones",
        "description": "Material for skeletal vessels.",
        "base_capacity": 100.0,
        "symbol": "†",
        "theme": "bones",
    },
    "souls": {
        "name": "Bound Souls",
        "description": "Spirits held inside the Soul Cage.",
        "base_capacity": 1.0,
        "symbol": "◌",
        "theme": "souls",
    },
    "knowledge": {
        "name": "Knowledge",
        "description": "Lessons recovered from graves and servants.",
        "base_capacity": 100.0,
        "symbol": "⌁",
        "theme": "knowledge",
    },
}

TAB_DEFS = (
    {"key": "overview", "label": "Overview"},
    {"key": "rituals", "label": "Rituals"},
    {"key": "assembly", "label": "Assembly"},
    {"key": "skeletons", "label": "Skeletons"},
    {"key": "upgrades", "label": "Upgrades"},
    {"key": "research", "label": "Research"},
    {"key": "stats", "label": "Stats"},
)

SKELETON_JOB_DEFS = {
    "mana": {
        "name": "Channel Mana",
        "short_name": "Channeling",
        "description": "Draws Mana continuously.",
    },
    "graves": {
        "name": "Dig Graves",
        "short_name": "Digging",
        "description": "Excavates graves continuously.",
    },
}


# Seven pieces make up every vessel. Separate left/right limbs make the
# drag-and-drop board feel like assembly rather than a three-choice quiz.
PART_DEFS = {
    "head": {"name": "Head", "symbol": "◯", "slot": "head"},
    "torso": {"name": "Torso", "symbol": "≋", "slot": "torso"},
    "left_arm": {"name": "Left Arm", "symbol": "╱", "slot": "left_arm"},
    "right_arm": {"name": "Right Arm", "symbol": "╲", "slot": "right_arm"},
    "left_leg": {"name": "Left Leg", "symbol": "╱", "slot": "left_leg"},
    "right_leg": {"name": "Right Leg", "symbol": "╲", "slot": "right_leg"},
    "soulgem": {"name": "Soulgem", "symbol": "◆", "slot": "soulgem"},
}

SLOT_DEFS = {
    "head": {"name": "Head", "accepts": "head"},
    "torso": {"name": "Torso", "accepts": "torso"},
    "left_arm": {"name": "Left Arm", "accepts": "left_arm"},
    "right_arm": {"name": "Right Arm", "accepts": "right_arm"},
    "left_leg": {"name": "Left Leg", "accepts": "left_leg"},
    "right_leg": {"name": "Right Leg", "accepts": "right_leg"},
    "soulgem": {"name": "Soulgem", "accepts": "soulgem"},
}


# Unlock rules are lists so adding another requirement remains data-only.
# Supported rule types: total_resource, stat, flag, and research.
UPGRADE_DEFS = {
    "focus_sigil": {
        "name": "Focus Sigil",
        "description": "Channel 35% more Mana while holding the sigil.",
        "cost": {"mana": 30.0},
        "unlock": [{"type": "total_resource", "resource": "mana", "value": 20}],
        "effects": [{"type": "channel_multiplier", "multiplier": 1.35}],
    },
    "iron_spade": {
        "name": "Iron Spade",
        "description": "Each manual dig clears one additional layer.",
        "cost": {"mana": 25.0, "bones": 12.0},
        "unlock": [{"type": "stat", "key": "graves_opened", "value": 2}],
        "effects": [{"type": "dig_click_add", "amount": 1.0}],
    },
    "lined_bone_sack": {
        "name": "Lined Bone Sack",
        "description": "Double Bone storage capacity.",
        "cost": {"bones": 24.0},
        "unlock": [{"type": "stat", "key": "graves_opened", "value": 4}],
        "effects": [{
            "type": "resource_capacity_multiplier",
            "resources": ["bones"],
            "multiplier": 2.0,
        }],
    },
    "grave_lantern": {
        "name": "Grave Lantern",
        "description": "Opened graves yield 50% more Bones.",
        "cost": {"mana": 60.0, "bones": 24.0},
        "unlock": [{"type": "flag", "key": "soul_trap_crafted"}],
        "effects": [{"type": "bones_per_grave_multiplier", "multiplier": 1.5}],
    },
    "silver_wire": {
        "name": "Silver Wire",
        "description": "The Soul Cage can hold one additional spirit.",
        "cost": {"mana": 80.0, "bones": 20.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 1}],
        "effects": [{"type": "resource_capacity_add", "resource": "souls", "amount": 1.0}],
    },
    "chalk_matrix": {
        "name": "Chalk Matrix",
        "description": "Preparing a bone frame costs 20% fewer Bones.",
        "cost": {"mana": 120.0, "bones": 45.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 2}],
        "effects": [{"type": "assembly_cost_multiplier", "multiplier": 0.8}],
    },
    "binding_salts": {
        "name": "Binding Salts",
        "description": "Skeleton bindings last 25% longer.",
        "cost": {"mana": 160.0, "souls": 2.0},
        "unlock": [{"type": "stat", "key": "servants_expired", "value": 2}],
        "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 1.25}],
    },
    "grave_compass": {
        "name": "Grave Compass",
        "description": "Skeletons assigned to graves dig 50% faster.",
        "cost": {"mana": 200.0, "bones": 60.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 4}],
        "effects": [{
            "type": "skeleton_work_multiplier",
            "job": "graves",
            "multiplier": 1.5,
        }],
    },
}


# Research is intentionally compact and prerequisite-driven. Effects combine
# with upgrade effects through the same engine.
RESEARCH_DEFS = {
    "grave_whispers": {
        "name": "Grave Whispers",
        "category": "Foundation",
        "description": "Graves yield 25% more Bones.",
        "cost": {"knowledge": 2.0},
        "prerequisites": [],
        "effects": [{"type": "bones_per_grave_multiplier", "multiplier": 1.25}],
    },
    "controlled_breath": {
        "name": "Controlled Breath",
        "category": "Foundation",
        "description": "Channel Mana 50% faster.",
        "cost": {"knowledge": 3.0},
        "prerequisites": ["grave_whispers"],
        "effects": [{"type": "channel_multiplier", "multiplier": 1.5}],
    },
    "practiced_hands": {
        "name": "Practiced Hands",
        "category": "Foundation",
        "description": "Bone frames cost 25% fewer Bones.",
        "cost": {"knowledge": 6.0},
        "prerequisites": ["controlled_breath"],
        "effects": [{"type": "assembly_cost_multiplier", "multiplier": 0.75}],
    },
    "bone_preservation": {
        "name": "Bone Preservation",
        "category": "Preservation",
        "description": "Expired skeletons return four additional Bones.",
        "cost": {"knowledge": 3.0},
        "prerequisites": ["grave_whispers"],
        "effects": [{"type": "skeleton_return_add", "amount": 4.0}],
    },
    "spectral_threads": {
        "name": "Spectral Threads",
        "category": "Preservation",
        "description": "Skeleton bindings last 50% longer.",
        "cost": {"knowledge": 4.0},
        "prerequisites": ["bone_preservation"],
        "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 1.5}],
    },
    "ossuary": {
        "name": "Small Ossuary",
        "category": "Preservation",
        "description": "Triple Bone storage capacity.",
        "cost": {"knowledge": 10.0},
        "prerequisites": ["spectral_threads"],
        "effects": [{
            "type": "resource_capacity_multiplier",
            "resources": ["bones"],
            "multiplier": 3.0,
        }],
    },
    "division_of_labor": {
        "name": "Division of Labor",
        "category": "Command",
        "description": "Bind one additional skeleton at a time.",
        "cost": {"knowledge": 7.0},
        "prerequisites": ["spectral_threads"],
        "effects": [{"type": "skeleton_limit_add", "amount": 1}],
    },
    "command_runes": {
        "name": "Command Runes",
        "category": "Command",
        "description": "All skeleton work is 50% faster.",
        "cost": {"knowledge": 10.0},
        "prerequisites": ["division_of_labor"],
        "effects": [{"type": "skeleton_work_multiplier", "multiplier": 1.5}],
    },
    "expanded_ranks": {
        "name": "Expanded Ranks",
        "category": "Command",
        "description": "Bind two additional skeletons at a time.",
        "cost": {"knowledge": 16.0},
        "prerequisites": ["command_runes"],
        "effects": [{"type": "skeleton_limit_add", "amount": 2}],
    },
    "soul_vault": {
        "name": "Soul Vault",
        "category": "Command",
        "description": "The Soul Cage holds three additional spirits.",
        "cost": {"knowledge": 12.0},
        "prerequisites": ["command_runes"],
        "effects": [{"type": "resource_capacity_add", "resource": "souls", "amount": 3.0}],
    },
    "tireless_dead": {
        "name": "Tireless Dead",
        "category": "Command",
        "description": "Double the duration of every future binding.",
        "cost": {"knowledge": 25.0},
        "prerequisites": ["expanded_ranks", "soul_vault"],
        "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 2.0}],
    },
}
