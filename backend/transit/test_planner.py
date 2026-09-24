from .test_support import DemoDatabaseTestCase
import itertools
from django.test import SimpleTestCase
from transit.planner import plan, alternatives
from transit.network import dataset, trips, snapshot, destination_candidates


def trip(id, stops, times, route=None):
    return {"id": id, "route_id": route or id, "stops": stops, "times": times}


class PlannerTests(SimpleTestCase):
    def test_later_bus_can_arrive_first(self):
        data = [
            trip("slow", ["a", "b"], [10, 100], "line"),
            trip("fast", ["a", "b"], [20, 40], "line"),
        ]
        result = plan(data, "a", {"b": 0}, 0)
        self.assertEqual(result["arrival"], 40)
        self.assertEqual(result["legs"][0]["trip_id"], "fast")

    def test_transfer_faster_than_direct(self):
        data = [
            trip("direct", ["a", "c"], [5, 90]),
            trip("first", ["a", "b"], [10, 20]),
            trip("second", ["b", "c"], [25, 40]),
        ]
        result = plan(data, "a", {"c": 0}, 0, transfer_seconds=5)
        self.assertEqual(result["arrival"], 40)
        self.assertEqual(result["transfers"], 1)
        self.assertEqual(
            result["duration_seconds"],
            result["ride_seconds"] + result["wait_seconds"] + result["walk_seconds"],
        )

    def test_minimum_transfer_time_enforced(self):
        data = [
            trip("first", ["a", "b"], [10, 20]),
            trip("missed", ["b", "c"], [24, 30]),
            trip("valid", ["b", "c"], [25, 40]),
        ]
        self.assertEqual(
            plan(data, "a", {"c": 0}, 0, transfer_seconds=5)["arrival"], 40
        )

    def test_continuation_does_not_require_transfer(self):
        result = plan(
            [trip("one", ["a", "b", "c"], [10, 20, 30])],
            "a",
            {"c": 0},
            0,
            transfer_seconds=120,
        )
        self.assertEqual(result["arrival"], 30)
        self.assertEqual(result["transfers"], 0)
        self.assertEqual(result["legs"][0]["stops"], ["a", "b", "c"])

    def test_direct_only_excludes_connection(self):
        data = [
            trip("first", ["a", "b"], [10, 20]),
            trip("second", ["b", "c"], [25, 40]),
        ]
        self.assertIsNone(
            plan(data, "a", {"c": 0}, 0, transfer_seconds=5, max_transfers=0)
        )

    def test_no_reverse_travel_or_departed_vehicle(self):
        data = [trip("one", ["a", "b"], [10, 20])]
        self.assertIsNone(plan(data, "b", {"a": 0}, 0))
        self.assertIsNone(plan(data, "a", {"b": 0}, 11))

    def test_walk_selects_best_total_destination(self):
        data = [trip("one", ["a", "b", "c"], [10, 20, 30])]
        answer = plan(data, "a", {"b": 30, "c": 5}, 0)
        self.assertEqual(answer["destination_stop"], "c")
        self.assertEqual(answer["arrival"], 35)

    def test_same_stop_zero_duration(self):
        self.assertEqual(plan([], "a", {"a": 0}, 15)["duration_seconds"], 0)

    def test_repeated_stop_can_be_revisited(self):
        data = [trip("loop", ["a", "b", "a", "c"], [10, 20, 30, 40])]
        self.assertEqual(plan(data, "a", {"c": 0}, 21)["arrival"], 40)

    def test_alternatives_keep_later_same_line_trip(self):
        data = [
            trip("slow", ["a", "b"], [10, 100], "A"),
            trip("fast", ["a", "b"], [20, 40], "A"),
            trip("other", ["a", "b"], [5, 50], "B"),
        ]
        result = alternatives(data, "a", {"b": 0}, 0)
        self.assertEqual([r["arrival"] for r in result], [40, 50])

    def test_small_network_matches_exhaustive_search(self):
        data = [
            trip("A", ["a", "b", "d"], [5, 10, 60]),
            trip("B", ["a", "c"], [8, 15]),
            trip("C", ["c", "d"], [20, 30]),
            trip("D", ["b", "d"], [12, 25]),
        ]
        # Enumeração independente das sequências de trechos para conferir o ótimo.
        edges = [
            (t["stops"][i], t["stops"][j], t["times"][i], t["times"][j], t["id"])
            for t in data
            for i in range(len(t["stops"]))
            for j in range(i + 1, len(t["stops"]))
        ]
        for start in [0, 6, 9, 13]:
            arrivals = []
            for length in range(1, 4):
                for path in itertools.product(edges, repeat=length):
                    now, stop, last = start, "a", None
                    for a, b, dep, arr, tid in path:
                        if a != stop or dep < now + (2 if last and last != tid else 0):
                            break
                        now, stop, last = arr, b, tid
                    else:
                        if stop == "d":
                            arrivals.append(now)
            result = plan(
                data, "a", {"d": 0}, start, transfer_seconds=2, max_transfers=2
            )
            self.assertEqual(
                result["arrival"] if result else None,
                min(arrivals) if arrivals else None,
            )


class ScenarioTests(DemoDatabaseTestCase):
    def test_all_scenario_values_consistent(self):
        net = dataset()
        ids = {s["id"] for s in net["stops"]}
        for route in net["routes"]:
            self.assertTrue(set(route["stops"]) <= ids)
            self.assertEqual(len(route["durations"]), len(route["stops"]) - 1)
            self.assertTrue(all(d > 0 for d in route["durations"]))
        origin = net["stops"][0]["id"]
        result = plan(trips(), origin, {net["stops"][6]["id"]: 0}, 28800)
        self.assertEqual(result["transfers"], 1)
        self.assertEqual(result["arrival"], 8 * 3600 + 25 * 60)
        self.assertIsNone(plan(trips(), origin, {net["stops"][7]["id"]: 0}, 28800))

    def test_positions_and_arrivals_repeat(self):
        origin = dataset()["stops"][0]["id"]
        self.assertEqual(snapshot(28800, origin), snapshot(28800, origin))
        data = snapshot(28800, origin)
        self.assertGreaterEqual(len(data["lines"]), 4)
        self.assertTrue(
            all(a["wait_seconds"] >= 0 for l in data["lines"] for a in l["arrivals"])
        )
        self.assertTrue(any(v["waiting_to_depart"] for v in data["vehicles"]))
        before = {v["id"]: v for v in snapshot(29460)["vehicles"]}
        after = {v["id"]: v for v in snapshot(29475)["vehicles"]}
        self.assertTrue(
            any(
                (before[k]["lat"], before[k]["lon"])
                != (after[k]["lat"], after[k]["lon"])
                for k in before.keys() & after.keys()
            )
        )

    def test_destination_far_from_network_has_no_candidates(self):
        self.assertEqual(destination_candidates(0, 0), {})
