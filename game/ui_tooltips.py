"""One accessible tooltip controller for all data-driven UI elements."""

from pyscript import web, when, window


_installed = False


def text_for(definition, details=None):
    lines = [definition.get("description", "")]
    lines.extend(item for item in (details or []) if item)
    flavor = definition.get("flavor")
    if flavor:
        lines.append(f"“{flavor}”")
    return "\n".join(item for item in lines if item)


def attach(element, definition=None, *, text=None, details=None):
    """Attach one tooltip while keeping essential information in the card."""

    tooltip_text = text if text is not None else text_for(definition or {}, details)
    if not tooltip_text:
        return element
    element.setAttribute("data-tooltip", tooltip_text)
    element.setAttribute("aria-describedby", "game-tooltip")
    return element


def _show(event):
    try:
        target = event.target.closest("[data-tooltip]") if event.target else None
        tooltip_text = target.getAttribute("data-tooltip")
    except (AttributeError, TypeError):
        return
    tooltip = web.page["game-tooltip"]
    tooltip.textContent = tooltip_text
    tooltip.hidden = False
    tooltip.setAttribute("aria-hidden", "false")
    rect = target.getBoundingClientRect()
    tooltip_rect = tooltip.getBoundingClientRect()
    left = min(float(window.innerWidth) - float(tooltip_rect.width) - 10, max(10, float(rect.left)))
    top = float(rect.bottom) + 8
    if top + float(tooltip_rect.height) > float(window.innerHeight) - 10:
        top = max(10, float(rect.top) - float(tooltip_rect.height) - 8)
    tooltip.style["left"] = f"{left}px"
    tooltip.style["top"] = f"{top}px"


def _hide(event):
    tooltip = web.page["game-tooltip"]
    tooltip.hidden = True
    tooltip.setAttribute("aria-hidden", "true")


def install():
    global _installed
    if _installed:
        return
    _installed = True
    when("mouseover", window.document)(_show)
    when("focusin", window.document)(_show)
    when("mouseout", window.document)(_hide)
    when("focusout", window.document)(_hide)
    when("keydown", window.document)(_escape_handler)


def _escape_handler(event):
    if str(event.key) == "Escape":
        _hide(event)
