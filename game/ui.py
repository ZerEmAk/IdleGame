"""Tabbed, data-driven interface for The First Rite."""

import math

from pyscript import web, when, window

from game import logic, save, state
from game.content import (
    PART_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
    SKELETON_JOB_DEFS,
    SLOT_DEFS,
    TAB_DEFS,
    UPGRADE_DEFS,
)
from game.definitions import (
    GAME_VERSION,
    GRAVEYARD_UNLOCK_MANA,
    KNOWLEDGE_PER_EXPIRED_SKELETON,
    KNOWLEDGE_PER_GRAVE,
    SOUL_TRAP_COST,
    SUMMON_COST,
)


active_tab = "overview"
_last_log_signature = None
_last_skeleton_signature = None


# ====================================================================
# FORMATTING
# ====================================================================


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
    return " + ".join(
        f"{format_number(amount)} {RESOURCE_DEFS[key]['name']}"
        for key, amount in costs.items()
    )


def prerequisite_text(keys):
    if not keys:
        return "No prerequisite"
    return "Requires " + ", ".join(RESEARCH_DEFS[key]["name"] for key in keys)


# ====================================================================
# COMMON DOM HELPERS
# ====================================================================


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


def panel_for(tab_key):
    return web.page[f"panel-{tab_key}"]


def switch_tab(tab_key):
    global active_tab
    active_tab = tab_key
    for tab in TAB_DEFS:
        key = tab["key"]
        selected = key == active_tab
        button = web.page[f"tab-{key}"]
        panel = web.page[f"panel-{key}"]
        button.setAttribute("aria-selected", "true" if selected else "false")
        button.setAttribute("tabindex", "0" if selected else "-1")
        panel.hidden = not selected
        if selected:
            button.classes.add("active")
        else:
            button.classes.discard("active")
    update_ui()


def make_tab_handler(tab_key):
    def handler(event):
        switch_tab(tab_key)
    return handler


def announce(message):
    web.page["game-announcer"].textContent = message


# ====================================================================
# ACTION HANDLERS
# ====================================================================


def channel_start(event):
    try:
        event.preventDefault()
        event.currentTarget.setPointerCapture(event.pointerId)
    except Exception:
        pass
    logic.set_channeling(True)
    update_ui()


def channel_stop(event):
    logic.set_channeling(False)
    update_ui()


def channel_key_down(event):
    if str(event.key) not in (" ", "Enter") or bool(event.repeat):
        return
    event.preventDefault()
    logic.set_channeling(True)
    update_ui()


def channel_key_up(event):
    if str(event.key) not in (" ", "Enter"):
        return
    event.preventDefault()
    logic.set_channeling(False)
    update_ui()


def dig_handler(event):
    before = state.game["stats"]["graves_opened"]
    if logic.dig_grave():
        if state.game["stats"]["graves_opened"] > before:
            announce("A grave was opened.")
        update_ui()


def craft_trap_handler(event):
    if logic.craft_soul_trap():
        save.save_game()
        announce("Soul Cage crafted.")
        update_ui()


def start_assembly_handler(event):
    if logic.start_assembly():
        announce("Bones prepared for assembly.")
        update_ui()


def make_part_click_handler(part_key):
    def handler(event):
        if logic.select_assembly_part(part_key):
            update_assembly_ui()
    return handler


def make_part_pointer_down_handler(part_key):
    def handler(event):
        if not logic.select_assembly_part(part_key):
            return
        state.runtime["dragged_part"] = part_key
        try:
            event.currentTarget.setPointerCapture(event.pointerId)
        except Exception:
            pass
        event.currentTarget.classList.add("is-dragging")
    return handler


def make_part_pointer_up_handler(part_key):
    def handler(event):
        event.currentTarget.classList.remove("is-dragging")
        target = window.document.elementFromPoint(event.clientX, event.clientY)
        slot = target.closest(".slot-button") if target else None
        state.runtime["dragged_part"] = None
        if not slot:
            update_assembly_ui()
            return

        slot_id = str(slot.id)
        if not slot_id.startswith("slot-"):
            return
        slot_key = slot_id[5:]
        was_ready = state.game["assembly"]["frame_ready"]
        logic.place_assembly_part(part_key, slot_key)
        if not was_ready and state.game["assembly"]["frame_ready"]:
            save.save_game()
            announce("Skeleton frame completed.")
        update_ui()
    return handler


def part_pointer_move_handler(event):
    if state.runtime.get("dragged_part") is None:
        return
    target = window.document.elementFromPoint(event.clientX, event.clientY)
    hovered = target.closest(".slot-button") if target else None
    hovered_id = str(hovered.id) if hovered else ""
    for slot_key in SLOT_DEFS:
        slot = web.page[f"slot-{slot_key}"]
        if hovered_id == f"slot-{slot_key}":
            slot.classes.add("is-drag-over")
        else:
            slot.classes.discard("is-drag-over")


def part_pointer_cancel_handler(event):
    state.runtime["dragged_part"] = None
    event.currentTarget.classList.remove("is-dragging")


def make_part_mouse_down_handler(part_key):
    def handler(event):
        if logic.select_assembly_part(part_key):
            state.runtime["dragged_part"] = part_key
            event.currentTarget.classList.add("is-dragging")
    return handler


def assembly_mouse_move_handler(event):
    if state.runtime.get("dragged_part") is None:
        return
    target = window.document.elementFromPoint(event.clientX, event.clientY)
    hovered = target.closest(".slot-button") if target else None
    hovered_id = str(hovered.id) if hovered else ""
    for slot_key in SLOT_DEFS:
        slot = web.page[f"slot-{slot_key}"]
        if hovered_id == f"slot-{slot_key}":
            slot.classes.add("is-drag-over")
        else:
            slot.classes.discard("is-drag-over")


def assembly_mouse_up_handler(event):
    part_key = state.runtime.get("dragged_part")
    if part_key is None:
        return
    state.runtime["dragged_part"] = None
    web.page[f"part-{part_key}"].classes.discard("is-dragging")
    target = window.document.elementFromPoint(event.clientX, event.clientY)
    slot = target.closest(".slot-button") if target else None
    for slot_key in SLOT_DEFS:
        web.page[f"slot-{slot_key}"].classes.discard("is-drag-over")
    if not slot:
        update_assembly_ui()
        return

    slot_id = str(slot.id)
    if not slot_id.startswith("slot-"):
        return
    was_ready = state.game["assembly"]["frame_ready"]
    logic.place_assembly_part(part_key, slot_id[5:])
    if not was_ready and state.game["assembly"]["frame_ready"]:
        save.save_game()
        announce("Skeleton frame completed.")
    update_ui()


def make_slot_click_handler(slot_key):
    def handler(event):
        was_ready = state.game["assembly"]["frame_ready"]
        logic.place_selected_part(slot_key)
        if not was_ready and state.game["assembly"]["frame_ready"]:
            save.save_game()
            announce("Skeleton frame completed.")
        update_ui()
    return handler


def summon_handler(event):
    if logic.summon_skeleton():
        save.save_game()
        announce("A skeleton was summoned.")
        render_skeleton_lists(force=True)
        update_ui()


def make_job_handler(skeleton_id, job):
    def handler(event):
        if logic.set_skeleton_job(skeleton_id, job):
            update_ui()
    return handler


def make_upgrade_handler(upgrade_key):
    def handler(event):
        if logic.buy_upgrade(upgrade_key):
            save.save_game()
            announce(f"Upgrade purchased: {UPGRADE_DEFS[upgrade_key]['name']}.")
            update_ui()
    return handler


def make_research_handler(research_key):
    def handler(event):
        if logic.buy_research(research_key):
            save.save_game()
            announce(f"Research completed: {RESEARCH_DEFS[research_key]['name']}.")
            update_ui()
    return handler


# ====================================================================
# BUILD RESOURCE SIDEBAR
# ====================================================================


def build_resources_ui():
    container = web.page["resources-list"]
    container.innerHTML = ""
    for key, definition in RESOURCE_DEFS.items():
        row = web.div(
            web.div(id=f"resource-{key}-bar", classes=["resource-fill"]),
            web.div(
                web.span(definition["symbol"], classes=["resource-symbol"], aria_hidden="true"),
                web.span(definition["name"], classes=["resource-name"]),
                web.span(
                    web.span("0", id=f"resource-{key}-amount"),
                    " / ",
                    web.span("0", id=f"resource-{key}-capacity"),
                    classes=["resource-amount"],
                ),
                web.span(
                    web.span("+0", id=f"resource-{key}-rate"),
                    "/s",
                    classes=["resource-rate"],
                ),
                classes=["resource-content"],
            ),
            id=f"resource-{key}-row",
            classes=["resource-row", f"resource-{definition['theme']}"],
        )
        row.setAttribute("role", "progressbar")
        row.setAttribute("aria-label", definition["name"])
        row.setAttribute("aria-valuemin", "0")
        row.setAttribute("aria-valuenow", "0")
        container.append(row)


# ====================================================================
# BUILD TAB SHELL
# ====================================================================


def build_tabs_ui():
    tabs = web.page["tabs"]
    content = web.page["tab-content"]
    tabs.innerHTML = ""
    content.innerHTML = ""
    tabs.setAttribute("role", "tablist")
    tabs.setAttribute("aria-label", "Game sections")

    for tab in TAB_DEFS:
        key = tab["key"]
        selected = key == active_tab
        button = web.button(
            tab["label"],
            web.span("", id=f"tab-{key}-badge", classes=["tab-badge"]),
            id=f"tab-{key}",
            classes=["tab-button"] + (["active"] if selected else []),
            type="button",
            on_click=make_tab_handler(key),
        )
        button.setAttribute("role", "tab")
        button.setAttribute("aria-selected", "true" if selected else "false")
        button.setAttribute("aria-controls", f"panel-{key}")
        button.setAttribute("tabindex", "0" if selected else "-1")
        tabs.append(button)

        panel = web.section(id=f"panel-{key}", classes=["tab-panel"])
        panel.setAttribute("role", "tabpanel")
        panel.setAttribute("aria-labelledby", f"tab-{key}")
        panel.hidden = not selected
        content.append(panel)

    build_overview_panel(panel_for("overview"))
    build_rituals_panel(panel_for("rituals"))
    build_assembly_panel(panel_for("assembly"))
    build_skeletons_panel(panel_for("skeletons"))
    build_upgrades_panel(panel_for("upgrades"))
    build_research_panel(panel_for("research"))
    build_stats_panel(panel_for("stats"))


# ====================================================================
# BUILD OVERVIEW
# ====================================================================


def build_overview_panel(panel):
    panel.append(
        section_heading(
            "Chapter I",
            "Your First Raising",
            "Gather resources, improve your rites, and grow a temporary workforce.",
        ),
        web.div(
            web.div(
                web.span("Current objective", classes=["metric-label"]),
                web.strong("Begin channeling Mana.", id="current-objective"),
                classes=["objective-card"],
            ),
            web.div(
                web.span("Skeletons", classes=["metric-label"]),
                web.strong("0 / 1", id="overview-skeletons"),
                classes=["metric-card"],
            ),
            web.div(
                web.span("Graves opened", classes=["metric-label"]),
                web.strong("0", id="overview-graves"),
                classes=["metric-card"],
            ),
            web.div(
                web.span("Production", classes=["metric-label"]),
                web.strong("No automation", id="overview-production"),
                classes=["metric-card"],
            ),
            classes=["overview-grid"],
        ),
        web.div(
            web.button(
                "Open Rituals",
                classes=["primary-action"],
                type="button",
                on_click=make_tab_handler("rituals"),
            ),
            web.button(
                "Open Assembly",
                type="button",
                on_click=make_tab_handler("assembly"),
            ),
            web.button(
                "View Upgrades",
                type="button",
                on_click=make_tab_handler("upgrades"),
            ),
            web.button(
                "View Research",
                type="button",
                on_click=make_tab_handler("research"),
            ),
            classes=["quick-links"],
        ),
        web.div(
            web.h3("Progression"),
            web.div(id="milestone-list", classes=["milestone-list"]),
            classes=["content-card"],
        ),
    )


# ====================================================================
# BUILD RITUALS
# ====================================================================


def build_rituals_panel(panel):
    channel_button = web.button(
        "Hold to Channel",
        id="channel-mana",
        classes=["primary-action", "hold-button"],
        type="button",
    )
    when("pointerdown", channel_button)(channel_start)
    when("pointerup", channel_button)(channel_stop)
    when("pointercancel", channel_button)(channel_stop)
    when("lostpointercapture", channel_button)(channel_stop)
    when("keydown", channel_button)(channel_key_down)
    when("keyup", channel_button)(channel_key_up)
    when("blur", channel_button)(channel_stop)

    panel.append(
        section_heading(
            "Manual work",
            "Rituals",
            "The opening actions remain useful after automation begins.",
        ),
        web.div(
            web.article(
                web.div(
                    web.h3("Channel Mana"),
                    web.span("Manual", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p("Hold the sigil to draw Mana continuously.", classes=["card-copy"]),
                meter("channel-meter-fill", "Mana storage"),
                web.div(
                    web.span("+0 Mana/s", id="channel-rate-text"),
                    web.span("0 Mana", id="channel-status"),
                    classes=["meter-labels"],
                ),
                channel_button,
                classes=["action-card"],
            ),
            web.article(
                web.div(
                    web.h3("Dig Grave"),
                    web.span("Locked", id="grave-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(
                    "Clear layers of earth for Bones, Knowledge, and captured Souls.",
                    classes=["card-copy"],
                ),
                meter("grave-meter-fill", "Grave excavation"),
                web.div(
                    web.span("0 / 15 layers", id="grave-progress-text"),
                    web.span("+4 Bones", id="grave-yield-text"),
                    classes=["meter-labels"],
                ),
                web.button(
                    "Dig One Layer",
                    id="dig-grave",
                    classes=["primary-action"],
                    type="button",
                    on_click=dig_handler,
                ),
                web.p(
                    f"Unlocks after generating {format_number(GRAVEYARD_UNLOCK_MANA)} Mana.",
                    id="grave-lock-reason",
                    classes=["lock-reason"],
                ),
                classes=["action-card"],
            ),
            web.article(
                web.div(
                    web.h3("Soul Cage"),
                    web.span("Locked", id="soul-cage-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(
                    "A reusable cage that captures spirits from opened graves.",
                    classes=["card-copy"],
                ),
                web.p(
                    "Cost: ",
                    web.strong(cost_text(SOUL_TRAP_COST)),
                    classes=["cost-line"],
                ),
                web.button(
                    "Craft Soul Cage",
                    id="craft-soul-trap",
                    classes=["primary-action"],
                    type="button",
                    on_click=craft_trap_handler,
                ),
                web.p(
                    "Opens after your first grave.",
                    id="soul-cage-lock-reason",
                    classes=["lock-reason"],
                ),
                classes=["action-card"],
            ),
            classes=["action-grid"],
        ),
    )


# ====================================================================
# BUILD ASSEMBLY
# ====================================================================


def build_assembly_panel(panel):
    part_tray = web.div(classes=["part-tray"])
    for part_key, definition in PART_DEFS.items():
        button = web.button(
            web.span(definition["symbol"], classes=["part-symbol"], aria_hidden="true"),
            web.span(definition["name"]),
            id=f"part-{part_key}",
            classes=["part-button"],
            type="button",
            on_click=make_part_click_handler(part_key),
        )
        # Pointer-driven dragging works with mouse, pen, and touch. The
        # click-selection fallback uses the same placement logic.
        button.setAttribute("draggable", "false")
        button.setAttribute("aria-pressed", "false")
        when("pointerdown", button)(make_part_pointer_down_handler(part_key))
        when("pointermove", button)(part_pointer_move_handler)
        when("pointerup", button)(make_part_pointer_up_handler(part_key))
        when("pointercancel", button)(part_pointer_cancel_handler)
        when("mousedown", button)(make_part_mouse_down_handler(part_key))
        part_tray.append(button)

    skeleton_slots = web.div(classes=["skeleton-board"])
    for slot_key, definition in SLOT_DEFS.items():
        slot = web.button(
            web.span("+", classes=["slot-symbol"], aria_hidden="true"),
            web.span(definition["name"], id=f"slot-{slot_key}-label"),
            id=f"slot-{slot_key}",
            classes=["slot-button", f"slot-{slot_key}"],
            type="button",
            on_click=make_slot_click_handler(slot_key),
        )
        skeleton_slots.append(slot)

    panel.append(
        section_heading(
            "Workshop",
            "Skeleton Assembly",
            "Prepare a frame, then drag all seven parts onto their matching slots.",
        ),
        web.div(
            web.div(
                web.p("Frame preparation", classes=["metric-label"]),
                web.strong("14 Bones", id="assembly-cost-text"),
            ),
            web.div(
                web.p("Active skeletons", classes=["metric-label"]),
                web.strong("0 / 1", id="assembly-capacity-text"),
            ),
            web.button(
                "Prepare Bones",
                id="start-assembly",
                classes=["primary-action"],
                type="button",
                on_click=start_assembly_handler,
            ),
            classes=["assembly-toolbar"],
        ),
        web.div(
            web.section(
                web.h3("Parts"),
                web.p("Drag a part, or select it and then choose a slot.", classes=["helper-text"]),
                part_tray,
                classes=["assembly-column"],
            ),
            web.section(
                web.h3("Frame"),
                web.p("Correct placements remain attached.", classes=["helper-text"]),
                skeleton_slots,
                classes=["assembly-column"],
            ),
            classes=["assembly-layout"],
        ),
        meter("assembly-meter-fill", "Skeleton assembly progress"),
        web.div(
            web.span("0 / 7 parts", id="assembly-progress-text"),
            web.span("Prepare Bones to begin.", id="assembly-feedback"),
            classes=["meter-labels", "assembly-feedback"],
        ),
        web.article(
            web.div(
                web.h3("Summoning"),
                web.span("Locked", id="summon-status", classes=["status-chip"]),
                classes=["card-heading"],
            ),
            web.p(
                "Bind a captured Soul to the completed frame. Each skeleton starts by channeling Mana.",
                classes=["card-copy"],
            ),
            web.div(
                web.span("Cost ", web.strong(cost_text(SUMMON_COST))),
                web.span("Duration ", web.strong("0:00", id="summon-duration-text")),
                web.span("Returns ", web.strong("0 Bones", id="summon-return-text")),
                classes=["summon-metrics"],
            ),
            web.button(
                "Summon Skeleton",
                id="summon-skeleton",
                classes=["primary-action"],
                type="button",
                on_click=summon_handler,
            ),
            web.p("Complete the seven-part frame first.", id="summon-lock-reason", classes=["lock-reason"]),
            classes=["action-card", "summon-card"],
        ),
    )


# ====================================================================
# BUILD SKELETONS
# ====================================================================


def build_skeletons_panel(panel):
    panel.append(
        section_heading(
            "Automation",
            "Skeletons",
            "Assign each temporary skeleton independently. Research expands the binding limit.",
        ),
        web.div(
            web.div(web.span("Bound", classes=["metric-label"]), web.strong("0", id="roster-bound"), classes=["metric-card"]),
            web.div(web.span("Limit", classes=["metric-label"]), web.strong("1", id="roster-limit"), classes=["metric-card"]),
            web.div(web.span("Mana work", classes=["metric-label"]), web.strong("0/s", id="roster-mana-rate"), classes=["metric-card"]),
            web.div(web.span("Grave work", classes=["metric-label"]), web.strong("0/s", id="roster-grave-rate"), classes=["metric-card"]),
            classes=["roster-summary"],
        ),
        web.div(id="skeleton-list", classes=["skeleton-list"]),
    )


def skeleton_card(skeleton, prefix, compact=False):
    skeleton_id = int(skeleton["id"])
    jobs = web.div(classes=["job-buttons"])
    for job, definition in SKELETON_JOB_DEFS.items():
        button = web.button(
            definition["name"],
            id=f"{prefix}-skeleton-{skeleton_id}-job-{job}",
            classes=["job-button"],
            type="button",
            on_click=make_job_handler(skeleton_id, job),
        )
        button.setAttribute("aria-pressed", "false")
        jobs.append(button)

    return web.article(
        web.div(
            web.div(
                web.span("☠", classes=["skeleton-icon"], aria_hidden="true"),
                web.div(
                    web.strong(f"Skeleton #{skeleton_id}"),
                    web.span("Channeling", id=f"{prefix}-skeleton-{skeleton_id}-job-label"),
                ),
                classes=["skeleton-identity"],
            ),
            web.strong("0:00", id=f"{prefix}-skeleton-{skeleton_id}-time", classes=["countdown"]),
            classes=["skeleton-heading"],
        ),
        meter(f"{prefix}-skeleton-{skeleton_id}-meter", f"Skeleton {skeleton_id} remaining binding"),
        jobs,
        classes=["skeleton-card"] + (["compact"] if compact else []),
    )


def render_skeleton_lists(force=False):
    global _last_skeleton_signature
    skeletons = state.game["skeletons"]
    signature = tuple(int(item["id"]) for item in skeletons)
    if not force and signature == _last_skeleton_signature:
        return
    _last_skeleton_signature = signature

    full = web.page["skeleton-list"]
    quick = web.page["skeleton-summary"]
    full.innerHTML = ""
    quick.innerHTML = ""

    if not skeletons:
        empty = web.div(
            web.strong("No active skeletons"),
            web.p("Assemble and summon a vessel to begin automation."),
            classes=["empty-state"],
        )
        full.append(empty)
        quick.append(
            web.div(
                web.strong("0 / 1", id="quick-skeleton-count"),
                web.span("Active / limit"),
                classes=["quick-skeleton-count"],
            ),
            web.p("No active skeletons.", classes=["helper-text"]),
        )
        return

    quick.append(
        web.div(
            web.strong("0 / 1", id="quick-skeleton-count"),
            web.span("Active / limit"),
            classes=["quick-skeleton-count"],
        )
    )
    for skeleton in skeletons:
        full.append(skeleton_card(skeleton, "full"))
        quick.append(skeleton_card(skeleton, "quick", compact=True))


# ====================================================================
# BUILD UPGRADES AND RESEARCH
# ====================================================================


def build_upgrades_panel(panel):
    grid = web.div(classes=["shop-grid"])
    for key, definition in UPGRADE_DEFS.items():
        grid.append(
            web.article(
                web.div(
                    web.h3(definition["name"]),
                    web.span("Locked", id=f"upgrade-{key}-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(definition["description"], classes=["card-copy"]),
                web.p("Cost: ", web.strong(cost_text(definition["cost"])), classes=["cost-line"]),
                web.button(
                    "Purchase",
                    id=f"upgrade-{key}-buy",
                    type="button",
                    on_click=make_upgrade_handler(key),
                ),
                classes=["shop-card"],
            )
        )
    panel.append(
        section_heading(
            "One-time improvements",
            "Upgrades",
            "Upgrades use ordinary resources and improve the current game permanently.",
        ),
        grid,
    )


def build_research_panel(panel):
    categories = []
    for definition in RESEARCH_DEFS.values():
        if definition["category"] not in categories:
            categories.append(definition["category"])

    columns = web.div(classes=["research-columns"])
    for category in categories:
        items = web.div(classes=["research-list"])
        for key, definition in RESEARCH_DEFS.items():
            if definition["category"] != category:
                continue
            items.append(
                web.article(
                    web.div(
                        web.strong(definition["name"]),
                        web.span(cost_text(definition["cost"]), classes=["research-cost"]),
                        classes=["research-row-heading"],
                    ),
                    web.p(definition["description"]),
                    web.div(
                        web.span(
                            prerequisite_text(definition.get("prerequisites", [])),
                            id=f"research-{key}-requirement",
                        ),
                        web.button(
                            "Research",
                            id=f"research-{key}-buy",
                            type="button",
                            on_click=make_research_handler(key),
                        ),
                        classes=["research-row-footer"],
                    ),
                    id=f"research-{key}-card",
                    classes=["research-card"],
                )
            )
        columns.append(
            web.section(web.h3(category), items, classes=["research-category"])
        )

    panel.append(
        section_heading(
            "Long-term studies",
            "Research",
            "Knowledge comes from opened graves and expired skeletons. Effects combine with upgrades.",
        ),
        web.div(
            web.span("Available Knowledge", classes=["metric-label"]),
            web.strong("0", id="research-knowledge"),
            web.span("Completed", classes=["metric-label"]),
            web.strong("0 / 11", id="research-count"),
            classes=["research-summary"],
        ),
        columns,
    )


# ====================================================================
# BUILD STATS
# ====================================================================


def build_stats_panel(panel):
    grid = web.div(classes=["stats-grid"])
    stat_rows = (
        ("Active time", "active-time"),
        ("Offline time", "offline-time"),
        ("Channeling time", "channel-time"),
        ("Dig actions", "dig-clicks"),
        ("Graves opened", "graves"),
        ("Skeletons summoned", "summoned"),
        ("Skeletons expired", "expired"),
        ("Upgrades purchased", "upgrades"),
        ("Research completed", "research"),
        ("Assembly mistakes", "mistakes"),
    )
    for label, key in stat_rows:
        grid.append(web.span(label), web.strong("0", id=f"stat-{key}"))
    for key, definition in RESOURCE_DEFS.items():
        grid.append(
            web.span(f"Total {definition['name']} generated"),
            web.strong("0", id=f"stat-total-{key}"),
        )
    panel.append(section_heading("Game data", "Statistics"), grid)


# ====================================================================
# BUILD EVERYTHING
# ====================================================================


def build_ui():
    web.page["version"].textContent = f"v{GAME_VERSION}"
    build_resources_ui()
    build_tabs_ui()
    when("mousemove", window.document)(assembly_mouse_move_handler)
    when("mouseup", window.document)(assembly_mouse_up_handler)
    render_skeleton_lists(force=True)
    render_log(force=True)


# ====================================================================
# UPDATE RESOURCE AND OVERVIEW
# ====================================================================


def update_resources_ui():
    rates = logic.production_rates()
    for key in RESOURCE_DEFS:
        amount = float(state.game["resources"][key])
        capacity = logic.resource_capacity(key)
        rate = rates[key]
        ratio = amount / capacity if capacity > 0 else 0.0

        web.page[f"resource-{key}-amount"].textContent = format_number(amount)
        web.page[f"resource-{key}-capacity"].textContent = format_number(capacity)
        web.page[f"resource-{key}-rate"].textContent = f"+{format_number(rate)}"
        web.page[f"resource-{key}-bar"].style["transform"] = f"scaleX({min(1, ratio):.5f})"
        row = web.page[f"resource-{key}-row"]
        row.setAttribute("aria-valuemax", format_number(capacity))
        row.setAttribute("aria-valuenow", format_number(amount))


def current_objective():
    game = state.game
    assembly = game["assembly"]
    if not game["unlocks"]["graveyard"]:
        return f"Generate {GRAVEYARD_UNLOCK_MANA:g} Mana to unlock grave digging."
    if not game["unlocks"]["soul_trap"]:
        return "Open your first grave."
    if not game["soul_trap_crafted"]:
        return "Gather materials and craft the Soul Cage."
    if not assembly["frame_ready"] and not assembly["started"]:
        return "Prepare Bones and assemble a seven-part skeleton frame."
    if assembly["started"]:
        return "Drag every part onto its matching frame slot."
    if len(game["skeletons"]) >= logic.skeleton_limit():
        return "Research a larger skeleton limit or manage current assignments."
    if game["resources"]["souls"] < 1:
        return "Open a grave to capture a Bound Soul."
    if not logic.can_afford(SUMMON_COST):
        return "Gather the remaining resources for summoning."
    return "Summon the completed skeleton."


def update_overview_ui():
    stats = state.game["stats"]
    skeleton_count = len(state.game["skeletons"])
    rates = logic.production_rates()
    web.page["current-objective"].textContent = current_objective()
    web.page["overview-skeletons"].textContent = f"{skeleton_count} / {logic.skeleton_limit()}"
    web.page["overview-graves"].textContent = str(stats["graves_opened"])

    production = []
    for key, rate in rates.items():
        if rate > 0:
            production.append(f"+{format_number(rate)} {RESOURCE_DEFS[key]['name']}/s")
    web.page["overview-production"].textContent = ", ".join(production) or "No automation"

    milestones = web.page["milestone-list"]
    milestones.innerHTML = ""
    items = (
        (state.game["soul_trap_crafted"], "Craft the Soul Cage"),
        (stats["skeletons_summoned"] >= 1, "Summon the first skeleton"),
        (stats["upgrades_bought"] >= 1, "Purchase an upgrade"),
        (stats["research_completed"] >= 1, "Complete research"),
        (logic.skeleton_limit() >= 2, "Unlock multiple skeletons"),
    )
    for complete, label in items:
        milestones.append(
            web.div(
                web.span("✓" if complete else "·", classes=["milestone-mark"]),
                web.span(label),
                classes=["milestone"] + (["complete"] if complete else []),
            )
        )


# ====================================================================
# UPDATE RITUALS AND ASSEMBLY
# ====================================================================


def update_rituals_ui():
    game = state.game
    channeling = bool(state.runtime["channeling"])
    mana = game["resources"]["mana"]
    mana_capacity = logic.resource_capacity("mana")
    button = web.page["channel-mana"]
    button.textContent = "Channeling…" if channeling else "Hold to Channel"
    if channeling:
        button.classes.add("is-channeling")
    else:
        button.classes.discard("is-channeling")
    set_meter("channel-meter-fill", mana / mana_capacity)
    web.page["channel-rate-text"].textContent = f"+{format_number(logic.channel_rate())} Mana/s"
    web.page["channel-status"].textContent = f"{format_number(mana)} Mana"

    grave_unlocked = game["unlocks"]["graveyard"]
    grave_progress = float(game["grave"]["progress"])
    required = logic.grave_progress_required()
    web.page["grave-status"].textContent = "Available" if grave_unlocked else "Locked"
    web.page["dig-grave"].disabled = not grave_unlocked
    web.page["dig-grave"].textContent = f"Dig +{format_number(logic.dig_click_power())} Layer"
    set_meter("grave-meter-fill", grave_progress / required)
    web.page["grave-progress-text"].textContent = (
        f"{format_number(grave_progress)} / {format_number(required)} layers"
    )
    web.page["grave-yield-text"].textContent = (
        f"+{format_number(logic.bones_per_grave())} Bones · "
        f"+{format_number(KNOWLEDGE_PER_GRAVE)} Knowledge"
    )
    web.page["grave-lock-reason"].hidden = grave_unlocked

    trap_unlocked = game["unlocks"]["soul_trap"]
    crafted = game["soul_trap_crafted"]
    web.page["soul-cage-status"].textContent = (
        "Crafted" if crafted else ("Available" if trap_unlocked else "Locked")
    )
    trap_button = web.page["craft-soul-trap"]
    trap_button.disabled = not trap_unlocked or crafted or not logic.can_afford(SOUL_TRAP_COST)
    trap_button.textContent = "Soul Cage Crafted" if crafted else "Craft Soul Cage"
    web.page["soul-cage-lock-reason"].hidden = trap_unlocked


def update_assembly_ui():
    game = state.game
    assembly = game["assembly"]
    cost = logic.assembly_cost()
    count = sum(bool(value) for value in assembly["placed"].values())
    skeleton_count = len(game["skeletons"])

    web.page["assembly-cost-text"].textContent = cost_text(cost)
    web.page["assembly-capacity-text"].textContent = f"{skeleton_count} / {logic.skeleton_limit()}"
    prep = web.page["start-assembly"]
    prep.disabled = (
        not game["unlocks"]["assembly"]
        or assembly["started"]
        or assembly["frame_ready"]
        or not logic.can_afford(cost)
    )
    prep.textContent = (
        "Frame Complete" if assembly["frame_ready"]
        else ("Assembly in Progress" if assembly["started"] else "Prepare Bones")
    )

    for part_key in PART_DEFS:
        placed = bool(assembly["placed"][part_key])
        selected = assembly["selected_part"] == part_key
        part = web.page[f"part-{part_key}"]
        part.disabled = not assembly["started"] or placed
        part.setAttribute("draggable", "false")
        part.setAttribute("aria-pressed", "true" if selected else "false")
        if selected:
            part.classes.add("is-selected")
        else:
            part.classes.discard("is-selected")
        if placed:
            part.classes.add("is-placed")
        else:
            part.classes.discard("is-placed")

    for slot_key, definition in SLOT_DEFS.items():
        part_key = definition["accepts"]
        filled = bool(assembly["placed"][part_key])
        slot = web.page[f"slot-{slot_key}"]
        slot.disabled = not assembly["started"] or filled
        web.page[f"slot-{slot_key}-label"].textContent = (
            f"{definition['name']} · placed" if filled else definition["name"]
        )
        if filled:
            slot.classes.add("is-filled")
        else:
            slot.classes.discard("is-filled")

    set_meter("assembly-meter-fill", count / len(PART_DEFS))
    web.page["assembly-progress-text"].textContent = f"{count} / {len(PART_DEFS)} parts"
    web.page["assembly-feedback"].textContent = state.runtime["assembly_feedback"]

    at_limit = skeleton_count >= logic.skeleton_limit()
    summon_ready = assembly["frame_ready"] and not at_limit
    web.page["summon-status"].textContent = (
        "At limit" if at_limit else ("Ready" if summon_ready else "Waiting")
    )
    summon = web.page["summon-skeleton"]
    summon.disabled = (
        not summon_ready
        or not game["unlocks"]["summoning"]
        or not logic.can_afford(SUMMON_COST)
    )
    web.page["summon-duration-text"].textContent = format_countdown(logic.skeleton_duration())
    web.page["summon-return-text"].textContent = (
        f"{format_number(logic.skeleton_returned_bones())} Bones"
    )
    reason = web.page["summon-lock-reason"]
    if at_limit:
        reason.textContent = "Skeleton limit reached. Complete Division of Labor research."
        reason.hidden = False
    elif not assembly["frame_ready"]:
        reason.textContent = "Complete the seven-part frame first."
        reason.hidden = False
    else:
        reason.hidden = True


# ====================================================================
# UPDATE SKELETONS, UPGRADES, RESEARCH, STATS
# ====================================================================


def update_skeletons_ui():
    render_skeleton_lists()
    skeletons = state.game["skeletons"]
    limit = logic.skeleton_limit()
    mana_workers = sum(1 for item in skeletons if item["job"] == "mana")
    grave_workers = sum(1 for item in skeletons if item["job"] == "graves")

    web.page["roster-bound"].textContent = str(len(skeletons))
    web.page["roster-limit"].textContent = str(limit)
    web.page["roster-mana-rate"].textContent = (
        f"+{format_number(mana_workers * logic.skeleton_job_rate('mana'))}/s"
    )
    web.page["roster-grave-rate"].textContent = (
        f"+{format_number(grave_workers * logic.skeleton_job_rate('graves'))} layers/s"
    )
    web.page["quick-skeleton-count"].textContent = f"{len(skeletons)} / {limit}"

    duration = logic.skeleton_duration()
    for skeleton in skeletons:
        skeleton_id = int(skeleton["id"])
        remaining = float(skeleton["remaining_seconds"])
        job = skeleton["job"]
        if job == "mana":
            job_label = f"Channeling +{format_number(logic.skeleton_job_rate(job))} Mana/s"
        else:
            job_label = f"Digging +{format_number(logic.skeleton_job_rate(job))} layers/s"

        for prefix in ("full", "quick"):
            web.page[f"{prefix}-skeleton-{skeleton_id}-time"].textContent = format_countdown(remaining)
            web.page[f"{prefix}-skeleton-{skeleton_id}-job-label"].textContent = job_label
            set_meter(f"{prefix}-skeleton-{skeleton_id}-meter", remaining / duration)
            for job_key in SKELETON_JOB_DEFS:
                button = web.page[f"{prefix}-skeleton-{skeleton_id}-job-{job_key}"]
                selected = job_key == job
                button.setAttribute("aria-pressed", "true" if selected else "false")
                if selected:
                    button.classes.add("is-active")
                else:
                    button.classes.discard("is-active")


def update_upgrades_ui():
    available_count = 0
    for key, definition in UPGRADE_DEFS.items():
        bought = bool(state.game["upgrades"][key])
        unlocked = logic.upgrade_unlocked(key)
        affordable = logic.can_afford(definition["cost"])
        if unlocked and affordable and not bought:
            available_count += 1
        status = web.page[f"upgrade-{key}-status"]
        button = web.page[f"upgrade-{key}-buy"]
        if bought:
            status.textContent = "Purchased"
            button.textContent = "Purchased"
            button.disabled = True
        elif not unlocked:
            status.textContent = "Locked"
            button.textContent = "Locked"
            button.disabled = True
        else:
            status.textContent = "Affordable" if affordable else "Available"
            button.textContent = "Purchase"
            button.disabled = not affordable
    web.page["tab-upgrades-badge"].textContent = str(available_count) if available_count else ""


def update_research_ui():
    knowledge = state.game["resources"]["knowledge"]
    completed = sum(bool(value) for value in state.game["research"].values())
    available_count = 0
    web.page["research-knowledge"].textContent = format_number(knowledge)
    web.page["research-count"].textContent = f"{completed} / {len(RESEARCH_DEFS)}"

    for key, definition in RESEARCH_DEFS.items():
        bought = bool(state.game["research"][key])
        unlocked = logic.research_unlocked(key)
        affordable = logic.can_afford(definition["cost"])
        card = web.page[f"research-{key}-card"]
        button = web.page[f"research-{key}-buy"]
        requirement = web.page[f"research-{key}-requirement"]

        if bought:
            card.classes.add("is-complete")
            button.textContent = "Complete"
            button.disabled = True
            requirement.textContent = "Researched"
        else:
            card.classes.discard("is-complete")
            button.textContent = "Research" if unlocked else "Locked"
            button.disabled = not unlocked or not affordable
            requirement.textContent = prerequisite_text(definition.get("prerequisites", []))
            if unlocked and affordable:
                available_count += 1
    web.page["tab-research-badge"].textContent = str(available_count) if available_count else ""


def update_stats_ui():
    stats = state.game["stats"]
    values = {
        "active-time": format_time(stats["active_time"]),
        "offline-time": format_time(stats["offline_time"]),
        "channel-time": format_time(stats["channel_seconds"]),
        "dig-clicks": str(stats["dig_clicks"]),
        "graves": str(stats["graves_opened"]),
        "summoned": str(stats["skeletons_summoned"]),
        "expired": str(stats["servants_expired"]),
        "upgrades": str(stats["upgrades_bought"]),
        "research": str(stats["research_completed"]),
        "mistakes": str(stats["assembly_mistakes"]),
    }
    for key, value in values.items():
        web.page[f"stat-{key}"].textContent = value
    for key in RESOURCE_DEFS:
        web.page[f"stat-total-{key}"].textContent = format_number(
            stats["total_generated"][key]
        )


def update_tab_badges():
    skeleton_count = len(state.game["skeletons"])
    web.page["tab-skeletons-badge"].textContent = str(skeleton_count) if skeleton_count else ""
    web.page["tab-assembly-badge"].textContent = "!" if state.game["assembly"]["frame_ready"] else ""


def update_ui():
    update_resources_ui()
    update_overview_ui()
    update_rituals_ui()
    update_assembly_ui()
    update_skeletons_ui()
    update_upgrades_ui()
    update_research_ui()
    update_stats_ui()
    update_tab_badges()
    render_log()


def update_fast_ui():
    """Refresh animation-sensitive values without rebuilding shop metadata."""

    update_resources_ui()
    update_rituals_ui()
    update_skeletons_ui()


# ====================================================================
# EVENT LOG AND STATUS
# ====================================================================


def render_log(force=False):
    global _last_log_signature
    log = state.game["log"]
    signature = (len(log), log[-1] if log else None)
    if not force and signature == _last_log_signature:
        return
    _last_log_signature = signature

    container = web.page["event-log"]
    container.innerHTML = ""
    if not log:
        container.append(web.p("No events yet.", classes=["log-empty"]))
        return
    for message in reversed(log):
        container.append(web.p(message, classes=["log-entry"]))


def set_save_status(text):
    web.page["save-status"].textContent = text
