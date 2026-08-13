"""Declarative upgrades and timed research projects.

Every project has a duration and total Knowledge cost. The research system
turns that total into a continuous drain while progress is being made.
Prerequisites form a small directed graph; keep keys stable for save files.
"""


UPGRADE_DEFS = {
    "focus_sigil": {
        "name": "Focus Sigil",
        "description": "Channel 35% more Mana while holding the sigil.",
        "flavor": "A simple mark, redrawn until the hand stops shaking.",
        "cost": {"mana": 30.0},
        "unlock": [{"type": "total_resource", "resource": "mana", "value": 20}],
        "effects": [{"type": "channel_multiplier", "multiplier": 1.35}],
    },
    "iron_spade": {
        "name": "Iron Spade",
        "description": "Each manual dig clears one additional layer.",
        "flavor": "Honest iron for dishonest work.",
        "cost": {"mana": 25.0, "bones": 12.0},
        "unlock": [{"type": "stat", "key": "graves_opened", "value": 2}],
        "effects": [{"type": "dig_click_add", "amount": 1.0}],
    },
    "lined_bone_sack": {
        "name": "Lined Bone Sack",
        "description": "Double Bone storage capacity.",
        "flavor": "The lining keeps the smaller pieces from escaping.",
        "cost": {"bones": 24.0},
        "unlock": [{"type": "stat", "key": "graves_opened", "value": 4}],
        "effects": [{"type": "resource_capacity_multiplier", "resources": ["bones"], "multiplier": 2.0}],
    },
    "grave_lantern": {
        "name": "Grave Lantern",
        "description": "Opened graves yield 50% more Bones.",
        "flavor": "Its flame leans toward occupied soil.",
        "cost": {"mana": 60.0, "bones": 24.0},
        "unlock": [{"type": "flag", "key": "soul_trap_crafted"}],
        "effects": [{"type": "bones_per_grave_multiplier", "multiplier": 1.5}],
    },
    "silver_wire": {
        "name": "Silver Wire",
        "description": "The Soul Cage can hold one additional spirit.",
        "flavor": "It hums whenever someone says goodbye.",
        "cost": {"mana": 80.0, "bones": 20.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 1}],
        "effects": [{"type": "resource_capacity_add", "resource": "souls", "amount": 1.0}],
    },
    "etched_trowel": {
        "name": "Etched Trowel",
        "description": "Focused Excavation has a 30% wider success zone.",
        "flavor": "Tiny runes guide the edge around fragile finds.",
        "cost": {"mana": 55.0, "grave_dust": 5.0},
        "unlock": [{"type": "stat", "key": "excavations_completed", "value": 2}],
        "effects": [{"type": "excavation_target_multiplier", "multiplier": 1.3}],
    },
    "copper_athame": {
        "name": "Copper Athame",
        "description": "Séance sigils remain visible 30% longer.",
        "flavor": "Copper remembers every circle it has cut.",
        "cost": {"mana": 70.0, "ectoplasm": 5.0},
        "unlock": [{"type": "stat", "key": "seances_completed", "value": 1}],
        "effects": [{"type": "seance_reveal_multiplier", "multiplier": 1.3}],
    },
    "black_candles": {
        "name": "Black Candles",
        "description": "Successful séances yield 50% more Ectoplasm.",
        "flavor": "They cast shadows before they are lit.",
        "cost": {"bones": 25.0, "ectoplasm": 10.0},
        "unlock": [{"type": "stat", "key": "seances_completed", "value": 3}],
        "effects": [{"type": "seance_reward_multiplier", "multiplier": 1.5}],
    },
    "chalk_matrix": {
        "name": "Chalk Matrix",
        "description": "Preparing a bone frame costs 20% fewer Bones.",
        "flavor": "Every line has a purpose. None forgive a smudge.",
        "cost": {"mana": 120.0, "bones": 45.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 2}],
        "effects": [{"type": "assembly_cost_multiplier", "multiplier": 0.8}],
    },
    "binding_salts": {
        "name": "Binding Salts",
        "description": "Skeleton bindings last 25% longer.",
        "flavor": "A boundary the dead dislike crossing.",
        "cost": {"mana": 160.0, "souls": 2.0},
        "unlock": [{"type": "stat", "key": "servants_expired", "value": 2}],
        "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 1.25}],
    },
    "grave_compass": {
        "name": "Grave Compass",
        "description": "Skeletons assigned to graves dig 50% faster.",
        "flavor": "It points down. It always points down.",
        "cost": {"mana": 200.0, "bones": 60.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 4}],
        "effects": [{"type": "skeleton_work_multiplier", "job": "graves", "multiplier": 1.5}],
    },
    "glass_alembic": {
        "name": "Glass Alembic",
        "description": "Workshop recipes produce 50% more output.",
        "flavor": "The glass fogs with faces when the mixture boils.",
        "cost": {"mana": 220.0, "ectoplasm": 14.0, "ritual_ink": 2.0},
        "unlock": [{"type": "research", "key": "ritual_alchemy"}],
        "effects": [{"type": "recipe_yield_multiplier", "multiplier": 1.5}],
    },
    "marrow_quill": {
        "name": "Marrow Quill",
        "description": "Research progresses 25% faster.",
        "flavor": "It scratches notes even after you set it down.",
        "cost": {"bones": 80.0, "ritual_ink": 3.0},
        "unlock": [{"type": "stat", "key": "research_completed", "value": 6}],
        "effects": [{"type": "research_speed_multiplier", "multiplier": 1.25}],
    },
    "reinforced_bindings": {
        "name": "Reinforced Bindings",
        "description": "Future skeletons last 35% longer.",
        "flavor": "Seven knots for seven bones that matter most.",
        "cost": {"mana": 300.0, "bones": 100.0, "ritual_ink": 3.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 6}],
        "effects": [{"type": "skeleton_duration_multiplier", "multiplier": 1.35}],
    },
    "polished_reliquary": {
        "name": "Polished Reliquary",
        "description": "Triple Relic storage capacity.",
        "flavor": "A safe place for unsafe keepsakes.",
        "cost": {"relics": 2.0, "ritual_ink": 4.0},
        "unlock": [{"type": "stat", "key": "relics_found", "value": 2}],
        "effects": [{"type": "resource_capacity_multiplier", "resources": ["relics"], "multiplier": 3.0}],
    },
    "foremans_bell": {
        "name": "Foreman's Bell",
        "description": "All skeleton work is 25% faster.",
        "flavor": "It rings once. Every skull turns.",
        "cost": {"mana": 420.0, "ritual_ink": 6.0, "relics": 2.0},
        "unlock": [{"type": "stat", "key": "skeletons_summoned", "value": 10}],
        "effects": [{"type": "skeleton_work_multiplier", "multiplier": 1.25}],
    },
}


def project(name, category, description, flavor, knowledge, duration,
            prerequisites=(), effects=(), start_cost=None):
    """Small constructor that keeps large research registries readable."""

    return {
        "name": name,
        "category": category,
        "description": description,
        "flavor": flavor,
        "knowledge_cost": float(knowledge),
        "duration": float(duration),
        "prerequisites": list(prerequisites),
        "start_cost": dict(start_cost or {}),
        "effects": list(effects),
    }


RESEARCH_DEFS = {
    "grave_whispers": project("Grave Whispers", "Foundation", "Graves yield 25% more Bones.", "Listen long enough and the soil lists its contents.", 2, 20, effects=[{"type": "bones_per_grave_multiplier", "multiplier": 1.25}]),
    "controlled_breath": project("Controlled Breath", "Foundation", "Channel Mana 40% faster and double Mana storage.", "The veil moves between one breath and the next.", 4, 30, ["grave_whispers"], [{"type": "channel_multiplier", "multiplier": 1.4}, {"type": "resource_capacity_multiplier", "resources": ["mana"], "multiplier": 2.0}]),
    "steady_hands": project("Steady Hands", "Foundation", "Focused Excavation success zones are 25% wider.", "Precision is merely patience with a sharper edge.", 5, 35, ["grave_whispers"], [{"type": "excavation_target_multiplier", "multiplier": 1.25}]),
    "field_notation": project("Field Notation", "Foundation", "Graves yield 50% more Knowledge.", "A discovery not recorded is only a rumor.", 7, 45, ["controlled_breath"], [{"type": "knowledge_per_grave_multiplier", "multiplier": 1.5}]),
    "practiced_hands": project("Practiced Hands", "Foundation", "Bone frames cost 25% fewer Bones.", "The seventh vessel takes half the thought of the first.", 9, 60, ["steady_hands", "field_notation"], [{"type": "assembly_cost_multiplier", "multiplier": 0.75}]),

    "bone_preservation": project("Bone Preservation", "Preservation", "Expired skeletons return four additional Bones.", "Dry joints keep better than grieving ones.", 5, 40, ["grave_whispers"], [{"type": "skeleton_return_add", "amount": 4.0}]),
    "spectral_threads": project("Spectral Threads", "Preservation", "Skeleton bindings last 50% longer.", "Invisible stitches hold the intention in place.", 8, 55, ["bone_preservation"], [{"type": "skeleton_duration_multiplier", "multiplier": 1.5}]),
    "ossuary": project("Small Ossuary", "Preservation", "Triple Bone storage capacity.", "Good shelving is the first step toward an army.", 14, 80, ["spectral_threads"], [{"type": "resource_capacity_multiplier", "resources": ["bones"], "multiplier": 3.0}]),
    "embalming_salts": project("Embalming Salts", "Preservation", "Bindings last another 40% longer.", "Preservation is a negotiation with time.", 18, 100, ["ossuary"], [{"type": "skeleton_duration_multiplier", "multiplier": 1.4}]),
    "reliquary_methods": project("Reliquary Methods", "Preservation", "Double Relic storage and excavation rewards.", "Catalog the object before it catalogs you.", 24, 120, ["embalming_salts"], [{"type": "resource_capacity_multiplier", "resources": ["relics"], "multiplier": 2.0}, {"type": "excavation_reward_multiplier", "multiplier": 2.0}], {"ritual_ink": 2.0}),

    "spectral_sight": project("Spectral Sight", "Spirit", "Séance sigils remain visible 40% longer.", "Do not stare directly at the shape behind the shape.", 5, 40, ["controlled_breath"], [{"type": "seance_reveal_multiplier", "multiplier": 1.4}]),
    "ectoplasmic_condensation": project("Ectoplasmic Condensation", "Spirit", "Séances yield 50% more Ectoplasm.", "Cold glass gives wandering spirits somewhere to settle.", 9, 60, ["spectral_sight"], [{"type": "seance_reward_multiplier", "multiplier": 1.5}]),
    "ritual_alchemy": project("Ritual Alchemy", "Spirit", "Unlock Ritual Ink distillation in the Workshop.", "Some formulae are recipes with worse consequences.", 12, 70, ["ectoplasmic_condensation"], []),
    "inked_formulae": project("Inked Formulae", "Spirit", "Research progresses 25% faster and double Mana storage again.", "Permanent ink permits permanent mistakes.", 18, 90, ["ritual_alchemy"], [{"type": "research_speed_multiplier", "multiplier": 1.25}, {"type": "resource_capacity_multiplier", "resources": ["mana"], "multiplier": 2.0}], {"ritual_ink": 1.0}),
    "soul_reservoir": project("Soul Reservoir", "Spirit", "Store three additional Bound Souls.", "More room does not make the cage quieter.", 24, 120, ["inked_formulae"], [{"type": "resource_capacity_add", "resource": "souls", "amount": 3.0}], {"ritual_ink": 2.0}),
    "veil_cartography": project("Veil Cartography", "Spirit", "Unlock the Haunt the Veil skeleton job.", "Every map has a border. This one has teeth.", 32, 150, ["soul_reservoir"], [{"type": "resource_capacity_multiplier", "resources": ["ectoplasm"], "multiplier": 2.0}], {"ritual_ink": 3.0}),

    "division_of_labor": project("Division of Labor", "Command", "Bind one additional skeleton at a time.", "Two workers create twice the work and three times the trouble.", 10, 65, ["spectral_threads"], [{"type": "skeleton_limit_add", "amount": 1}]),
    "command_runes": project("Command Runes", "Command", "All skeleton work is 50% faster.", "Clear instructions matter when the listener lacks a brain.", 14, 80, ["division_of_labor"], [{"type": "skeleton_work_multiplier", "multiplier": 1.5}]),
    "grave_scribes": project("Grave Scribes", "Command", "Unlock the Study Notes skeleton job.", "A skull makes a surprisingly stable inkwell.", 18, 95, ["command_runes", "field_notation"], []),
    "dust_seekers": project("Dust Seekers", "Command", "Unlock the Sift Soil skeleton job.", "Give idle hands a sieve.", 22, 110, ["grave_scribes", "steady_hands"], []),
    "expanded_ranks": project("Expanded Ranks", "Command", "Bind two additional skeletons at a time.", "A row becomes a rank when every skull faces forward.", 30, 150, ["command_runes", "ritual_alchemy"], [{"type": "skeleton_limit_add", "amount": 2}], {"ritual_ink": 2.0}),
    "soul_vault": project("Soul Vault", "Command", "Store three additional Bound Souls.", "The hinges complain in voices you almost recognize.", 24, 120, ["command_runes"], [{"type": "resource_capacity_add", "resource": "souls", "amount": 3.0}]),
    "tireless_dead": project("Tireless Dead", "Command", "Double every future binding duration.", "Fatigue was always a living problem.", 38, 180, ["expanded_ranks", "embalming_salts"], [{"type": "skeleton_duration_multiplier", "multiplier": 2.0}], {"ritual_ink": 3.0}),
    "overseer_runes": project("Overseer Runes", "Command", "All skeleton work is 50% faster again.", "Authority, reduced to a symbol even the dead understand.", 46, 210, ["tireless_dead", "veil_cartography"], [{"type": "skeleton_work_multiplier", "multiplier": 1.5}], {"ritual_ink": 5.0, "relics": 1.0}),
    "legion_protocols": project("Legion Protocols", "Command", "Bind three more skeletons and plan two more studies.", "At sufficient scale, necromancy becomes administration.", 60, 300, ["overseer_runes", "reliquary_methods"], [{"type": "skeleton_limit_add", "amount": 3}, {"type": "research_queue_add", "amount": 2}], {"ritual_ink": 8.0, "relics": 2.0}),
}
