"""Visual registry and replaceable placeholder-art paths.

Gameplay definitions should not care how art is rendered. To replace a
placeholder later, add a path to ``ART_OVERRIDES[kind][content_key]``. The UI
keeps the same semantic label, fallback glyph, sizing, and animation hooks.
"""

from game.content_core import TAB_DEFS


PLACEHOLDER_ASSETS = {
    "resource": "assets/placeholders/resource.svg",
    "upgrade": "assets/placeholders/upgrade.svg",
    "research": "assets/placeholders/research.svg",
    "part": "assets/placeholders/skeleton-part.svg",
    "skeleton": "assets/placeholders/skeleton.svg",
    "button": "assets/placeholders/button.svg",
}

# Add content-specific art here without changing panel code, for example:
# ART_OVERRIDES["resource"]["mana"] = "assets/art/resources/mana.svg"
ART_OVERRIDES = {kind: {} for kind in PLACEHOLDER_ASSETS}

# Derived from the one tab registry so labels, icons, and room names cannot drift.
TAB_VISUALS = {
    tab["key"]: {"symbol": tab["symbol"], "name": tab["scene"]}
    for tab in TAB_DEFS
}


def art_path(kind, content_key):
    """Resolve item-specific art, falling back to its replaceable category SVG."""

    return ART_OVERRIDES.get(kind, {}).get(content_key, PLACEHOLDER_ASSETS[kind])
