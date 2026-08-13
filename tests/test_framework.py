"""Regression tests for framework contracts that do not require a browser."""

import ast
from pathlib import Path
import unittest

from game import economy, logic, migrations, requirements, research, state, validation
from game.content import PART_DEFS, RESEARCH_DEFS, SEANCE_SIGIL_DEFS, TAB_DEFS, UPGRADE_DEFS
from game.visuals import PLACEHOLDER_ASSETS, TAB_VISUALS


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        state.reset_state()

    def test_content_registries_validate(self):
        self.assertTrue(validation.validate_content())

    def test_pyscript_uses_keyword_safe_input_factory(self):
        """PyScript exposes the HTML input factory as ``web.input_``."""

        source = (Path(__file__).parents[1] / "game" / "ui.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        web_factories = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "web"
        ]
        self.assertIn("input_", web_factories)
        self.assertNotIn("input", web_factories)

    def test_raw_drag_nodes_and_wrapped_art_use_their_native_apis(self):
        root = Path(__file__).parents[1]
        ui_source = (root / "game" / "ui.py").read_text(encoding="utf-8")
        component_source = (root / "game" / "ui_components.py").read_text(encoding="utf-8")
        self.assertIn('style.setProperty("left"', ui_source)
        self.assertIn('slot.classList.add("part-snapped")', ui_source)
        self.assertIn('node.style["--art-image"]', component_source)
        self.assertNotIn("node.style.setProperty", component_source)

    def test_opening_loop_and_editable_worker_name(self):
        logic.add_resource("mana", 100)
        logic.update_unlocks()
        for _ in range(15):
            logic.dig_grave()
        logic.add_resource("bones", 100)
        self.assertTrue(logic.craft_soul_trap())
        logic.add_resource("souls", 1)
        self.assertTrue(logic.start_assembly())
        for part in PART_DEFS:
            self.assertTrue(logic.place_assembly_part(part, part))
        self.assertTrue(logic.summon_skeleton())
        worker = state.game["skeletons"][0]
        self.assertTrue(worker["name"])
        self.assertTrue(logic.rename_skeleton(worker["id"], "  Sir   Rattle\x00  "))
        self.assertEqual(worker["name"], "Sir Rattle")

    def test_assembly_tray_shuffle_is_saved_and_validated(self):
        state.game["unlocks"]["assembly"] = True
        state.game["resources"]["bones"] = 100
        self.assertTrue(logic.start_assembly())
        order = state.game["assembly"]["part_order"]
        self.assertCountEqual(order, PART_DEFS)
        self.assertNotEqual(order, list(PART_DEFS))

    def test_tab_visuals_and_placeholder_assets_are_complete(self):
        self.assertEqual(set(TAB_VISUALS), {tab["key"] for tab in TAB_DEFS})
        root = Path(__file__).parents[1]
        for relative_path in PLACEHOLDER_ASSETS.values():
            self.assertTrue((root / relative_path).is_file(), relative_path)

    def test_research_drains_continuously_and_pauses(self):
        state.game["resources"]["knowledge"] = 0.5
        self.assertTrue(research.plan("grave_whispers"))
        research.advance(20)
        active = state.game["research"]["active"]
        self.assertAlmostEqual(active["progress"], 5.0, places=5)
        self.assertAlmostEqual(state.game["resources"]["knowledge"], 0.0, places=7)
        self.assertTrue(active["paused"])
        state.game["resources"]["knowledge"] = 1.5
        research.advance(20)
        self.assertTrue(state.game["research"]["completed"]["grave_whispers"])
        self.assertIsNone(state.game["research"]["active"])

    def test_excavation_and_seance_feed_main_economy(self):
        state.game["stats"]["graves_opened"] = 1
        self.assertTrue(logic.start_excavation())
        excavation = state.game["activities"]["excavation"]
        excavation["elapsed"] = 0.4
        excavation["target"] = logic.excavation_marker()
        self.assertTrue(logic.resolve_excavation())
        self.assertGreater(state.game["resources"]["grave_dust"], 0)
        self.assertGreaterEqual(state.game["resources"]["relics"], 1)

        state.game["soul_trap_crafted"] = True
        state.game["resources"]["mana"] = 100
        self.assertTrue(logic.start_seance())
        seance = state.game["activities"]["seance"]
        seance["phase"] = "input"
        for sigil in list(seance["sequence"]):
            logic.choose_seance_sigil(sigil)
        self.assertEqual(seance["phase"], "result")
        self.assertGreater(state.game["resources"]["ectoplasm"], 0)

    def test_minigame_difficulty_and_exact_excavation_stop(self):
        self.assertEqual(len(SEANCE_SIGIL_DEFS), 16)
        state.game["soul_trap_crafted"] = True
        state.game["resources"]["mana"] = 100
        self.assertTrue(logic.start_seance())
        self.assertEqual(len(state.game["activities"]["seance"]["sequence"]), 6)

        state.game["stats"]["graves_opened"] = 1
        self.assertTrue(logic.start_excavation())
        target = state.game["activities"]["excavation"]["target"]
        self.assertTrue(logic.resolve_excavation(target))
        excavation = state.game["activities"]["excavation"]
        self.assertFalse(excavation["active"])
        self.assertAlmostEqual(excavation["stopped_marker"], target)
        self.assertEqual(excavation["result"], "perfect")

    def test_v2_save_migrates_structured_research_workers_and_log(self):
        old = {
            "save_schema": 2,
            "research": {"grave_whispers": True},
            "skeletons": [{"id": 1, "remaining_seconds": 20, "job": "mana"}],
            "log": ["[12:00:00] Legacy event."],
        }
        migrated = migrations.migrate(old, 3)
        self.assertTrue(migrated["research"]["completed"]["grave_whispers"])
        self.assertTrue(migrated["skeletons"][0]["name"])
        self.assertEqual(migrated["log"][0]["category"], "system")

    def test_v3_save_adds_persistent_assembly_order(self):
        old = {"save_schema": 3, "assembly": {"started": True}}
        migrated = migrations.migrate(old, 4)
        self.assertEqual(migrated["save_schema"], 4)
        self.assertEqual(migrated["assembly"]["part_order"], list(PART_DEFS))

    def test_atomic_spending_and_unknown_requirements_fail_closed(self):
        state.game["resources"]["mana"] = 5
        state.game["resources"]["bones"] = 2
        self.assertFalse(economy.spend({"mana": 4, "bones": 3}))
        self.assertEqual(state.game["resources"]["mana"], 5)
        self.assertEqual(state.game["resources"]["bones"], 2)
        self.assertFalse(requirements.requirement_met({"type": "typo_unlock"}))

    def test_research_queue_promotes_and_completes_in_order(self):
        state.game["research"]["completed"]["grave_whispers"] = True
        state.game["resources"]["knowledge"] = 20
        self.assertTrue(research.plan("controlled_breath"))
        self.assertTrue(research.plan("bone_preservation"))
        self.assertEqual(state.game["research"]["queue"], ["bone_preservation"])
        research.advance(70)
        self.assertTrue(state.game["research"]["completed"]["controlled_breath"])
        self.assertTrue(state.game["research"]["completed"]["bone_preservation"])
        self.assertIsNone(state.game["research"]["active"])

    def test_large_tick_matches_small_ticks_for_stable_rates(self):
        def scenario(ticks):
            state.reset_state()
            state.game["resources"]["knowledge"] = 10
            state.game["skeletons"] = [{
                "id": 1,
                "name": "Morrow",
                "remaining_seconds": 100,
                "maximum_seconds": 100,
                "job": "mana",
            }]
            research.plan("grave_whispers")
            for seconds in ticks:
                logic.advance_game(seconds)
            active = state.game["research"]["active"]
            return (
                state.game["resources"]["mana"],
                state.game["resources"]["knowledge"],
                20.0 if active is None else active["progress"],
                state.game["skeletons"][0]["remaining_seconds"],
            )

        one_tick = scenario([20])
        small_ticks = scenario([1] * 20)
        for left, right in zip(one_tick, small_ticks):
            self.assertAlmostEqual(left, right, places=6)

    def test_large_tick_matches_live_steps_near_resource_cap(self):
        """Research consumption and worker production share bounded steps."""

        def scenario(ticks):
            state.reset_state()
            state.game["research"]["completed"]["grave_whispers"] = True
            state.game["resources"]["knowledge"] = 99.5
            state.game["skeletons"] = [{
                "id": 1,
                "name": "Scribe",
                "remaining_seconds": 100,
                "maximum_seconds": 100,
                "job": "study",
            }]
            self.assertTrue(research.plan("controlled_breath"))
            for seconds in ticks:
                logic.advance_game(seconds)
            return (
                state.game["resources"]["knowledge"],
                state.game["research"]["completed"]["controlled_breath"],
            )

        one_tick = scenario([30])
        live_steps = scenario([1] * 30)
        self.assertAlmostEqual(one_tick[0], live_steps[0], places=6)
        self.assertEqual(one_tick[1], live_steps[1])

    def test_loaded_research_at_exact_duration_completes(self):
        definition = RESEARCH_DEFS["grave_whispers"]
        state.game["research"]["active"] = {
            "key": "grave_whispers",
            "progress": definition["duration"],
            "knowledge_spent": definition["knowledge_cost"],
            "paused": True,
        }
        research.advance(0.1)
        self.assertTrue(state.game["research"]["completed"]["grave_whispers"])
        self.assertIsNone(state.game["research"]["active"])

    def test_multiple_workers_expire_once_in_same_tick(self):
        state.game["skeletons"] = [
            {"id": 1, "name": "Ash", "remaining_seconds": 1, "maximum_seconds": 10, "job": "mana"},
            {"id": 2, "name": "Hush", "remaining_seconds": 2, "maximum_seconds": 10, "job": "mana"},
        ]
        logic.advance_game(5)
        self.assertEqual(state.game["skeletons"], [])
        self.assertEqual(state.game["stats"]["servants_expired"], 2)
        self.assertEqual(len([event for event in state.game["log"] if event["category"] == "skeleton"]), 2)

    def test_all_catalogue_costs_fit_eventual_storage(self):
        state.game["upgrades"] = {key: True for key in UPGRADE_DEFS}
        state.game["research"]["completed"] = {key: True for key in RESEARCH_DEFS}
        for catalogue in (UPGRADE_DEFS, RESEARCH_DEFS):
            for key, definition in catalogue.items():
                costs = definition.get("cost", definition.get("start_cost", {}))
                for resource, amount in costs.items():
                    self.assertLessEqual(
                        float(amount),
                        logic.resource_capacity(resource),
                        f"{key} costs more {resource} than can ever be stored",
                    )


if __name__ == "__main__":
    unittest.main()
