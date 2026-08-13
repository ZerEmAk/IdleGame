# Save Format

The current schema is **v4**. `SAVE_KEY` remains stable so earlier browser saves
are found and upgraded automatically.

Important top-level fields:

```text
save_schema, resources, unlocks, grave, soul_trap_crafted,
assembly, skeletons, next_skeleton_id, upgrades, research,
activities, preferences, stats, log, next_log_id, last_save
```

Timed research:

```json
{
  "completed": {"grave_whispers": true},
  "active": {
    "key": "controlled_breath",
    "progress": 12.5,
    "knowledge_spent": 1.67,
    "paused": false
  },
  "queue": ["steady_hands"]
}
```

Assembly shuffle:

```json
{
  "started": true,
  "selected_part": null,
  "placed": {"head": false, "torso": false},
  "part_order": ["right_leg", "head", "soulgem", "left_arm", "torso", "right_arm", "left_leg"],
  "frame_ready": false
}
```

The real `placed` object always contains all seven registered part keys. The
order is saved so reloading cannot reshuffle an assembly already in progress.

Named workers:

```json
{
  "id": 3,
  "name": "Morrow",
  "remaining_seconds": 122.4,
  "maximum_seconds": 225.0,
  "job": "graves"
}
```

Structured event:

```json
{
  "id": 87,
  "timestamp": 1786623456.0,
  "game_time": 542.3,
  "category": "research",
  "tone": "success",
  "message": "Research completed: Grave Whispers.",
  "subject": "grave_whispers"
}
```

`migrations.py` advances exactly one schema at a time. v1 converts the original
single servant and three-part body into v2; v2 converts boolean research,
unnamed workers, and string logs into v3; v3 adds the persistent shuffled part
order in v4. `save.py` then merges only recognized
fields into a fresh default and normalizes numeric ranges, identifiers,
activities, names, research, and events.

Do not store DOM proxies, Python classes, functions, random generators, or
monotonic timestamps. Saved state must survive `json.dumps` and be meaningful
after a page reload. Keep real wall-clock time only in `last_save`; the runtime
loop uses `time.perf_counter()` to avoid clock adjustments.

After loading, offline progress is simulated once and immediately saved with a
new `last_save`. This prevents reloads or repeated Load clicks from claiming
the same elapsed interval more than once.
