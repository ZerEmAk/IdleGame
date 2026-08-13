"""Small reusable DOM and formatting components.

Panel code should compose these helpers rather than recreate number formats,
cost labels, progress-bar accessibility, or section headings.
"""

import math

from pyscript import web

from game.content import RESEARCH_DEFS, RESOURCE_DEFS
from game.visuals import art_path


def format_number(value):
    value = float(value)
    absolute = abs(value)
    for threshold, suffix in (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ):
        if absolute >= threshold:
            return f"{value / threshold:.2f}{suffix}"
    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))
    return f"{value:.2f}"


def format_time(seconds):
    seconds = int(max(0, seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_countdown(seconds):
    seconds = int(math.ceil(max(0.0, float(seconds))))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


def cost_text(costs):
    if not costs:
        return "None"
    return " + ".join(
        f"{format_number(amount)} {RESOURCE_DEFS[key]['name']}"
        for key, amount in costs.items()
    )


def prerequisite_text(keys):
    if not keys:
        return "No prerequisite"
    return "Requires " + ", ".join(RESEARCH_DEFS[key]["name"] for key in keys)


def meter(fill_id, label, classes=None):
    track = web.div(
        web.div(id=fill_id, classes=["meter-fill"]),
        classes=["meter-track"] + (classes or []),
    )
    track.setAttribute("role", "progressbar")
    track.setAttribute("aria-label", label)
    track.setAttribute("aria-valuemin", "0")
    track.setAttribute("aria-valuemax", "100")
    track.setAttribute("aria-valuenow", "0")
    return track


def set_meter(fill_id, ratio):
    ratio = max(0.0, min(1.0, float(ratio)))
    fill = web.page[fill_id]
    fill.style["transform"] = f"scaleX({ratio:.5f})"
    fill.parentElement.setAttribute("aria-valuenow", f"{ratio * 100:.1f}")


def section_heading(kicker, title, description=None):
    children = [web.p(kicker, classes=["eyebrow"]), web.h2(title)]
    if description:
        children.append(web.p(description, classes=["section-description"]))
    return web.header(*children, classes=["section-heading"])


def art_slot(kind, content_key, label, symbol="", size="medium"):
    """Build replaceable decorative art beside an item's semantic text."""

    node = web.span(
        web.span(symbol, classes=["art-fallback"], aria_hidden="true"),
        classes=["art-slot", f"art-{kind}", f"art-{size}"],
    )
    # Every current slot sits beside a visible heading or label. Hiding the
    # placeholder avoids duplicate names and developer-facing replacement text
    # in screen-reader output; callers remain responsible for the real label.
    node.setAttribute("aria-hidden", "true")
    node.setAttribute("data-art-key", f"{kind}:{content_key}")
    node.style["--art-image"] = f"url('{art_path(kind, content_key)}')"
    return node
