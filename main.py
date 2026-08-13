from pyscript import document, when
from js import localStorage, window

import asyncio
import json
import time


# ================================================================
# GAME CONFIGURATION
# ================================================================

GAME_VERSION = "0.0.1"

SAVE_KEY = "incremental_framework_save_v1"

AUTOSAVE_SECONDS = 10


# ================================================================
# RESOURCE DEFINITIONS
# ================================================================
#
# These describe what resources EXIST.
#
# They do NOT contain the player's current amount.
#
# This distinction becomes very useful later.
# ================================================================

RESOURCE_DEFS = {

    "energy": {
        "name": "Energy",
        "base_capacity": 100.0,
    },

    "materials": {
        "name": "Materials",
        "base_capacity": 100.0,
    },

    "research": {
        "name": "Research",
        "base_capacity": 50.0,
    },

}


# ================================================================
# BUILDING DEFINITIONS
# ================================================================
#
# Again, these are definitions.
#
# The player's amount owned lives somewhere else.
# ================================================================

BUILDING_DEFS = {

    "generator": {
        "name": "Generator",

        "cost_resource": "energy",

        "base_cost": 10,
        "cost_growth": 1.15,

        "produces": {
            "energy": 1.0,
        },
    },


    "collector": {
        "name": "Collector",

        "cost_resource": "energy",

        "base_cost": 25,
        "cost_growth": 1.15,

        "produces": {
            "materials": 0.5,
        },
    },


    "laboratory": {
        "name": "Laboratory",

        "cost_resource": "materials",

        "base_cost": 30,
        "cost_growth": 1.18,

        "produces": {
            "research": 0.1,
        },
    },

}


# ================================================================
# UPGRADE DEFINITIONS
# ================================================================

UPGRADE_DEFS = {

    "generator_efficiency": {
        "name": "Efficient Generators",

        "cost_resource": "research",
        "cost": 10,
    },


    "expanded_storage": {
        "name": "Expanded Storage",

        "cost_resource": "materials",
        "cost": 50,
    },

}


# ================================================================
# CREATE A NEW GAME
# ================================================================
#
# All SAVEABLE player data goes here.
#
# Try to avoid putting HTML or UI information in this dictionary.
# ================================================================

def new_game_state():

    return {

        "resources": {
            "energy": 0.0,
            "materials": 0.0,
            "research": 0.0,
        },

        "buildings": {
            "generator": 0,
            "collector": 0,
            "laboratory": 0,
        },

        "upgrades": {
            "generator_efficiency": False,
            "expanded_storage": False,
        },

        "buy_amount": "1",

        "stats": {

            "play_time": 0.0,

            "manual_clicks": 0,

            "total_generated": {
                "energy": 0.0,
                "materials": 0.0,
                "research": 0.0,
            },

        },

        "log": [],

        "last_save": 0.0,

    }


game = new_game_state()


# ================================================================
# NUMBER FORMATTING
# ================================================================

def format_number(value):

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"

    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))

    return f"{value:.1f}"


# ================================================================
# TIME FORMATTING
# ================================================================

def format_time(seconds):

    seconds = int(seconds)

    hours = seconds // 3600

    minutes = (seconds % 3600) // 60

    seconds = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"

    if minutes > 0:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


# ================================================================
# RESOURCE CAPACITY
# ================================================================

def resource_capacity(resource_key):

    capacity = (
        RESOURCE_DEFS[resource_key]["base_capacity"]
    )

    # Example upgrade that changes storage.
    if game["upgrades"]["expanded_storage"]:

        if resource_key in (
            "energy",
            "materials",
        ):
            capacity *= 2

    return capacity


# ================================================================
# PRODUCTION
# ================================================================

def production_rates():

    rates = {
        resource_key: 0.0
        for resource_key in RESOURCE_DEFS
    }


    for building_key, owned in game["buildings"].items():

        definition = BUILDING_DEFS[building_key]

        for resource_key, amount in definition["produces"].items():

            production = owned * amount


            # Example upgrade effect.
            if (
                building_key == "generator"
                and
                game["upgrades"]["generator_efficiency"]
            ):
                production *= 2


            rates[resource_key] += production


    return rates


# ================================================================
# BUILDING COST
# ================================================================

def building_unit_cost(
    building_key,
    owned_number,
):

    definition = BUILDING_DEFS[building_key]

    base_cost = definition["base_cost"]

    growth = definition["cost_growth"]

    return round(
        base_cost
        *
        growth ** owned_number
    )


# ================================================================
# CALCULATE A PURCHASE
# ================================================================
#
# Returns:
#
#     quantity, total_cost
#
# This lets the same buying code support:
#
#     Buy 1
#     Buy 10
#     Buy Max
# ================================================================

def building_purchase_info(building_key):

    definition = BUILDING_DEFS[building_key]

    resource_key = definition["cost_resource"]

    available = game["resources"][resource_key]

    owned = game["buildings"][building_key]

    selected = game["buy_amount"]


    # ------------------------------------------------------------
    # BUY MAX
    # ------------------------------------------------------------

    if selected == "max":

        quantity = 0

        total_cost = 0


        # Safety limit.
        while quantity < 10_000:

            next_cost = building_unit_cost(
                building_key,
                owned + quantity,
            )

            if total_cost + next_cost > available:
                break

            total_cost += next_cost

            quantity += 1


        return quantity, total_cost


    # ------------------------------------------------------------
    # FIXED AMOUNT
    # ------------------------------------------------------------

    quantity = int(selected)

    total_cost = 0


    for offset in range(quantity):

        total_cost += building_unit_cost(
            building_key,
            owned + offset,
        )


    return quantity, total_cost


# ================================================================
# ADD EVENT LOG MESSAGE
# ================================================================

def add_log(message):

    timestamp = time.strftime("%H:%M:%S")

    game["log"].append(
        f"[{timestamp}] {message}"
    )


    # Do not allow the log to grow forever.
    game["log"] = game["log"][-100:]


    render_log()


# ================================================================
# RENDER EVENT LOG
# ================================================================

def render_log():

    log_element = document.querySelector(
        "#event-log"
    )

    log_element.innerHTML = ""


    for message in reversed(game["log"]):

        entry = document.createElement("p")

        entry.className = "log-entry"

        entry.innerText = message

        log_element.appendChild(entry)


# ================================================================
# UPDATE RESOURCE UI
# ================================================================

def update_resources_ui():

    rates = production_rates()


    for resource_key in RESOURCE_DEFS:

        amount = game["resources"][resource_key]

        capacity = resource_capacity(
            resource_key
        )

        rate = rates[resource_key]


        document.querySelector(
            f"#{resource_key}-amount"
        ).innerText = format_number(amount)


        document.querySelector(
            f"#{resource_key}-capacity"
        ).innerText = format_number(capacity)


        document.querySelector(
            f"#{resource_key}-rate"
        ).innerText = (
            f"+{format_number(rate)}"
        )


        # --------------------------------------------------------
        # RESOURCE BAR
        # --------------------------------------------------------

        if capacity > 0:

            percentage = (
                amount
                /
                capacity
                *
                100
            )

        else:

            percentage = 0


        percentage = max(
            0,
            min(100, percentage),
        )


        document.querySelector(
            f"#{resource_key}-bar"
        ).style.width = (
            f"{percentage}%"
        )


# ================================================================
# UPDATE BUILDING UI
# ================================================================

def update_buildings_ui():

    for building_key, definition in BUILDING_DEFS.items():

        owned = game["buildings"][building_key]

        quantity, cost = building_purchase_info(
            building_key
        )

        resource_key = definition["cost_resource"]

        available = game["resources"][resource_key]


        document.querySelector(
            f"#{building_key}-owned"
        ).innerText = str(owned)


        # --------------------------------------------------------
        # BUY LABEL
        # --------------------------------------------------------

        if game["buy_amount"] == "max":

            document.querySelector(
                f"#{building_key}-buy-label"
            ).innerText = (
                f"Buy max ({quantity})"
            )

        else:

            document.querySelector(
                f"#{building_key}-buy-label"
            ).innerText = (
                f"Buy {quantity}"
            )


        # --------------------------------------------------------
        # COST
        # --------------------------------------------------------

        if quantity > 0:

            displayed_cost = cost

        else:

            displayed_cost = building_unit_cost(
                building_key,
                owned,
            )


        document.querySelector(
            f"#{building_key}-cost"
        ).innerText = format_number(
            displayed_cost
        )


        # --------------------------------------------------------
        # BUTTON ENABLED / DISABLED
        # --------------------------------------------------------

        button = document.querySelector(
            f"[data-building='{building_key}']"
        )


        can_afford = (
            quantity > 0
            and
            available >= cost
        )


        button.disabled = not can_afford


# ================================================================
# UPDATE UPGRADE UI
# ================================================================

def update_upgrades_ui():

    for upgrade_key, definition in UPGRADE_DEFS.items():

        bought = game["upgrades"][upgrade_key]

        resource_key = definition["cost_resource"]

        cost = definition["cost"]

        available = game["resources"][resource_key]


        button = document.querySelector(
            f"#upgrade-{upgrade_key}"
        )

        state_text = document.querySelector(
            f"#{upgrade_key}-state"
        )


        if bought:

            button.disabled = True

            state_text.innerText = "Purchased"

        else:

            button.disabled = available < cost

            state_text.innerText = "Available"


# ================================================================
# UPDATE BUY QUANTITY BUTTONS
# ================================================================

def update_buy_selector_ui():

    buttons = document.querySelectorAll(
        ".buy-amount"
    )


    for button in buttons:

        button.classList.remove("active")


        if (
            str(button.dataset.amount)
            ==
            str(game["buy_amount"])
        ):

            button.classList.add("active")


# ================================================================
# UPDATE STATS
# ================================================================

def update_stats_ui():

    stats = game["stats"]


    document.querySelector(
        "#stat-play-time"
    ).innerText = format_time(
        stats["play_time"]
    )


    document.querySelector(
        "#stat-manual-clicks"
    ).innerText = str(
        stats["manual_clicks"]
    )


    document.querySelector(
        "#stat-energy-generated"
    ).innerText = format_number(
        stats["total_generated"]["energy"]
    )


    document.querySelector(
        "#stat-materials-generated"
    ).innerText = format_number(
        stats["total_generated"]["materials"]
    )


    document.querySelector(
        "#stat-research-generated"
    ).innerText = format_number(
        stats["total_generated"]["research"]
    )


# ================================================================
# UPDATE ENTIRE UI
# ================================================================

def update_ui():

    update_resources_ui()

    update_buildings_ui()

    update_upgrades_ui()

    update_buy_selector_ui()

    update_stats_ui()


# ================================================================
# MANUAL ACTION
# ================================================================

@when(
    "click",
    "#manual-action",
)
def manual_action(event):

    resource_key = "energy"

    amount = 1


    current = game["resources"][resource_key]

    capacity = resource_capacity(resource_key)


    new_amount = min(
        current + amount,
        capacity,
    )


    gained = new_amount - current


    game["resources"][resource_key] = (
        new_amount
    )


    game["stats"]["manual_clicks"] += 1


    game["stats"]["total_generated"][
        resource_key
    ] += gained


    update_ui()


# ================================================================
# BUY BUILDING
# ================================================================
#
# One handler controls ALL building buttons.
#
# event.currentTarget tells us which button was clicked.
# ================================================================

@when(
    "click",
    ".building-buy",
)
def buy_building(event):

    building_key = str(
        event.currentTarget.dataset.building
    )


    definition = BUILDING_DEFS[
        building_key
    ]


    quantity, cost = building_purchase_info(
        building_key
    )


    if quantity <= 0:
        return


    resource_key = definition[
        "cost_resource"
    ]


    if (
        game["resources"][resource_key]
        <
        cost
    ):
        return


    game["resources"][resource_key] -= cost

    game["buildings"][building_key] += (
        quantity
    )


    add_log(
        f"Bought {quantity} "
        f"{definition['name']}."
    )


    update_ui()


# ================================================================
# BUY UPGRADE
# ================================================================

@when(
    "click",
    ".upgrade-buy",
)
def buy_upgrade(event):

    upgrade_key = str(
        event.currentTarget.dataset.upgrade
    )


    if game["upgrades"][upgrade_key]:
        return


    definition = UPGRADE_DEFS[
        upgrade_key
    ]


    resource_key = definition[
        "cost_resource"
    ]

    cost = definition["cost"]


    if (
        game["resources"][resource_key]
        <
        cost
    ):
        return


    game["resources"][resource_key] -= cost

    game["upgrades"][upgrade_key] = True


    add_log(
        f"Purchased upgrade: "
        f"{definition['name']}."
    )


    update_ui()


# ================================================================
# BUY QUANTITY SELECTOR
# ================================================================

@when(
    "click",
    ".buy-amount",
)
def change_buy_amount(event):

    game["buy_amount"] = str(
        event.currentTarget.dataset.amount
    )

    update_ui()


# ================================================================
# TAB SYSTEM
# ================================================================

@when(
    "click",
    ".tab-button",
)
def change_tab(event):

    selected_tab = str(
        event.currentTarget.dataset.tab
    )


    # ------------------------------------------------------------
    # TAB BUTTONS
    # ------------------------------------------------------------

    buttons = document.querySelectorAll(
        ".tab-button"
    )


    for button in buttons:

        button.classList.remove("active")


        if (
            str(button.dataset.tab)
            ==
            selected_tab
        ):

            button.classList.add("active")


    # ------------------------------------------------------------
    # TAB CONTENT
    # ------------------------------------------------------------

    panels = document.querySelectorAll(
        ".tab-panel"
    )


    for panel in panels:

        panel.classList.remove("active")


        if (
            str(panel.dataset.panel)
            ==
            selected_tab
        ):

            panel.classList.add("active")


# ================================================================
# SAVE SYSTEM
# ================================================================

def save_game(silent=False):

    game["last_save"] = time.time()


    save_data = json.dumps(game)


    localStorage.setItem(
        SAVE_KEY,
        save_data,
    )


    document.querySelector(
        "#save-status"
    ).innerText = "Saved"


    if not silent:

        add_log("Game saved.")


# ================================================================
# MERGE SAVE DATA
# ================================================================
#
# This is useful later.
#
# Imagine version 0.2 adds a new resource.
#
# An old 0.1 save will not contain that resource.
#
# Instead of replacing the entire new game dictionary with the old
# one, we merge the old values into a fresh game state.
# ================================================================

def merge_save(
    default,
    saved,
):

    for key, saved_value in saved.items():

        if key not in default:
            continue


        default_value = default[key]


        if (
            isinstance(default_value, dict)
            and
            isinstance(saved_value, dict)
        ):

            merge_save(
                default_value,
                saved_value,
            )

        else:

            default[key] = saved_value


# ================================================================
# LOAD SYSTEM
# ================================================================

def load_game(show_message=True):

    global game


    save_data = localStorage.getItem(
        SAVE_KEY
    )


    if save_data is None:

        if show_message:
            add_log("No save exists yet.")

        return False


    save_data = str(save_data).strip()


    if save_data == "":

        localStorage.removeItem(
            SAVE_KEY
        )

        return False


    try:

        loaded_data = json.loads(
            save_data
        )


        fresh_game = new_game_state()


        merge_save(
            fresh_game,
            loaded_data,
        )


        game = fresh_game


        update_ui()

        render_log()


        if show_message:
            add_log("Save loaded.")


        return True


    except Exception as error:

        print(
            f"Could not load save: {error}"
        )

        return False


# ================================================================
# SETTINGS BUTTONS
# ================================================================

@when(
    "click",
    "#settings-button",
)
def open_settings(event):

    document.querySelector(
        "#settings-dialog"
    ).showModal()


@when(
    "click",
    "#close-settings",
)
def close_settings(event):

    document.querySelector(
        "#settings-dialog"
    ).close()


@when(
    "click",
    "#save-game",
)
def manual_save(event):

    save_game()


@when(
    "click",
    "#load-game",
)
def manual_load(event):

    load_game()


# ================================================================
# RESET GAME
# ================================================================

@when(
    "click",
    "#reset-game",
)
def reset_game(event):

    global game


    confirmed = window.confirm(
        "Delete your save and reset the game?"
    )


    if not confirmed:
        return


    localStorage.removeItem(
        SAVE_KEY
    )


    game = new_game_state()


    add_log("New game started.")


    update_ui()


    document.querySelector(
        "#settings-dialog"
    ).close()


# ================================================================
# CLEAR LOG
# ================================================================

@when(
    "click",
    "#clear-log",
)
def clear_log(event):

    game["log"] = []

    render_log()


# ================================================================
# PRODUCTION TICK
# ================================================================

def produce_resources(delta):

    rates = production_rates()


    for resource_key, rate in rates.items():

        current = game["resources"][
            resource_key
        ]

        capacity = resource_capacity(
            resource_key
        )


        wanted_amount = (
            current
            +
            rate * delta
        )


        new_amount = min(
            wanted_amount,
            capacity,
        )


        actually_generated = (
            new_amount
            -
            current
        )


        game["resources"][
            resource_key
        ] = new_amount


        game["stats"]["total_generated"][
            resource_key
        ] += actually_generated


# ================================================================
# MAIN GAME LOOP
# ================================================================

async def game_loop():

    previous_time = time.time()

    autosave_timer = 0.0

    ui_timer = 0.0


    while True:

        await asyncio.sleep(0.1)


        current_time = time.time()


        delta = (
            current_time
            -
            previous_time
        )


        previous_time = current_time


        # --------------------------------------------------------
        # GAME LOGIC
        # --------------------------------------------------------

        produce_resources(delta)


        game["stats"]["play_time"] += (
            delta
        )


        # --------------------------------------------------------
        # UI UPDATE
        #
        # Game calculations run every ~0.1 seconds.
        #
        # The UI only needs refreshing several times per second.
        # --------------------------------------------------------

        ui_timer += delta


        if ui_timer >= 0.2:

            update_ui()

            ui_timer = 0.0


        # --------------------------------------------------------
        # AUTOSAVE
        # --------------------------------------------------------

        autosave_timer += delta


        if autosave_timer >= AUTOSAVE_SECONDS:

            save_game(
                silent=True
            )

            autosave_timer = 0.0


# ================================================================
# STARTUP
# ================================================================

document.querySelector(
    "#version"
).innerText = f"v{GAME_VERSION}"


save_loaded = load_game(
    show_message=False
)


if save_loaded:

    add_log("Save loaded.")

else:

    add_log("New game started.")


update_ui()

render_log()


asyncio.create_task(
    game_loop()
)