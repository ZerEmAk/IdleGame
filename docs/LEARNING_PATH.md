# Learning Path and Sources

Read in this order; build a small change after each section instead of trying to
learn the whole stack first.

## 1. Incremental math and pacing

- Anthony Pecorella, [The Math of Idle Games, Part I](https://www.gamedeveloper.com/design/the-math-of-idle-games-part-i), [Part II](https://www.gamedeveloper.com/game-platforms/the-math-of-idle-games-part-ii), and [Part III](https://www.gamedeveloper.com/design/the-math-of-idle-games-part-iii).
- GDC, [Quest for Progress: The Math and Design of Idle Games](https://www.gdcvault.com/play/1023863/Quest-for-Progress-The-Math).

Topics: exponential costs, linear/exponential production, time-to-afford,
prestige reward formulas, soft caps, source/sink tables, and milestone pacing.
Build a spreadsheet that predicts the first hour, then compare it to a real
play session.

## 2. Architecture patterns

- Robert Nystrom, [Game Programming Patterns](https://gameprogrammingpatterns.com/contents.html): Game Loop, State, Command, Observer, and Event Queue.
- Read the [Event Queue caveats](https://gameprogrammingpatterns.com/event-queue.html) before creating one global bus for everything.
- Python [typing](https://docs.python.org/3/library/typing.html) and [dataclasses](https://docs.python.org/3/library/dataclasses.html).

Topics: functional core/browser shell, data-driven registries, finite-state
machines, commands, dependency direction, validation, and stable identifiers.
Keep dictionaries while content is fluid; add `TypedDict` or dataclasses when
the schema stabilizes and editor/type-checker value exceeds conversion cost.

## 3. PyScript and the browser

- [PyScript events](https://docs.pyscript.net/2026.3.1/user-guide/events/).
- [PyScript web/DOM API](https://docs.pyscript.net/2026.3.1/api/web/).
- MDN [Pointer Events](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events), [pointer capture](https://developer.mozilla.org/en-US/docs/Web/API/Element/setPointerCapture), [requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame), and [Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API).

Topics: event propagation, generated mouse events, touch-action, pointer
capture cleanup, DOM update cost, compositor-friendly transforms, and animation
state. Keep simulation time in Python; use CSS/animation frames only to present
it.

## 4. Saving and offline progress

- MDN [Web Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API), [IndexedDB](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API), and [Page Visibility API](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API).

Topics: schema versions, ordered migrations, corrupted-save recovery, JSON-safe
state, wall-clock versus monotonic time, deterministic elapsed-time simulation,
event boundaries, and export/import. Move from `localStorage` to IndexedDB only
when save size, transactions, or multiple slots justify the complexity.

## 5. Accessibility and input

- WAI-ARIA [Tooltip Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) and [Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/).
- WCAG 2.2 [Dragging Movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements).
- MDN [`prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion).

Topics: semantic names, focus order, keyboard equivalents, visible disabled
reasons, touch targets, live regions, contrast, and motion controls. A tooltip
supplements visible information; it must not be the only place a requirement or
price appears.

## 6. Testing and release discipline

- Python [`unittest`](https://docs.python.org/3/library/unittest.html) or [pytest](https://docs.pytest.org/en/stable/).
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) for property-based economy and migration tests.
- [Playwright](https://playwright.dev/python/docs/intro) for browser flows.
- [Semantic Versioning](https://semver.org/) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Prioritize tests for atomic spending, caps, research partial payment, large-tick
equivalence, simultaneous expirations, hostile names, minigame transitions,
content reference validation, and every save migration. Then automate a real
first-Skeleton browser playthrough at desktop and mobile widths.

## Recommended practice projects

1. Add Candle Wax using only the guide in `ADDING_CONTENT.md`.
2. Add a Skeleton wax-rendering job without touching the UI.
3. Create a 30-second timed recipe using a generic process record.
4. Add save export/import and a second save slot.
5. Split one UI tab into a panel module using a build/update pair.
6. Implement a memorial ledger as an event consumer.
7. Prototype a reset on paper, then reject it unless it adds a real decision.
