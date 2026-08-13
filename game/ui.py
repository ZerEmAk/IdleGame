"""Tabbed, data-driven interface for The First Rite."""

import time

from pyscript import web, when, window

from game import logic, save, state, ui_tooltips
from game.content import (
    ACTIVITY_DEFS,
    LOG_CATEGORY_DEFS,
    PART_DEFS,
    RECIPE_DEFS,
    RESEARCH_DEFS,
    RESOURCE_DEFS,
    SEANCE_SIGIL_DEFS,
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
from game.ui_components import (
    art_slot,
    cost_text,
    format_countdown,
    format_number,
    format_time,
    meter,
    prerequisite_text,
    section_heading,
    set_meter,
)
from game.visuals import TAB_VISUALS


active_tab = "overview"
_last_log_signature = None
_last_skeleton_signature = None
_last_research_signature = None
_last_milestone_signature = None
_last_operation_signature = None
_previous_resource_amounts = {}
_last_resource_pulses = {}
_drag_ghost = None
_upgrade_view = "available"
_overview_target = "rituals"


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
    web.page["tab-content"].scrollTop = 0
    apply_tab_theme()
    update_ui()


def apply_tab_theme():
    """Expose the selected room to CSS without duplicating panel logic."""

    body = window.document.body
    for tab in TAB_DEFS:
        body.classList.remove(f"tab-is-{tab['key']}")
    body.classList.add(f"tab-is-{active_tab}")


def make_tab_handler(tab_key):
    def handler(event):
        switch_tab(tab_key)
    return handler


def announce(message):
    web.page["game-announcer"].textContent = message


def overview_action_handler(event):
    switch_tab(_overview_target)


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
        event.preventDefault()
        if not logic.select_assembly_part(part_key):
            return
        state.runtime["dragged_part"] = part_key
        state.runtime["drag_pointer"] = int(event.pointerId)
        try:
            event.currentTarget.setPointerCapture(event.pointerId)
        except Exception:
            pass
        event.currentTarget.classList.add("is-dragging")
        create_drag_ghost(event.currentTarget, event.clientX, event.clientY)
        update_drag_targets(part_key, None)
    return handler


def part_pointer_move_handler(event):
    part_key = state.runtime.get("dragged_part")
    if part_key is None:
        return
    if state.runtime.get("drag_pointer") not in (None, int(event.pointerId)):
        return
    event.preventDefault()
    move_drag_ghost(event.clientX, event.clientY)
    hovered = drag_slot_at(event.clientX, event.clientY, part_key)
    update_drag_targets(part_key, hovered)


def drag_slot_at(x, y, part_key):
    """Find the best slot beneath a pointer, including overlapped hex cells."""

    candidates = window.document.elementsFromPoint(x, y)
    fallback = None
    for target in candidates:
        slot = target.closest(".slot-button") if target else None
        # Raw browser calls return JavaScript ``null`` (a truthy-looking proxy
        # to Python), not a wrapped ``None`` value.
        if not slot:
            continue
        if fallback is None:
            fallback = slot
        slot_id = str(slot.id)
        if slot_id.startswith("slot-"):
            slot_key = slot_id[5:]
            if SLOT_DEFS.get(slot_key, {}).get("accepts") == part_key:
                return slot
    return fallback


def document_pointer_up_handler(event):
    part_key = state.runtime.get("dragged_part")
    if part_key is None:
        return
    if state.runtime.get("drag_pointer") not in (None, int(event.pointerId)):
        return
    event.preventDefault()
    slot = drag_slot_at(event.clientX, event.clientY, part_key)
    cleanup_drag()
    if not slot:
        reject_assembly_drop()
        update_assembly_ui()
        return
    slot_id = str(slot.id)
    if not slot_id.startswith("slot-"):
        return
    was_ready = state.game["assembly"]["frame_ready"]
    placed = logic.place_assembly_part(part_key, slot_id[5:])
    if placed:
        animate_part_snap(slot)
    else:
        reject_assembly_drop()
    if not was_ready and state.game["assembly"]["frame_ready"]:
        save.save_game()
        announce("Skeleton frame completed.")
    update_ui()


def part_pointer_cancel_handler(event):
    cleanup_drag()
    try:
        event.currentTarget.classList.remove("is-dragging")
    except Exception:
        pass


def assembly_drag_key_handler(event):
    if str(event.key) == "Escape" and state.runtime.get("dragged_part") is not None:
        cleanup_drag()
        state.runtime["assembly_feedback"] = "Placement cancelled."
        update_assembly_ui()


def create_drag_ghost(source, x, y):
    """Create a visible proxy; the source stays put as a spatial reference."""

    global _drag_ghost
    if _drag_ghost is not None:
        _drag_ghost.remove()
    _drag_ghost = source.cloneNode(True)
    _drag_ghost.removeAttribute("id")
    _drag_ghost.removeAttribute("aria-describedby")
    _drag_ghost.classList.remove("is-dragging")
    _drag_ghost.classList.add("drag-ghost")
    _drag_ghost.disabled = False
    move_drag_ghost(x, y)
    window.document.body.appendChild(_drag_ghost)


def move_drag_ghost(x, y):
    if _drag_ghost is not None:
        # Position through fixed ``left``/``top`` coordinates. Transform-based
        # translation was resolved as (0, 0) by some PyScript/browser proxy
        # combinations, pinning the ghost in the viewport's upper-left corner.
        style = _drag_ghost.style
        style.setProperty("left", f"{float(x) + 14:.1f}px", "important")
        style.setProperty("top", f"{float(y) + 14:.1f}px", "important")
        style.setProperty("transform", "rotate(-2deg) scale(1.06)", "important")


def update_drag_targets(part_key, hovered):
    hovered_id = str(hovered.id) if hovered else ""
    for slot_key, definition in SLOT_DEFS.items():
        slot = web.page[f"slot-{slot_key}"]
        available = not bool(state.game["assembly"]["placed"][definition["accepts"]])
        valid = available and definition["accepts"] == part_key
        class_states = {
            "is-valid-drop": valid,
            "is-invalid-drop": available and not valid,
            "is-drag-over": valid and hovered_id == f"slot-{slot_key}",
        }
        for class_name, enabled in class_states.items():
            if enabled:
                slot.classes.add(class_name)
            else:
                slot.classes.discard(class_name)


def cleanup_drag(remove_source=True):
    global _drag_ghost
    part_key = state.runtime.get("dragged_part")
    if remove_source and part_key in PART_DEFS:
        web.page[f"part-{part_key}"].classes.discard("is-dragging")
    state.runtime["dragged_part"] = None
    state.runtime["drag_pointer"] = None
    for slot_key in SLOT_DEFS:
        slot = web.page[f"slot-{slot_key}"]
        for class_name in ("is-drag-over", "is-valid-drop", "is-invalid-drop"):
            slot.classes.discard(class_name)
    if _drag_ghost is not None:
        _drag_ghost.remove()
        _drag_ghost = None


def animate_part_snap(slot):
    """Animate a raw DOM slot returned by ``elementsFromPoint``."""

    slot.classList.remove("part-snapped")
    _ = slot.offsetWidth
    slot.classList.add("part-snapped")


def reject_assembly_drop():
    board = web.page["assembly-board"]
    board.classes.discard("drop-rejected")
    _ = board.offsetWidth
    board.classes.add("drop-rejected")


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


def make_name_change_handler(skeleton_id):
    def handler(event):
        if logic.rename_skeleton(skeleton_id, event.currentTarget.value):
            event.currentTarget.value = logic.find_skeleton(skeleton_id)["name"]
            save.save_game()
            render_skeleton_lists(force=True)
            update_skeletons_ui()
    return handler


def make_name_key_handler(skeleton_id):
    def handler(event):
        if str(event.key) == "Enter":
            event.preventDefault()
            logic.rename_skeleton(skeleton_id, event.currentTarget.value)
            event.currentTarget.blur()
        elif str(event.key) == "Escape":
            event.currentTarget.value = logic.find_skeleton(skeleton_id)["name"]
            event.currentTarget.blur()
    return handler


def make_upgrade_handler(upgrade_key):
    def handler(event):
        if logic.buy_upgrade(upgrade_key):
            save.save_game()
            announce(f"Upgrade purchased: {UPGRADE_DEFS[upgrade_key]['name']}.")
            update_ui()
    return handler


def make_upgrade_view_handler(view):
    def handler(event):
        global _upgrade_view
        _upgrade_view = view
        update_upgrades_ui()
    return handler


def make_research_handler(research_key):
    def handler(event):
        if logic.buy_research(research_key):
            save.save_game()
            announce(f"Research planned: {RESEARCH_DEFS[research_key]['name']}.")
            update_ui()
    return handler


def cancel_research_handler(event):
    if logic.cancel_research():
        save.save_game()
        render_research_queue(force=True)
        update_ui()


def make_remove_research_handler(research_key):
    def handler(event):
        if logic.remove_queued_research(research_key):
            save.save_game()
            render_research_queue(force=True)
            update_ui()
    return handler


def excavation_handler(event):
    excavation = state.game["activities"]["excavation"]
    was_active = bool(excavation["active"])
    marker_override = None
    if was_active:
        # Judge the exact pixel the player saw, then freeze it before any slow
        # UI update can advance the marker another frame.
        track_rect = web.page["excavation-target"].parentElement.getBoundingClientRect()
        marker_rect = web.page["excavation-marker"].getBoundingClientRect()
        if float(track_rect.width) > 0:
            marker_override = (
                (float(marker_rect.left) + float(marker_rect.width) / 2)
                - float(track_rect.left)
            ) / float(track_rect.width)
        web.page["excavation-marker"].classes.add("is-stopped")
    result = (
        logic.resolve_excavation(marker_override)
        if was_active
        else logic.start_excavation()
    )
    if result:
        if was_active:
            save.save_game()
        update_ui()


def seance_control_handler(event):
    phase = state.game["activities"]["seance"]["phase"]
    changed = False
    if phase == "idle":
        changed = logic.start_seance()
    elif phase == "result":
        changed = logic.reset_seance()
    if changed:
        save.save_game()
    update_ui()


def make_sigil_handler(sigil_key):
    def handler(event):
        logic.choose_seance_sigil(sigil_key)
        event.currentTarget.classList.remove("rune-feedback")
        _ = event.currentTarget.offsetWidth
        event.currentTarget.classList.add("rune-feedback")
        if state.game["activities"]["seance"]["phase"] == "result":
            save.save_game()
        update_ui()
    return handler


def make_recipe_handler(recipe_key):
    def handler(event):
        if logic.craft_recipe(recipe_key):
            save.save_game()
            update_ui()
    return handler


def make_log_filter_handler(category):
    def handler(event):
        state.game["preferences"]["log_filter"] = category
        render_log(force=True)
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
                art_slot(
                    "resource", key, f"Replaceable {definition['name']} icon",
                    definition["symbol"], "resource",
                ),
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
        row.style["--resource-color"] = definition["accent"]
        row.style["--resource-rgb"] = definition["accent_rgb"]
        row.setAttribute("role", "progressbar")
        row.setAttribute("aria-label", definition["name"])
        row.setAttribute("aria-valuemin", "0")
        row.setAttribute("aria-valuenow", "0")
        row.setAttribute("tabindex", "0")
        ui_tooltips.attach(row, definition)
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
        badge = web.span("", id=f"tab-{key}-badge", classes=["tab-badge"])
        # Badges are visual status only; keep the tab's accessible name stable.
        badge.setAttribute("aria-hidden", "true")
        button = web.button(
            web.span(TAB_VISUALS[key]["symbol"], classes=["tab-icon"], aria_hidden="true"),
            web.span(tab["label"], classes=["tab-label"]),
            badge,
            id=f"tab-{key}",
            classes=["tab-button"] + (["active"] if selected else []),
            type="button",
            on_click=make_tab_handler(key),
        )
        button.setAttribute("role", "tab")
        button.setAttribute("aria-label", tab["label"])
        button.setAttribute("aria-selected", "true" if selected else "false")
        button.setAttribute("aria-controls", f"panel-{key}")
        button.setAttribute("tabindex", "0" if selected else "-1")
        tabs.append(button)

        panel = web.section(
            id=f"panel-{key}",
            classes=["tab-panel", f"tab-theme-{key}"],
        )
        panel.setAttribute("role", "tabpanel")
        panel.setAttribute("aria-labelledby", f"tab-{key}")
        panel.hidden = not selected
        content.append(panel)

    for tab in TAB_DEFS:
        builder = PANEL_BUILDERS.get(tab["key"])
        if builder is None:
            raise ValueError(f"No panel builder registered for tab {tab['key']!r}.")
        builder(panel_for(tab["key"]))


# ====================================================================
# BUILD OVERVIEW
# ====================================================================


def build_overview_panel(panel):
    panel.append(
        section_heading(
            "Command desk",
            "The Apprentice's Ledger",
            "See what matters now, where your operation is stalled, and which room needs you next.",
        ),
        web.article(
            art_slot("research", "overview", "Replaceable command-desk artwork", "✦", "hero"),
            web.div(
                web.span("Current objective", classes=["metric-label"]),
                web.h3("Begin channeling Mana.", id="current-objective"),
                web.p("Your first useful action appears here.", id="objective-detail"),
                meter("objective-meter-fill", "Current objective progress"),
                web.div(
                    web.span("0%", id="objective-progress-text"),
                    web.span("Opening rite", id="objective-stage"),
                    classes=["meter-labels"],
                ),
            ),
            web.button(
                art_slot("button", "overview-action", "Replaceable action icon", "→", "button"),
                web.span("Go to Rituals", id="overview-action-label"),
                id="overview-action",
                classes=["primary-action", "icon-action"],
                type="button",
                on_click=overview_action_handler,
            ),
            classes=["overview-hero"],
        ),
        web.div(
            web.div(
                art_slot("skeleton", "overview-roster", "Replaceable Skeleton graphic", "☠", "small"),
                web.span("Bound servants", classes=["metric-label"]),
                web.strong("0 / 1", id="overview-skeletons"),
                web.small("No one is working yet", id="overview-skeleton-detail"),
                classes=["metric-card", "overview-vital"],
            ),
            web.div(
                art_slot("resource", "grave-progress", "Replaceable grave graphic", "†", "small"),
                web.span("Graves opened", classes=["metric-label"]),
                web.strong("0", id="overview-graves"),
                web.small("0 / 15 current layers", id="overview-grave-detail"),
                classes=["metric-card", "overview-vital"],
            ),
            web.div(
                art_slot("research", "active-project", "Replaceable research graphic", "⌁", "small"),
                web.span("Active research", classes=["metric-label"]),
                web.strong("Lectern idle", id="overview-research"),
                web.small("No Knowledge drain", id="overview-research-detail"),
                classes=["metric-card", "overview-vital"],
            ),
            web.div(
                art_slot("upgrade", "net-production", "Replaceable production graphic", "+", "small"),
                web.span("Net production", classes=["metric-label"]),
                web.strong("No automation", id="overview-production"),
                web.small("Assign Skeletons to begin", id="overview-production-detail"),
                classes=["metric-card", "overview-vital"],
            ),
            classes=["overview-vitals"],
        ),
        web.div(
            web.button(
                art_slot("button", "rituals", "Rituals icon", "✦", "button"),
                web.span("Rituals"),
                classes=["overview-room-link", "room-rituals"],
                type="button",
                on_click=make_tab_handler("rituals"),
            ),
            web.button(
                art_slot("button", "assembly", "Assembly icon", "⬡", "button"),
                web.span("Assembly"),
                classes=["overview-room-link", "room-assembly"],
                type="button",
                on_click=make_tab_handler("assembly"),
            ),
            web.button(
                art_slot("button", "upgrades", "Upgrades icon", "◆", "button"),
                web.span("Upgrades"),
                classes=["overview-room-link", "room-upgrades"],
                type="button",
                on_click=make_tab_handler("upgrades"),
            ),
            web.button(
                art_slot("button", "research", "Research icon", "⌁", "button"),
                web.span("Research"),
                classes=["overview-room-link", "room-research"],
                type="button",
                on_click=make_tab_handler("research"),
            ),
            classes=["overview-room-links"],
        ),
        web.div(
            web.article(
                web.div(
                    web.h3("Rite progression"),
                    web.span("Chapter I", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.div(id="milestone-list", classes=["milestone-list"]),
                classes=["content-card", "overview-milestones"],
            ),
            web.article(
                web.div(
                    web.h3("Operation status"),
                    web.span("Live", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.div(id="overview-status-list", classes=["overview-status-list"]),
                classes=["content-card", "overview-status"],
            ),
            classes=["overview-lower-grid"],
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

    excavation = ACTIVITY_DEFS["excavation"]
    seance = ACTIVITY_DEFS["seance"]
    excavation_button = web.button(
        "Begin Excavation",
        id="excavation-action",
        classes=["primary-action"],
        type="button",
        on_click=excavation_handler,
    )
    ui_tooltips.attach(excavation_button, excavation)
    seance_button = web.button(
        "Begin Séance",
        id="seance-action",
        classes=["primary-action"],
        type="button",
        on_click=seance_control_handler,
    )
    ui_tooltips.attach(seance_button, seance, details=[f"Cost: {cost_text(seance['cost'])}"])
    sigils = web.div(classes=["sigil-buttons"])
    for key, definition in SEANCE_SIGIL_DEFS.items():
        sigil = web.button(
            web.span(definition["symbol"], aria_hidden="true"),
            web.span(definition["name"], classes=["sr-only"]),
            id=f"seance-sigil-{key}",
            classes=["sigil-button"],
            type="button",
            on_click=make_sigil_handler(key),
        )
        ui_tooltips.attach(sigil, text=definition["name"])
        sigils.append(sigil)

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
        web.h3("Active rituals", id="active-rituals-heading", classes=["subsection-title"]),
        web.div(
            web.article(
                web.div(
                    web.h3(excavation["name"]),
                    web.span("Locked", id="excavation-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(excavation["description"], classes=["card-copy"]),
                web.p(excavation["flavor"], classes=["flavor-text"]),
                web.div(
                    web.div(id="excavation-target", classes=["excavation-target"]),
                    web.div(id="excavation-marker", classes=["excavation-marker"]),
                    classes=["excavation-track"],
                ),
                web.div(
                    web.span("Ready", id="excavation-feedback"),
                    web.span("Perfect: Dust + Relic"),
                    classes=["meter-labels"],
                ),
                excavation_button,
                classes=["action-card", "minigame-card"],
            ),
            web.article(
                web.div(
                    web.h3(seance["name"]),
                    web.span("Locked", id="seance-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(seance["description"], classes=["card-copy"]),
                web.p(seance["flavor"], classes=["flavor-text"]),
                web.div("The circle is quiet.", id="seance-sequence", classes=["seance-sequence"]),
                sigils,
                web.p("Begin when ready.", id="seance-feedback", classes=["helper-text"]),
                seance_button,
                classes=["action-card", "minigame-card"],
            ),
            id="active-rituals-grid",
            classes=["minigame-grid"],
        ),
    )


# ====================================================================
# BUILD WORKSHOP (generic recipes)
# ====================================================================


def build_workshop_panel(panel):
    recipes = web.div(classes=["shop-grid"])
    for key, definition in RECIPE_DEFS.items():
        button = web.button(
            "Craft",
            id=f"recipe-{key}-craft",
            type="button",
            on_click=make_recipe_handler(key),
        )
        ui_tooltips.attach(
            button,
            definition,
            details=[f"Consumes {cost_text(definition['cost'])}", f"Produces {cost_text(definition['produces'])}"],
        )
        recipes.append(
            web.article(
                web.div(
                    web.h3(definition["name"]),
                    web.span("Locked", id=f"recipe-{key}-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(definition["description"], classes=["card-copy"]),
                web.p(definition["flavor"], classes=["flavor-text"]),
                web.p("Cost: ", web.strong(cost_text(definition["cost"])), classes=["cost-line"]),
                web.p("Creates: ", web.strong(cost_text(definition["produces"])), classes=["cost-line"]),
                button,
                id=f"recipe-{key}-card",
                classes=["shop-card", "recipe-card"],
            )
        )
    panel.append(
        section_heading(
            "Crafting",
            "Workshop",
            "Convert specialist materials into research reagents and permanent value.",
        ),
        web.p(
            "Every recipe preserves value differently; compare its output with the next rite you intend to fund.",
            classes=["helper-text"],
        ),
        recipes,
    )


# ====================================================================
# BUILD ASSEMBLY
# ====================================================================


def build_assembly_panel(panel):
    part_tray = web.div(classes=["part-tray"])
    part_order = state.game["assembly"].get("part_order", list(PART_DEFS))
    for part_key in part_order:
        definition = PART_DEFS[part_key]
        button = web.button(
            art_slot(
                "part", part_key, f"Replaceable {definition['name']} graphic",
                definition["symbol"], "part",
            ),
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
        when("pointercancel", button)(part_pointer_cancel_handler)
        when("lostpointercapture", button)(part_pointer_cancel_handler)
        ui_tooltips.attach(
            button,
            text=f"{definition['name']}\nDrag to the matching silhouette slot, or select and click."
        )
        part_tray.append(button)

    skeleton_slots = web.div(id="assembly-board", classes=["skeleton-board"])
    for slot_key, definition in SLOT_DEFS.items():
        slot = web.button(
            web.span("+", id=f"slot-{slot_key}-symbol", classes=["slot-symbol"], aria_hidden="true"),
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
    summary = web.div(
        web.div(
            web.span("Bound", classes=["metric-label"]),
            web.strong("0", id="roster-bound"),
            classes=["metric-card"],
        ),
        web.div(
            web.span("Limit", classes=["metric-label"]),
            web.strong("1", id="roster-limit"),
            classes=["metric-card"],
        ),
        classes=["roster-summary"],
    )
    for job_key, definition in SKELETON_JOB_DEFS.items():
        summary.append(
            web.div(
                web.span(definition["short_name"], classes=["metric-label"]),
                web.strong("0/s", id=f"roster-{job_key}-rate"),
                classes=["metric-card"],
            )
        )

    panel.append(
        section_heading(
            "Automation",
            "Skeletons",
            "Assign each temporary skeleton independently. Research expands the binding limit.",
        ),
        summary,
        web.div(id="skeleton-list", classes=["skeleton-list"]),
    )


def skeleton_card(skeleton, prefix, compact=False):
    skeleton_id = int(skeleton["id"])
    if compact:
        name_control = web.strong(skeleton["name"], id=f"{prefix}-skeleton-{skeleton_id}-name")
    else:
        # HTML names that collide with Python keywords use a trailing
        # underscore in PyScript's web element factory (``input_``).
        name_control = web.input_(
            value=skeleton["name"],
            id=f"{prefix}-skeleton-{skeleton_id}-name",
            classes=["skeleton-name-input"],
            type="text",
            maxlength="24",
        )
        name_control.setAttribute("aria-label", f"Name for skeleton {skeleton_id}")
        when("change", name_control)(make_name_change_handler(skeleton_id))
        when("keydown", name_control)(make_name_key_handler(skeleton_id))
        ui_tooltips.attach(name_control, text="Editable name · Enter or leave the field to save · Escape to cancel")

    children = [
        web.div(
            web.div(
                art_slot(
                    "skeleton", str(skeleton_id),
                    f"Replaceable portrait for {skeleton['name']}", "☠", "portrait",
                ),
                web.div(
                    name_control,
                    web.span("Channeling", id=f"{prefix}-skeleton-{skeleton_id}-job-label"),
                ),
                classes=["skeleton-identity"],
            ),
            web.strong("0:00", id=f"{prefix}-skeleton-{skeleton_id}-time", classes=["countdown"]),
            classes=["skeleton-heading"],
        ),
        meter(f"{prefix}-skeleton-{skeleton_id}-meter", f"Skeleton {skeleton_id} remaining binding"),
    ]
    if not compact:
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
            ui_tooltips.attach(
                button,
                definition,
                details=[f"Base rate: {format_number(float(definition['base_rate']))}/s"],
            )
            jobs.append(button)
        children.append(jobs)
    return web.article(
        *children,
        classes=["skeleton-card"] + (["compact"] if compact else []),
    )


def _skeleton_dom_matches(skeletons):
    """Return whether every worker has a full card and read-only summary.

    The fast UI loop can run immediately after a roster rebuild, a load, or an
    expiry. Treat the DOM as a cache of authoritative state and repair it when
    any expected node is absent instead of letting one stale lookup stop the
    entire game loop.
    """

    if web.page["skeleton-list"] is None or web.page["skeleton-summary"] is None:
        return False
    if web.page["quick-skeleton-count"] is None:
        return False
    for skeleton in skeletons:
        skeleton_id = int(skeleton["id"])
        for prefix in ("full", "quick"):
            required_ids = (
                f"{prefix}-skeleton-{skeleton_id}-time",
                f"{prefix}-skeleton-{skeleton_id}-job-label",
                f"{prefix}-skeleton-{skeleton_id}-meter",
            )
            if any(web.page[node_id] is None for node_id in required_ids):
                return False
        for job_key in SKELETON_JOB_DEFS:
            if web.page[f"full-skeleton-{skeleton_id}-job-{job_key}"] is None:
                return False
    return True


def render_skeleton_lists(force=False):
    global _last_skeleton_signature
    skeletons = state.game["skeletons"]
    signature = tuple((int(item["id"]), str(item.get("name", ""))) for item in skeletons)
    if (
        not force
        and signature == _last_skeleton_signature
        and _skeleton_dom_matches(skeletons)
    ):
        return

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
        _last_skeleton_signature = signature
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
    # Commit the cache signature only after every required node was appended.
    _last_skeleton_signature = signature


# ====================================================================
# BUILD UPGRADES AND RESEARCH
# ====================================================================


def build_upgrades_panel(panel):
    available_grid = web.div(id="upgrade-available-grid", classes=["upgrade-grid"])
    completed_grid = web.div(id="upgrade-completed-grid", classes=["upgrade-grid"])
    for key, definition in UPGRADE_DEFS.items():
        button = web.button(
            "Purchase",
            id=f"upgrade-{key}-buy",
            type="button",
            on_click=make_upgrade_handler(key),
        )
        ui_tooltips.attach(
            button,
            definition,
            details=[f"Cost: {cost_text(definition['cost'])}"],
        )
        card = web.article(
                art_slot(
                    "upgrade", key, f"Replaceable art for {definition['name']}",
                    "◆", "card",
                ),
                web.div(
                web.div(
                    web.h3(definition["name"]),
                    web.span("Locked", id=f"upgrade-{key}-status", classes=["status-chip"]),
                    classes=["card-heading"],
                ),
                web.p(definition["description"], classes=["card-copy"]),
                web.p("Cost: ", web.strong(cost_text(definition["cost"])), classes=["cost-line"]),
                classes=["upgrade-copy"],
                ),
                button,
                id=f"upgrade-{key}-card",
                classes=["upgrade-card"],
            )
        ui_tooltips.attach(
            card,
            definition,
            details=[f"Cost: {cost_text(definition['cost'])}"],
        )
        target = completed_grid if state.game["upgrades"].get(key, False) else available_grid
        target.append(card)

    available_tab = web.button(
        "Available", web.span("0", id="upgrade-available-count", classes=["subtab-count"]),
        id="upgrade-view-available", classes=["subtab-button", "active"], type="button",
        on_click=make_upgrade_view_handler("available"),
    )
    completed_tab = web.button(
        "Completed", web.span("0", id="upgrade-completed-count", classes=["subtab-count"]),
        id="upgrade-view-completed", classes=["subtab-button"], type="button",
        on_click=make_upgrade_view_handler("completed"),
    )
    for subtab, selected, controls in (
        (available_tab, True, "upgrade-available-view"),
        (completed_tab, False, "upgrade-completed-view"),
    ):
        subtab.setAttribute("role", "tab")
        subtab.setAttribute("aria-selected", "true" if selected else "false")
        subtab.setAttribute("aria-controls", controls)

    panel.append(
        section_heading(
            "Implements",
            "Workshop Improvements",
            "A concise list of useful purchases. Acquired implements move into the Completed archive.",
        ),
        web.div(available_tab, completed_tab, classes=["panel-subtabs"], role="tablist"),
        web.section(
            available_grid,
            web.div(
                art_slot("upgrade", "empty", "No available upgrade placeholder", "◇", "hero"),
                web.h3("Nothing available"),
                web.p("Progress the rite or gather resources to reveal another implement."),
                id="upgrade-available-empty", classes=["collection-empty"],
            ),
            id="upgrade-available-view", classes=["upgrade-view"],
        ),
        web.section(
            completed_grid,
            web.div(
                art_slot("upgrade", "archive", "Completed upgrade archive placeholder", "✓", "hero"),
                web.h3("The cabinet is empty"),
                web.p("Purchased upgrades will be archived here."),
                id="upgrade-completed-empty", classes=["collection-empty"],
            ),
            id="upgrade-completed-view", classes=["upgrade-view"],
        ),
    )


def research_tier(research_key, cache=None):
    """Return a stable graph depth used by the visual research lanes."""

    cache = cache if cache is not None else {}
    if research_key in cache:
        return cache[research_key]
    prerequisites = RESEARCH_DEFS[research_key].get("prerequisites", [])
    cache[research_key] = 0 if not prerequisites else 1 + max(
        research_tier(key, cache) for key in prerequisites
    )
    return cache[research_key]


def research_is_known(research_key):
    """Reveal roots and one step beyond completed research; fog deeper nodes."""

    definition = RESEARCH_DEFS[research_key]
    completed = state.game["research"]["completed"]
    active = state.game["research"].get("active")
    planned = ([active["key"]] if active else []) + state.game["research"].get("queue", [])
    prerequisites = definition.get("prerequisites", [])
    return (
        not prerequisites
        or completed.get(research_key, False)
        or research_key in planned
        or logic.research_unlocked(research_key)
        or any(completed.get(key, False) for key in prerequisites)
    )


def research_visibility(research_key):
    if research_is_known(research_key):
        return "known"
    prerequisites = RESEARCH_DEFS[research_key].get("prerequisites", [])
    if any(research_is_known(key) for key in prerequisites):
        return "fogged"
    return "shrouded"


def build_research_panel(panel):
    categories = []
    for definition in RESEARCH_DEFS.values():
        if definition["category"] not in categories:
            categories.append(definition["category"])

    tree = web.div(classes=["research-tree"])
    tier_cache = {}
    for category in categories:
        items = web.div(classes=["research-lane-nodes"])
        category_items = [
            (key, definition) for key, definition in RESEARCH_DEFS.items()
            if definition["category"] == category
        ]
        category_items.sort(key=lambda item: (research_tier(item[0], tier_cache), item[0]))
        for key, definition in category_items:
            button = web.button(
                "Plan",
                id=f"research-{key}-buy",
                type="button",
                on_click=make_research_handler(key),
            )
            ui_tooltips.attach(
                button,
                definition,
                details=[
                    f"Duration: {format_time(definition['duration'])}",
                    f"Total drain: {format_number(definition['knowledge_cost'])} Knowledge",
                    f"Start cost: {cost_text(definition['start_cost'])}" if definition.get("start_cost") else "No start cost",
                ],
            )
            items.append(
                web.article(
                    web.span(
                        f"Tier {research_tier(key, tier_cache) + 1}",
                        classes=["research-tier"],
                    ),
                    web.div(
                        art_slot(
                            "research", key, f"Replaceable art for {definition['name']}",
                            "⌁", "research",
                        ),
                        web.strong(definition["name"], id=f"research-{key}-title"),
                        web.span(
                            f"{format_number(definition['knowledge_cost'])} K · {format_time(definition['duration'])}",
                            id=f"research-{key}-cost",
                            classes=["research-cost"],
                        ),
                        classes=["research-row-heading"],
                    ),
                    web.p(definition["description"], id=f"research-{key}-description"),
                    web.div(
                        web.span(
                            prerequisite_text(definition.get("prerequisites", [])),
                            id=f"research-{key}-requirement",
                        ),
                        button,
                        classes=["research-row-footer"],
                    ),
                    id=f"research-{key}-card",
                    classes=["research-card", "research-node"],
                )
            )
        tree.append(
            web.section(
                web.header(
                    art_slot("research", category.lower(), f"{category} branch placeholder", "⌁", "small"),
                    web.div(web.h3(category), web.p(f"{len(category_items)} studies")),
                    classes=["research-lane-heading"],
                ),
                items,
                classes=["research-lane", f"lane-{category.lower()}"],
            )
        )

    panel.append(
        section_heading(
            "Forbidden studies",
            "Research Tree",
            "Follow connected disciplines through the fog. Only nearby studies reveal their names and costs.",
        ),
        web.div(
            web.span("Available Knowledge", classes=["metric-label"]),
            web.strong("0", id="research-knowledge"),
            web.span("Completed", classes=["metric-label"]),
            web.strong(f"0 / {len(RESEARCH_DEFS)}", id="research-count"),
            web.span("Planning", classes=["metric-label"]),
            web.strong("0 / 4", id="research-planned"),
            classes=["research-summary"],
        ),
        web.article(
            web.div(
                web.div(
                    web.span("Active project", classes=["metric-label"]),
                    web.strong("Lectern idle", id="research-active-name"),
                ),
                web.span("Idle", id="research-active-status", classes=["status-chip"]),
                classes=["card-heading"],
            ),
            meter("research-active-meter", "Active research progress"),
            web.div(
                web.span("Choose an available project.", id="research-active-progress"),
                web.span("0 Knowledge/s", id="research-active-drain"),
                classes=["meter-labels"],
            ),
            web.button(
                "Cancel Active Research",
                id="cancel-research",
                classes=["quiet-button"],
                type="button",
                on_click=cancel_research_handler,
            ),
            web.div(id="research-queue-list", classes=["research-queue"]),
            classes=["research-active-card"],
        ),
        web.div(
            web.span("Visible", classes=["tree-key", "key-visible"]),
            web.span("Available", classes=["tree-key", "key-available"]),
            web.span("In progress", classes=["tree-key", "key-active"]),
            web.span("Unknown", classes=["tree-key", "key-fogged"]),
            classes=["research-tree-key"],
        ),
        tree,
    )


def render_research_queue(force=False):
    global _last_research_signature
    research_state = state.game["research"]
    active = research_state.get("active")
    signature = (active["key"] if active else None, tuple(research_state.get("queue", [])))
    if not force and signature == _last_research_signature:
        return
    _last_research_signature = signature
    container = web.page["research-queue-list"]
    container.innerHTML = ""
    queue = research_state.get("queue", [])
    if not queue:
        container.append(web.span("Queue empty", classes=["helper-text"]))
        return
    container.append(web.span("Next", classes=["metric-label"]))
    for index, key in enumerate(queue, start=1):
        container.append(
            web.div(
                web.span(f"{index}. {RESEARCH_DEFS[key]['name']}"),
                web.button(
                    "Remove",
                    classes=["text-button"],
                    type="button",
                    on_click=make_remove_research_handler(key),
                ),
                classes=["research-queue-item"],
            )
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
        ("Excavations completed", "excavations"),
        ("Perfect excavations", "perfect-excavations"),
        ("Séances completed", "seances"),
        ("Workshop recipes", "recipes"),
        ("Relics found", "relics"),
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


# Adding a tab requires one declarative TAB_DEFS row plus a build/update pair
# registered here and in PANEL_UPDATERS. Navigation itself stays generic.
PANEL_BUILDERS = {
    "overview": build_overview_panel,
    "rituals": build_rituals_panel,
    "workshop": build_workshop_panel,
    "assembly": build_assembly_panel,
    "skeletons": build_skeletons_panel,
    "upgrades": build_upgrades_panel,
    "research": build_research_panel,
    "stats": build_stats_panel,
}


def build_ui():
    web.page["version"].textContent = f"v{GAME_VERSION}"
    build_resources_ui()
    build_tabs_ui()
    build_log_filters()
    ui_tooltips.install()
    when("keydown", window.document)(assembly_drag_key_handler)
    when("pointermove", window.document)(part_pointer_move_handler)
    when("pointerup", window.document)(document_pointer_up_handler)
    when("pointercancel", window.document)(part_pointer_cancel_handler)
    apply_tab_theme()
    apply_preferences()
    render_skeleton_lists(force=True)
    render_research_queue(force=True)
    render_log(force=True)


def apply_preferences():
    reduced = bool(state.game["preferences"]["reduced_motion"])
    web.page["reduced-motion"].checked = reduced
    if reduced:
        window.document.body.classList.add("reduce-motion")
    else:
        window.document.body.classList.remove("reduce-motion")


def build_log_filters():
    container = web.page["log-filters"]
    container.innerHTML = ""
    selected = state.game["preferences"]["log_filter"]
    for key, definition in LOG_CATEGORY_DEFS.items():
        button = web.button(
            definition["name"],
            id=f"log-filter-{key}",
            classes=["log-filter"] + (["active"] if key == selected else []),
            type="button",
            on_click=make_log_filter_handler(key),
        )
        button.setAttribute("aria-pressed", "true" if key == selected else "false")
        container.append(button)


# ====================================================================
# UPDATE RESOURCE AND OVERVIEW
# ====================================================================


def update_resources_ui():
    rates = logic.production_rates()
    now = time.perf_counter()
    for key, definition in RESOURCE_DEFS.items():
        amount = float(state.game["resources"][key])
        capacity = logic.resource_capacity(key)
        rate = rates[key]
        ratio = amount / capacity if capacity > 0 else 0.0
        row = web.page[f"resource-{key}-row"]
        row.hidden = not logic.content_visible(definition)

        web.page[f"resource-{key}-amount"].textContent = format_number(amount)
        web.page[f"resource-{key}-capacity"].textContent = format_number(capacity)
        rate_prefix = "+" if rate >= 0 else "−"
        web.page[f"resource-{key}-rate"].textContent = f"{rate_prefix}{format_number(abs(rate))}"
        web.page[f"resource-{key}-bar"].style["transform"] = f"scaleX({min(1, ratio):.5f})"
        # Range semantics require machine-readable numbers, not abbreviated
        # visible strings such as "1.00K".
        row.setAttribute("aria-valuemax", str(float(capacity)))
        row.setAttribute("aria-valuenow", str(float(amount)))
        previous = _previous_resource_amounts.get(key, amount)
        last_pulse = _last_resource_pulses.get(key, 0.0)
        if (
            amount - previous >= max(0.01, capacity * 0.00005)
            and now - last_pulse >= 0.45
        ):
            row.classes.discard("resource-gained")
            _ = row.offsetWidth
            row.classes.add("resource-gained")
            _last_resource_pulses[key] = now
        _previous_resource_amounts[key] = amount


def current_objective_data():
    game = state.game
    assembly = game["assembly"]
    if not game["unlocks"]["graveyard"]:
        return {"title": f"Generate {GRAVEYARD_UNLOCK_MANA:g} Mana", "detail": "Hold the channeling sigil until the graveyard answers.", "tab": "rituals", "action": "Open Rituals", "current": game["resources"]["mana"], "target": GRAVEYARD_UNLOCK_MANA, "stage": "Opening rite"}
    if not game["unlocks"]["soul_trap"]:
        return {"title": "Open your first grave", "detail": "Clear every layer to recover Bones and Knowledge.", "tab": "rituals", "action": "Dig the Grave", "current": game["grave"]["progress"], "target": logic.grave_progress_required(), "stage": "Excavation"}
    if not game["soul_trap_crafted"]:
        return {"title": "Craft the Soul Cage", "detail": "The reusable cage captures Souls from opened graves.", "tab": "rituals", "action": "Open Rituals", "current": min(game["resources"]["mana"] / SOUL_TRAP_COST["mana"], game["resources"]["bones"] / SOUL_TRAP_COST["bones"]), "target": 1, "stage": "Spirit binding"}
    if not assembly["frame_ready"] and not assembly["started"]:
        cost = logic.assembly_cost()["bones"]
        return {"title": "Prepare a bone frame", "detail": "The Ossuary Table needs enough Bones for seven pieces.", "tab": "assembly", "action": "Open Assembly", "current": game["resources"]["bones"], "target": cost, "stage": "Assembly"}
    if assembly["started"]:
        placed = sum(bool(value) for value in assembly["placed"].values())
        return {"title": "Complete the hex lattice", "detail": "The loose parts are shuffled. Match each to its socket.", "tab": "assembly", "action": "Continue Assembly", "current": placed, "target": len(PART_DEFS), "stage": "Assembly"}
    if len(game["skeletons"]) >= logic.skeleton_limit():
        return {"title": "Expand the bound ranks", "detail": "The current command limit is full. Study Division of Labor.", "tab": "research", "action": "Open Research", "current": len(game["skeletons"]), "target": logic.skeleton_limit(), "stage": "Command"}
    if game["resources"]["souls"] < 1:
        return {"title": "Capture a Bound Soul", "detail": "Open another grave while the Soul Cage is ready.", "tab": "rituals", "action": "Open Rituals", "current": game["grave"]["progress"], "target": logic.grave_progress_required(), "stage": "Spirit binding"}
    if not logic.can_afford(SUMMON_COST):
        return {"title": "Gather summoning resources", "detail": "The vessel is waiting for enough Mana and a Soul.", "tab": "rituals", "action": "Gather Resources", "current": game["resources"]["mana"], "target": SUMMON_COST["mana"], "stage": "Summoning"}
    return {"title": "Summon the completed skeleton", "detail": "Bind the captured Soul at the Ossuary Table.", "tab": "assembly", "action": "Summon Skeleton", "current": 1, "target": 1, "stage": "Summoning"}


def current_objective():
    return current_objective_data()["title"]


def update_overview_ui():
    global _overview_target, _last_milestone_signature, _last_operation_signature
    stats = state.game["stats"]
    skeleton_count = len(state.game["skeletons"])
    rates = logic.production_rates()
    objective = current_objective_data()
    _overview_target = objective["tab"]
    ratio = min(1.0, float(objective["current"]) / max(0.0001, float(objective["target"])))
    web.page["current-objective"].textContent = objective["title"]
    web.page["objective-detail"].textContent = objective["detail"]
    web.page["overview-action-label"].textContent = objective["action"]
    web.page["objective-progress-text"].textContent = f"{ratio * 100:.0f}%"
    web.page["objective-stage"].textContent = objective["stage"]
    set_meter("objective-meter-fill", ratio)
    web.page["overview-skeletons"].textContent = f"{skeleton_count} / {logic.skeleton_limit()}"
    web.page["overview-graves"].textContent = str(stats["graves_opened"])
    web.page["overview-skeleton-detail"].textContent = (
        "No one is working yet" if skeleton_count == 0 else f"{skeleton_count} active binding(s)"
    )
    web.page["overview-grave-detail"].textContent = (
        f"{format_number(state.game['grave']['progress'])} / "
        f"{format_number(logic.grave_progress_required())} current layers"
    )
    active_research = state.game["research"].get("active")
    active_definition = RESEARCH_DEFS[active_research["key"]] if active_research else None
    web.page["overview-research"].textContent = active_definition["name"] if active_definition else "Lectern idle"
    web.page["overview-research-detail"].textContent = (
        f"{float(active_research['progress']) / float(active_definition['duration']) * 100:.0f}% · −{format_number(logic.research_drain_rate())} Knowledge/s"
        if active_research else "No Knowledge drain"
    )

    production = []
    for key, rate in rates.items():
        if abs(rate) > 0.0001 and logic.content_visible(RESOURCE_DEFS[key]):
            sign = "+" if rate > 0 else "−"
            production.append(f"{sign}{format_number(abs(rate))} {RESOURCE_DEFS[key]['name']}/s")
    web.page["overview-production"].textContent = ", ".join(production) or "No automation"
    web.page["overview-production-detail"].textContent = (
        f"{len(production)} active resource flow(s)" if production else "Assign Skeletons to begin"
    )

    items = (
        (state.game["soul_trap_crafted"], "Craft the Soul Cage"),
        (stats["skeletons_summoned"] >= 1, "Summon the first skeleton"),
        (stats["upgrades_bought"] >= 1, "Purchase an upgrade"),
        (stats["research_completed"] >= 1, "Complete research"),
        (logic.skeleton_limit() >= 2, "Unlock multiple skeletons"),
    )
    milestone_signature = tuple((bool(complete), label) for complete, label in items)
    if milestone_signature != _last_milestone_signature:
        milestones = web.page["milestone-list"]
        milestones.innerHTML = ""
        for complete, label in items:
            milestones.append(
                web.div(
                    web.span("✓" if complete else "·", classes=["milestone-mark"]),
                    web.span(label),
                    classes=["milestone"] + (["complete"] if complete else []),
                )
            )
        _last_milestone_signature = milestone_signature

    status_items = (
        ("Research", active_definition["name"] if active_definition else "Idle", bool(active_research)),
        ("Assembly", f"{sum(bool(v) for v in state.game['assembly']['placed'].values())}/7 parts", state.game["assembly"]["started"]),
        ("Workforce", f"{skeleton_count}/{logic.skeleton_limit()} bound", skeleton_count > 0),
        ("Soul Cage", "Ready" if state.game["soul_trap_crafted"] else "Not crafted", state.game["soul_trap_crafted"]),
    )
    operation_signature = tuple((label, value, bool(live)) for label, value, live in status_items)
    if operation_signature != _last_operation_signature:
        status = web.page["overview-status-list"]
        status.innerHTML = ""
        for label, value, live in status_items:
            status.append(
                web.div(
                    web.span(label),
                    web.strong(value),
                    classes=["status-line"] + (["is-live"] if live else []),
                )
            )
        _last_operation_signature = operation_signature


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
        f"+{format_number(logic.knowledge_per_grave())} Knowledge · "
        f"+{format_number(logic.grave_dust_per_grave())} Grave Dust"
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

    any_activity_visible = any(logic.content_visible(item) for item in ACTIVITY_DEFS.values())
    web.page["active-rituals-heading"].hidden = not any_activity_visible
    web.page["active-rituals-grid"].hidden = not any_activity_visible

    update_excavation_ui()
    update_seance_ui()


def update_excavation_ui():
    definition = ACTIVITY_DEFS["excavation"]
    excavation = state.game["activities"]["excavation"]
    visible = logic.content_visible(definition)
    card = web.page["excavation-action"].closest(".minigame-card")
    card.hidden = not visible
    button = web.page["excavation-action"]
    button.disabled = not visible
    button.textContent = "Strike Now" if excavation["active"] else "Begin Excavation"
    result = excavation.get("result")
    web.page["excavation-status"].textContent = (
        "Moving" if excavation["active"]
        else (result.title() if result else ("Ready" if visible else "Locked"))
    )
    marker = (
        logic.excavation_marker()
        if excavation["active"]
        else float(excavation.get("stopped_marker", 0.0))
    )
    width = logic.excavation_target_width()
    target = float(excavation["target"])
    marker_node = web.page["excavation-marker"]
    marker_node.style["left"] = f"{marker * 100:.3f}%"
    if excavation["active"]:
        marker_node.classes.discard("is-stopped")
    else:
        marker_node.classes.add("is-stopped")
    target_node = web.page["excavation-target"]
    target_node.style["left"] = f"{max(0, target - width / 2) * 100:.3f}%"
    target_node.style["width"] = f"{width * 100:.3f}%"
    if excavation["active"]:
        remaining = max(0.0, float(definition["duration"]) - float(excavation["elapsed"]))
        web.page["excavation-feedback"].textContent = f"Strike within {remaining:.1f}s"
    elif result:
        feedback = {
            "perfect": "Perfect strike — Relic uncovered!",
            "good": "Clean strike — extra Grave Dust.",
            "glancing": "Glancing strike — one layer cleared.",
        }
        web.page["excavation-feedback"].textContent = feedback[result]
    else:
        web.page["excavation-feedback"].textContent = "Ready"
    for result_name in ("perfect", "good", "glancing"):
        class_name = f"result-{result_name}"
        if result == result_name:
            card.classList.add(class_name)
        else:
            card.classList.remove(class_name)


def update_seance_ui():
    definition = ACTIVITY_DEFS["seance"]
    seance = state.game["activities"]["seance"]
    visible = logic.content_visible(definition)
    card = web.page["seance-action"].closest(".minigame-card")
    card.hidden = not visible
    phase = seance["phase"]
    web.page["seance-status"].textContent = {
        "idle": "Ready" if visible else "Locked",
        "reveal": "Memorize",
        "input": "Your turn",
        "result": "Complete",
    }[phase]
    sequence_node = web.page["seance-sequence"]
    revealed_key = None
    if phase == "reveal":
        sequence = seance["sequence"]
        total = max(0.001, float(seance.get("reveal_total", definition["reveal_seconds"])))
        elapsed = max(0.0, total - float(seance["reveal_remaining"]))
        interval = total / max(1, len(sequence))
        reveal_index = min(len(sequence) - 1, int(elapsed / interval))
        revealed_key = sequence[reveal_index]
        sequence_node.textContent = SEANCE_SIGIL_DEFS[revealed_key]["symbol"]
    elif phase == "input":
        sequence_node.textContent = "  ".join(
            SEANCE_SIGIL_DEFS[key]["symbol"] if index < seance["input_index"] else "·"
            for index, key in enumerate(seance["sequence"])
        )
    else:
        sequence_node.textContent = "The circle is quiet." if phase == "idle" else "✦"
    web.page["seance-feedback"].textContent = seance["feedback"]
    feedback_tone = seance.get("feedback_tone", "idle")
    for tone in ("reveal", "input", "correct", "failure", "success"):
        class_name = f"tone-{tone}"
        if feedback_tone == tone:
            card.classList.add(class_name)
        else:
            card.classList.remove(class_name)
    control = web.page["seance-action"]
    control.textContent = {"idle": "Begin Séance", "reveal": "Watch the Pattern", "input": "Choose Sigils", "result": "Reset Circle"}[phase]
    control.disabled = (
        not visible
        or phase in ("reveal", "input")
        or (phase == "idle" and not logic.can_afford(definition["cost"]))
    )
    for key in SEANCE_SIGIL_DEFS:
        rune = web.page[f"seance-sigil-{key}"]
        rune.disabled = phase != "input"
        if key == revealed_key:
            rune.classes.add("is-revealed")
        else:
            rune.classes.discard("is-revealed")
        if key == seance.get("last_sigil") and feedback_tone == "failure":
            rune.classes.add("is-wrong")
        else:
            rune.classes.discard("is-wrong")
        if key == seance.get("last_sigil") and feedback_tone in ("correct", "success"):
            rune.classes.add("is-correct")
        else:
            rune.classes.discard("is-correct")


def update_workshop_ui():
    available = 0
    for key, definition in RECIPE_DEFS.items():
        visible = logic.recipe_visible(key)
        affordable = logic.can_afford(definition["cost"])
        card = web.page[f"recipe-{key}-card"]
        card.hidden = not visible
        web.page[f"recipe-{key}-status"].textContent = "Ready" if affordable else ("Available" if visible else "Locked")
        web.page[f"recipe-{key}-craft"].disabled = not visible or not affordable
        if visible and affordable:
            available += 1
    web.page["tab-workshop-badge"].textContent = str(available) if available else ""


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
        part.style["order"] = str(assembly.get("part_order", list(PART_DEFS)).index(part_key))
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
        web.page[f"slot-{slot_key}-symbol"].textContent = PART_DEFS[part_key]["symbol"] if filled else "+"
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
    if not _skeleton_dom_matches(skeletons):
        # DOM mutations from browser extensions or an interrupted rebuild are
        # recoverable. Rebuild once and, if it is still incomplete, let the
        # next frame retry without terminating the simulation loop.
        render_skeleton_lists(force=True)
        if not _skeleton_dom_matches(skeletons):
            return
    limit = logic.skeleton_limit()
    if active_tab == "skeletons":
        web.page["roster-bound"].textContent = str(len(skeletons))
        web.page["roster-limit"].textContent = str(limit)
        for job_key, job_definition in SKELETON_JOB_DEFS.items():
            worker_count = sum(1 for item in skeletons if item["job"] == job_key)
            unit = (
                RESOURCE_DEFS[job_definition["resource"]]["name"]
                if job_definition["kind"] == "resource"
                else "layers"
            )
            web.page[f"roster-{job_key}-rate"].textContent = (
                f"+{format_number(worker_count * logic.skeleton_job_rate(job_key))} {unit}/s"
            )
    web.page["quick-skeleton-count"].textContent = f"{len(skeletons)} / {limit}"

    duration = logic.skeleton_duration()
    for skeleton in skeletons:
        skeleton_id = int(skeleton["id"])
        remaining = float(skeleton["remaining_seconds"])
        maximum = max(1.0, float(skeleton.get("maximum_seconds", logic.skeleton_duration())))
        job = skeleton["job"]
        definition = SKELETON_JOB_DEFS[job]
        unit = RESOURCE_DEFS[definition["resource"]]["name"] if definition["kind"] == "resource" else "layers"
        job_label = f"{definition['short_name']} +{format_number(logic.skeleton_job_rate(job))} {unit}/s"

        prefixes = ("full", "quick") if active_tab == "skeletons" else ("quick",)
        for prefix in prefixes:
            web.page[f"{prefix}-skeleton-{skeleton_id}-time"].textContent = format_countdown(remaining)
            web.page[f"{prefix}-skeleton-{skeleton_id}-job-label"].textContent = job_label
            set_meter(f"{prefix}-skeleton-{skeleton_id}-meter", remaining / maximum)
        if active_tab == "skeletons":
            for job_key in SKELETON_JOB_DEFS:
                button = web.page[f"full-skeleton-{skeleton_id}-job-{job_key}"]
                button.hidden = not logic.content_visible(SKELETON_JOB_DEFS[job_key])
                selected = job_key == job
                button.setAttribute("aria-pressed", "true" if selected else "false")
                if selected:
                    button.classes.add("is-active")
                else:
                    button.classes.discard("is-active")


def update_upgrades_ui():
    available_count = 0
    visible_count = 0
    completed_count = 0
    available_grid = web.page["upgrade-available-grid"]
    completed_grid = web.page["upgrade-completed-grid"]
    for key, definition in UPGRADE_DEFS.items():
        bought = bool(state.game["upgrades"][key])
        unlocked = logic.upgrade_unlocked(key)
        affordable = logic.can_afford(definition["cost"])
        if unlocked and affordable and not bought:
            available_count += 1
        status = web.page[f"upgrade-{key}-status"]
        button = web.page[f"upgrade-{key}-buy"]
        card = web.page[f"upgrade-{key}-card"]
        if bought:
            completed_count += 1
            card.hidden = False
            if card.parentElement.id != "upgrade-completed-grid":
                completed_grid.append(card)
            status.textContent = "Purchased"
            button.textContent = "Installed"
            button.disabled = True
            card.classes.add("is-complete")
        elif not unlocked:
            if card.parentElement.id != "upgrade-available-grid":
                available_grid.append(card)
            card.hidden = True
            status.textContent = "Locked"
            button.textContent = "Locked"
            button.disabled = True
            card.classes.discard("is-complete")
        else:
            if card.parentElement.id != "upgrade-available-grid":
                available_grid.append(card)
            card.hidden = False
            visible_count += 1
            status.textContent = "Affordable" if affordable else "Available"
            button.textContent = "Purchase"
            button.disabled = not affordable
            card.classes.discard("is-complete")
    available_selected = _upgrade_view == "available"
    web.page["upgrade-available-view"].hidden = not available_selected
    web.page["upgrade-completed-view"].hidden = available_selected
    for view, selected in (("available", available_selected), ("completed", not available_selected)):
        tab = web.page[f"upgrade-view-{view}"]
        tab.setAttribute("aria-selected", "true" if selected else "false")
        if selected:
            tab.classes.add("active")
        else:
            tab.classes.discard("active")
    web.page["upgrade-available-count"].textContent = str(visible_count)
    web.page["upgrade-completed-count"].textContent = str(completed_count)
    web.page["upgrade-view-available"].setAttribute(
        "aria-label", f"Available upgrades ({visible_count})"
    )
    web.page["upgrade-view-completed"].setAttribute(
        "aria-label", f"Completed upgrades ({completed_count})"
    )
    web.page["upgrade-available-empty"].hidden = visible_count > 0
    web.page["upgrade-completed-empty"].hidden = completed_count > 0
    web.page["tab-upgrades-badge"].textContent = str(available_count) if available_count else ""


def update_research_ui():
    knowledge = state.game["resources"]["knowledge"]
    research_state = state.game["research"]
    completed_map = research_state["completed"]
    completed = sum(bool(value) for value in completed_map.values())
    active = research_state.get("active")
    planned = ([active["key"]] if active else []) + list(research_state.get("queue", []))
    available_count = 0
    web.page["research-knowledge"].textContent = format_number(knowledge)
    web.page["research-count"].textContent = f"{completed} / {len(RESEARCH_DEFS)}"
    web.page["research-planned"].textContent = f"{len(planned)} / {logic.research_queue_limit()}"

    for key, definition in RESEARCH_DEFS.items():
        bought = bool(completed_map[key])
        unlocked = logic.research_unlocked(key)
        affordable = logic.can_afford(definition.get("start_cost", {}))
        active_key = active["key"] if active else None
        queued = key in research_state.get("queue", [])
        can_plan = (
            unlocked
            and affordable
            and key not in planned
            and len(planned) < logic.research_queue_limit()
        )
        card = web.page[f"research-{key}-card"]
        button = web.page[f"research-{key}-buy"]
        requirement = web.page[f"research-{key}-requirement"]
        title = web.page[f"research-{key}-title"]
        description = web.page[f"research-{key}-description"]
        cost = web.page[f"research-{key}-cost"]
        visibility = research_visibility(key)

        for class_name in (
            "is-complete", "is-active", "is-queued", "is-available",
            "is-fogged", "is-shrouded",
        ):
            card.classes.discard(class_name)
        if visibility != "known":
            card.classes.add(f"is-{visibility}")
            card.setAttribute("aria-label", "Unknown research")
            title.textContent = "Unknown Rite"
            description.textContent = (
                "A nearby shape moves behind the fog."
                if visibility == "fogged"
                else "This branch disappears into forbidden mist."
            )
            cost.textContent = "? K · ?:??"
            requirement.textContent = "Complete nearby studies to reveal it"
            button.textContent = "Obscured"
            button.disabled = True
            button.setAttribute("aria-label", "Unknown research; complete nearby studies to reveal it")
            button.setAttribute("data-tooltip", "Unknown rite. Progress through connected studies to reveal it.")
            continue

        card.removeAttribute("aria-label")
        button.setAttribute("aria-label", f"Plan research: {definition['name']}")
        title.textContent = definition["name"]
        description.textContent = definition["description"]
        cost.textContent = (
            f"{format_number(definition['knowledge_cost'])} K · "
            f"{format_time(definition['duration'])}"
        )
        button.setAttribute(
            "data-tooltip",
            ui_tooltips.text_for(
                definition,
                [
                    f"Duration: {format_time(definition['duration'])}",
                    f"Total drain: {format_number(definition['knowledge_cost'])} Knowledge",
                ],
            ),
        )
        if bought:
            card.classes.add("is-complete")
            button.textContent = "Complete"
            button.setAttribute("aria-label", f"Research complete: {definition['name']}")
            button.disabled = True
            requirement.textContent = "Researched"
        elif key == active_key:
            card.classes.add("is-active")
            button.textContent = "Active"
            button.setAttribute("aria-label", f"Research active: {definition['name']}")
            button.disabled = True
            requirement.textContent = "In progress"
        elif queued:
            card.classes.add("is-queued")
            button.textContent = "Queued"
            button.setAttribute("aria-label", f"Research queued: {definition['name']}")
            button.disabled = True
            requirement.textContent = f"Queue position {research_state['queue'].index(key) + 1}"
        else:
            if unlocked:
                card.classes.add("is-available")
            button.textContent = "Plan" if unlocked else "Locked"
            button.disabled = not can_plan
            requirement.textContent = prerequisite_text(definition.get("prerequisites", []))
            if unlocked and definition.get("start_cost"):
                requirement.textContent += f" · Start: {cost_text(definition['start_cost'])}"
            if can_plan:
                available_count += 1
    web.page["tab-research-badge"].textContent = str(available_count) if available_count else ""
    update_research_progress_ui()
    render_research_queue()


def update_research_progress_ui():
    active = state.game["research"].get("active")
    cancel = web.page["cancel-research"]
    if active is None:
        web.page["research-active-name"].textContent = "Lectern idle"
        web.page["research-active-status"].textContent = "Idle"
        web.page["research-active-progress"].textContent = "Choose an available project."
        web.page["research-active-drain"].textContent = "0 Knowledge/s"
        set_meter("research-active-meter", 0)
        cancel.disabled = True
        return
    definition = RESEARCH_DEFS[active["key"]]
    duration = float(definition["duration"])
    progress = float(active["progress"])
    paused = bool(active.get("paused"))
    web.page["research-active-name"].textContent = definition["name"]
    web.page["research-active-status"].textContent = "Paused" if paused else "Studying"
    web.page["research-active-progress"].textContent = (
        f"{format_time(progress)} / {format_time(duration)} · "
        f"{format_number(active['knowledge_spent'])} / {format_number(definition['knowledge_cost'])} Knowledge"
    )
    web.page["research-active-drain"].textContent = f"−{format_number(logic.research_drain_rate())} Knowledge/s"
    set_meter("research-active-meter", progress / duration)
    cancel.disabled = False


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
        "excavations": str(stats["excavations_completed"]),
        "perfect-excavations": str(stats["perfect_excavations"]),
        "seances": str(stats["seances_completed"]),
        "recipes": str(stats["recipes_crafted"]),
        "relics": str(stats["relics_found"]),
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

    recipe_count = sum(
        1 for key, definition in RECIPE_DEFS.items()
        if logic.recipe_visible(key) and logic.can_afford(definition["cost"])
    )
    web.page["tab-workshop-badge"].textContent = str(recipe_count) if recipe_count else ""

    upgrade_count = sum(
        1 for key, definition in UPGRADE_DEFS.items()
        if not state.game["upgrades"][key]
        and logic.upgrade_unlocked(key)
        and logic.can_afford(definition["cost"])
    )
    web.page["tab-upgrades-badge"].textContent = str(upgrade_count) if upgrade_count else ""

    research_state = state.game["research"]
    active = research_state.get("active")
    planned = ([active["key"]] if active else []) + list(research_state.get("queue", []))
    research_count = sum(
        1 for key, definition in RESEARCH_DEFS.items()
        if not research_state["completed"][key]
        and key not in planned
        and len(planned) < logic.research_queue_limit()
        and logic.research_unlocked(key)
        and logic.can_afford(definition.get("start_cost", {}))
    )
    web.page["tab-research-badge"].textContent = str(research_count) if research_count else ""


PANEL_UPDATERS = {
    "overview": update_overview_ui,
    "rituals": update_rituals_ui,
    "workshop": update_workshop_ui,
    "assembly": update_assembly_ui,
    "skeletons": update_skeletons_ui,
    "upgrades": update_upgrades_ui,
    "research": update_research_ui,
    "stats": update_stats_ui,
}


def update_ui():
    update_resources_ui()
    PANEL_UPDATERS[active_tab]()
    update_tab_badges()
    render_log()


def update_fast_ui():
    """Refresh global chrome and only the animation-sensitive visible panel."""

    update_resources_ui()
    if active_tab == "rituals":
        update_rituals_ui()
    update_skeletons_ui()
    if active_tab == "research":
        update_research_progress_ui()


# ====================================================================
# EVENT LOG AND STATUS
# ====================================================================


def render_log(force=False):
    global _last_log_signature
    log = state.game["log"]
    selected = state.game["preferences"]["log_filter"]
    last_id = log[-1].get("id") if log else None
    signature = (len(log), last_id, selected)
    if not force and signature == _last_log_signature:
        return
    _last_log_signature = signature

    container = web.page["event-log"]
    container.innerHTML = ""
    for key in LOG_CATEGORY_DEFS:
        button = web.page[f"log-filter-{key}"]
        active = key == selected
        button.setAttribute("aria-pressed", "true" if active else "false")
        if active:
            button.classes.add("active")
        else:
            button.classes.discard("active")

    visible_events = [
        event for event in log
        if selected == "all" or event.get("category") == selected
    ]
    if not visible_events:
        container.append(web.p("No events in this category yet.", classes=["log-empty"]))
        return
    for event in reversed(visible_events):
        category = event.get("category", "system")
        definition = LOG_CATEGORY_DEFS.get(category, LOG_CATEGORY_DEFS["system"])
        try:
            timestamp = time.strftime(
                "%H:%M:%S", time.localtime(float(event.get("timestamp", 0)))
            )
        except (OverflowError, OSError, TypeError, ValueError):
            timestamp = "--:--:--"
        container.append(
            web.article(
                web.div(
                    web.span(f"{definition['symbol']} {definition['name']}", classes=["log-category"]),
                    web.time(timestamp),
                    classes=["log-meta"],
                ),
                web.p(event.get("message", "")),
                classes=["log-entry", f"log-{category}", f"tone-{event.get('tone', 'info')}"]
            )
        )


def set_save_status(text):
    web.page["save-status"].textContent = text
