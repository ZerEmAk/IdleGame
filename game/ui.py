"""DOM creation and UI updates.

Repeated visuals are generated here from definitions.py. The HTML file only
contains the large page containers.

A useful rule:

    create UI structure once
    update only changing text/bars during the game loop

Do not rebuild the entire page every 0.2 seconds.
"""

from pyscript import web

from game import logic, state
from game.definitions import (
    BUILDING_DEFS,
    BUY_AMOUNTS,
    GAME_VERSION,
    MANUAL_ACTION,
    RESOURCE_DEFS,
    TAB_DEFS,
    UPGRADE_DEFS,
)


active_tab = "overview"


# ====================================================================
# FORMATTING
# ====================================================================


def format_number(value):
    """Simple readable number formatting for the starter framework."""

    value = float(value)
    absolute = abs(value)

    suffixes = (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )

    for threshold, suffix in suffixes:
        if absolute >= threshold:
            return f"{value / threshold:.2f}{suffix}"

    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))

    return f"{value:.1f}"



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


# ====================================================================
# EVENT HANDLER FACTORIES
# ====================================================================
#
# Dynamic buttons are created by Python. Attaching their handler while they
# are created avoids relying on a selector that existed before the button did.
# ====================================================================


def make_tab_handler(tab_key):
    def handler(event):
        set_active_tab(tab_key)
    return handler



def make_buy_amount_handler(amount):
    def handler(event):
        state.game["buy_amount"] = amount
        update_ui()
    return handler



def make_building_handler(building_key):
    def handler(event):
        if logic.buy_building(building_key):
            update_ui()
            render_log()
    return handler



def make_upgrade_handler(upgrade_key):
    def handler(event):
        if logic.buy_upgrade(upgrade_key):
            update_ui()
            render_log()
    return handler



def manual_action_handler(event):
    logic.perform_manual_action()
    update_ui()


# ====================================================================
# BUILD: RESOURCES
# ====================================================================


def build_resources_ui():
    container = web.page["resources-list"]
    container.innerHTML = ""

    for resource_key, definition in RESOURCE_DEFS.items():
        row = web.div(
            web.div(
                id=f"resource-{resource_key}-bar",
                classes=["resource-fill"],
            ),
            web.div(
                web.span(
                    definition["name"],
                    classes=["resource-name"],
                ),
                web.span(
                    web.span("0", id=f"resource-{resource_key}-amount"),
                    " / ",
                    web.span("0", id=f"resource-{resource_key}-capacity"),
                ),
                web.span(
                    "Rate",
                    classes=["resource-rate"],
                ),
                web.span(
                    web.span("0", id=f"resource-{resource_key}-rate"),
                    "/s",
                    classes=["resource-rate"],
                ),
                web.p(
                    definition.get("description", ""),
                    classes=["resource-description"],
                ),
                classes=["resource-content"],
            ),
            classes=["resource-row"],
        )

        container.append(row)


# ====================================================================
# BUILD: TABS
# ====================================================================


def build_tabs_ui():
    tabs = web.page["tabs"]
    content = web.page["tab-content"]

    tabs.innerHTML = ""
    content.innerHTML = ""

    for tab in TAB_DEFS:
        tab_key = tab["key"]
        classes = ["tab-button"]

        if tab_key == active_tab:
            classes.append("active")

        tabs.append(
            web.button(
                tab["label"],
                id=f"tab-{tab_key}",
                classes=classes,
                type="button",
                on_click=make_tab_handler(tab_key),
            )
        )

        panel_classes = ["tab-panel"]
        if tab_key == active_tab:
            panel_classes.append("active")

        panel = web.section(
            id=f"panel-{tab_key}",
            classes=panel_classes,
        )

        content.append(panel)

        if tab_key == "overview":
            build_overview_panel(panel)
        elif tab_key == "buildings":
            build_buildings_panel(panel)
        elif tab_key == "upgrades":
            build_upgrades_panel(panel)
        elif tab_key == "stats":
            build_stats_panel(panel)
        else:
            panel.append(
                web.p(f"No renderer exists for tab '{tab_key}' yet.")
            )


# ====================================================================
# BUILD: OVERVIEW
# ====================================================================


def build_overview_panel(panel):
    panel.append(
        web.h2("Overview"),
        web.p(
            "This is intentionally generic. Replace the example resources, "
            "buildings and upgrades as your real game takes shape."
        ),
        web.div(
            web.h3("Starter Action"),
            web.p(
                "A manual action is useful for testing the framework before "
                "your real opening mechanic exists."
            ),
            web.button(
                MANUAL_ACTION["label"],
                id="manual-action",
                type="button",
                on_click=manual_action_handler,
            ),
            classes=["section-box"],
        ),
        web.div(
            web.h3("Development Rule"),
            web.p(
                "Put game content in definitions.py, rules in logic.py, "
                "and presentation in ui.py / style.css."
            ),
            classes=["section-box"],
        ),
    )


# ====================================================================
# BUILD: BUILDINGS
# ====================================================================


def building_production_text(definition):
    pieces = []

    for resource_key, amount in definition.get("produces", {}).items():
        resource_name = RESOURCE_DEFS[resource_key]["name"]
        pieces.append(f"{format_number(amount)} {resource_name}/s")

    if not pieces:
        return "Produces nothing yet."

    return "Produces " + ", ".join(pieces) + "."



def build_buildings_panel(panel):
    panel.append(web.h2("Buildings"))

    selector = web.div(
        web.span("Buy:"),
        classes=["buy-selector"],
    )

    for amount in BUY_AMOUNTS:
        label = "Max" if amount == "max" else amount
        classes = ["buy-amount"]

        if state.game["buy_amount"] == amount:
            classes.append("active")

        selector.append(
            web.button(
                label,
                id=f"buy-amount-{amount}",
                classes=classes,
                type="button",
                on_click=make_buy_amount_handler(amount),
            )
        )

    panel.append(selector)

    shop_list = web.div(classes=["shop-list"])

    for building_key, definition in BUILDING_DEFS.items():
        cost_resource_name = RESOURCE_DEFS[
            definition["cost_resource"]
        ]["name"]

        shop_list.append(
            web.div(
                web.span(
                    definition["name"],
                    classes=["shop-name"],
                ),
                web.button(
                    "Buy",
                    id=f"building-{building_key}-buy",
                    classes=["shop-buy-button"],
                    type="button",
                    on_click=make_building_handler(building_key),
                ),
                web.p(
                    definition.get("description", ""),
                    classes=["shop-description"],
                ),
                web.p(
                    building_production_text(definition),
                    classes=["shop-effect"],
                ),
                web.span(
                    "Owned: ",
                    web.strong("0", id=f"building-{building_key}-owned"),
                    classes=["shop-meta"],
                ),
                web.span(
                    web.span("Buy 1", id=f"building-{building_key}-buy-label"),
                    " — ",
                    web.strong("0", id=f"building-{building_key}-cost"),
                    f" {cost_resource_name}",
                    classes=["shop-meta"],
                ),
                classes=["shop-item"],
            )
        )

    panel.append(shop_list)


# ====================================================================
# BUILD: UPGRADES
# ====================================================================


def build_upgrades_panel(panel):
    panel.append(
        web.h2("Upgrades"),
        web.p("Upgrades are one-time purchases that modify the current run."),
    )

    shop_list = web.div(classes=["shop-list"])

    for upgrade_key, definition in UPGRADE_DEFS.items():
        resource_name = RESOURCE_DEFS[
            definition["cost_resource"]
        ]["name"]

        shop_list.append(
            web.div(
                web.span(
                    definition["name"],
                    classes=["shop-name"],
                ),
                web.button(
                    "Buy",
                    id=f"upgrade-{upgrade_key}-buy",
                    classes=["shop-buy-button"],
                    type="button",
                    on_click=make_upgrade_handler(upgrade_key),
                ),
                web.p(
                    definition.get("description", ""),
                    classes=["shop-description"],
                ),
                web.span(
                    "Cost: ",
                    web.strong(
                        format_number(definition["cost"]),
                        id=f"upgrade-{upgrade_key}-cost",
                    ),
                    f" {resource_name}",
                    classes=["shop-meta"],
                ),
                web.span(
                    "Available",
                    id=f"upgrade-{upgrade_key}-state",
                    classes=["shop-meta"],
                ),
                classes=["shop-item"],
            )
        )

    panel.append(shop_list)


# ====================================================================
# BUILD: STATS
# ====================================================================


def build_stats_panel(panel):
    stats_grid = web.div(
        web.span("Active play time"),
        web.strong("0s", id="stat-active-time"),
        web.span("Offline time processed"),
        web.strong("0s", id="stat-offline-time"),
        web.span("Manual actions"),
        web.strong("0", id="stat-manual-actions"),
        classes=["stats-grid"],
    )

    for resource_key, definition in RESOURCE_DEFS.items():
        stats_grid.append(
            web.span(f"Total {definition['name']} generated"),
            web.strong(
                "0",
                id=f"stat-total-{resource_key}",
            ),
        )

    panel.append(
        web.h2("Statistics"),
        stats_grid,
    )


# ====================================================================
# BUILD EVERYTHING ONCE
# ====================================================================


def build_ui():
    web.page["version"].textContent = f"v{GAME_VERSION}"
    build_resources_ui()
    build_tabs_ui()
    render_log()


# ====================================================================
# TAB SWITCHING
# ====================================================================


def set_active_tab(tab_key):
    global active_tab
    active_tab = tab_key

    for tab in TAB_DEFS:
        key = tab["key"]
        button = web.page[f"tab-{key}"]
        panel = web.page[f"panel-{key}"]

        if key == active_tab:
            button.classes.add("active")
            panel.classes.add("active")
        else:
            button.classes.discard("active")
            panel.classes.discard("active")


# ====================================================================
# UPDATE: RESOURCES
# ====================================================================


def update_resources_ui():
    rates = logic.production_rates()

    for resource_key in RESOURCE_DEFS:
        amount = state.game["resources"][resource_key]
        capacity = logic.resource_capacity(resource_key)
        rate = rates[resource_key]

        web.page[f"resource-{resource_key}-amount"].textContent = (
            format_number(amount)
        )
        web.page[f"resource-{resource_key}-capacity"].textContent = (
            format_number(capacity)
        )
        web.page[f"resource-{resource_key}-rate"].textContent = (
            f"+{format_number(rate)}"
        )

        percentage = 0.0
        if capacity > 0:
            percentage = (amount / capacity) * 100.0

        percentage = max(0.0, min(100.0, percentage))
        web.page[f"resource-{resource_key}-bar"].style["width"] = (
            f"{percentage:.2f}%"
        )


# ====================================================================
# UPDATE: BUILDINGS
# ====================================================================


def update_buildings_ui():
    for building_key, definition in BUILDING_DEFS.items():
        owned = int(state.game["buildings"][building_key])
        quantity, total_cost = logic.building_purchase_info(building_key)
        resource_key = definition["cost_resource"]
        available = float(state.game["resources"][resource_key])

        web.page[f"building-{building_key}-owned"].textContent = str(owned)

        if state.game["buy_amount"] == "max":
            buy_label = f"Buy max ({quantity})"
        else:
            buy_label = f"Buy {quantity}"

        web.page[f"building-{building_key}-buy-label"].textContent = buy_label

        displayed_cost = total_cost
        if quantity <= 0:
            displayed_cost = logic.building_unit_cost(building_key, owned)

        web.page[f"building-{building_key}-cost"].textContent = (
            format_number(displayed_cost)
        )

        can_afford = quantity > 0 and available >= total_cost
        web.page[f"building-{building_key}-buy"].disabled = not can_afford

    for amount in BUY_AMOUNTS:
        button = web.page[f"buy-amount-{amount}"]

        if state.game["buy_amount"] == amount:
            button.classes.add("active")
        else:
            button.classes.discard("active")


# ====================================================================
# UPDATE: UPGRADES
# ====================================================================


def update_upgrades_ui():
    for upgrade_key, definition in UPGRADE_DEFS.items():
        bought = bool(state.game["upgrades"][upgrade_key])
        resource_key = definition["cost_resource"]
        cost = float(definition["cost"])
        available = float(state.game["resources"][resource_key])

        button = web.page[f"upgrade-{upgrade_key}-buy"]
        state_text = web.page[f"upgrade-{upgrade_key}-state"]

        if bought:
            button.disabled = True
            state_text.textContent = "Purchased"
        else:
            button.disabled = available < cost
            state_text.textContent = "Available"


# ====================================================================
# UPDATE: STATS
# ====================================================================


def update_stats_ui():
    stats = state.game["stats"]

    web.page["stat-active-time"].textContent = format_time(
        stats["active_time"]
    )
    web.page["stat-offline-time"].textContent = format_time(
        stats["offline_time"]
    )
    web.page["stat-manual-actions"].textContent = str(
        stats["manual_actions"]
    )

    for resource_key in RESOURCE_DEFS:
        web.page[f"stat-total-{resource_key}"].textContent = format_number(
            stats["total_generated"][resource_key]
        )


# ====================================================================
# UPDATE EVERYTHING THAT CHANGES OFTEN
# ====================================================================


def update_ui():
    update_resources_ui()
    update_buildings_ui()
    update_upgrades_ui()
    update_stats_ui()


# ====================================================================
# EVENT LOG
# ====================================================================


def render_log():
    container = web.page["event-log"]
    container.innerHTML = ""

    if not state.game["log"]:
        container.append(
            web.p("No events yet.", classes=["log-empty"])
        )
        return

    for message in reversed(state.game["log"]):
        container.append(
            web.p(message, classes=["log-entry"])
        )


# ====================================================================
# SMALL STATUS HELPERS
# ====================================================================


def set_save_status(text):
    web.page["save-status"].textContent = text
