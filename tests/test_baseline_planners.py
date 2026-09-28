"""Unit tests for Phase 3 Baseline Path Planning: BFS and Dijkstra on Hex Grid."""
import unittest

from client.protocol import AgentKind, Direction
from env.hex_grid import HexCoord, HexGrid, TerrainType, TrafficLevel
from planner.bfs import BFSPlanner, PathResult
from planner.dijkstra import DijkstraPlanner


class TestBaselinePathPlanners(unittest.TestCase):
    def setUp(self):
        # 3x3 grid setup
        self.width = 3
        self.height = 3

    def test_hand_calculated_dijkstra_vs_bfs(self):
        """Hand-calculated test case:
        Grid 3x3:
        Row 0: Cell 0 (Plain), Cell 1 (Mountain), Cell 2 (Target)
        Row 1: Cell 3 (Road Clear), Cell 4 (Road Clear), Cell 5 (Plain)
        Row 2: Cell 6, 7, 8 (Plain)
        
        Calculations:
        - Path A (Direct): 0 -> 1 -> 2
            Step 1: Cell 0 (Plain) -> Cell 1: cost = 2.0, fuel = 1
            Step 2: Cell 1 (Mountain) -> Cell 2: cost = 3.0, fuel = 2
            Total Cost = 5.0, Total Hops = 2, Total Fuel = 3
        
        - Path B (Road Detour): 0 -> 3 -> 4 -> 2
            Step 1: Cell 0 (Plain) -> Cell 3: cost = 2.0, fuel = 1
            Step 2: Cell 3 (Road Clear) -> Cell 4: cost = 1.0, fuel = 2
            Step 3: Cell 4 (Road Clear) -> Cell 2: cost = 1.0, fuel = 2
            Total Cost = 4.0, Total Hops = 3, Total Fuel = 5
        
        Expectations:
        - Dijkstra chooses Path B because Cost 4.0 < 5.0.
        - BFS chooses Path A because Hops 2 < 3.
        """
        cell_types = [
            TerrainType.PLAIN.value,     # 0
            TerrainType.MOUNTAIN.value,  # 1
            TerrainType.PLAIN.value,     # 2 (Target)
            TerrainType.ROAD.value,      # 3
            TerrainType.ROAD.value,      # 4
            TerrainType.PLAIN.value,     # 5
            TerrainType.PLAIN.value,     # 6
            TerrainType.PLAIN.value,     # 7
            TerrainType.PLAIN.value,     # 8
        ]
        traffics = [TrafficLevel.CLEAR.value] * 9
        grid = HexGrid(self.width, self.height, cell_types=cell_types, traffic_levels=traffics)

        dijkstra = DijkstraPlanner(grid)
        bfs = BFSPlanner(grid)

        res_dijkstra = dijkstra.plan(start_index=0, target_indices=2)
        res_bfs = bfs.plan(start_index=0, target_indices=2)

        # 1. Dijkstra verifies minimum cost path
        self.assertTrue(res_dijkstra.reachable)
        self.assertAlmostEqual(res_dijkstra.movement_cost, 4.0, places=2)
        self.assertEqual(res_dijkstra.path, [0, 3, 4, 2])
        self.assertEqual(res_dijkstra.route_length, 3)
        self.assertEqual(res_dijkstra.fuel_consumption, 5)

        # 2. BFS verifies minimum hop path
        self.assertTrue(res_bfs.reachable)
        self.assertEqual(res_bfs.path, [0, 1, 2])
        self.assertEqual(res_bfs.route_length, 2)
        self.assertAlmostEqual(res_bfs.movement_cost, 5.0, places=2)
        self.assertEqual(res_bfs.fuel_consumption, 3)

        # 3. Assert metrics are populated
        self.assertGreaterEqual(res_dijkstra.runtime_ms, 0.0)
        self.assertGreaterEqual(res_bfs.runtime_ms, 0.0)

    def test_blocked_cell_avoidance(self):
        """Test routing around impassable Pond."""
        # 3x3 grid where Cell 1 is a Pond (impassable)
        cell_types = [TerrainType.PLAIN.value] * 9
        cell_types[1] = TerrainType.POND.value

        grid = HexGrid(self.width, self.height, cell_types=cell_types)
        dijkstra = DijkstraPlanner(grid)
        bfs = BFSPlanner(grid)

        res_dijkstra = dijkstra.plan(0, 2)
        res_bfs = bfs.plan(0, 2)

        self.assertTrue(res_dijkstra.reachable)
        self.assertNotIn(1, res_dijkstra.path)  # Must NOT go through Pond

        self.assertTrue(res_bfs.reachable)
        self.assertNotIn(1, res_bfs.path)

    def test_unreachable_target(self):
        """Test target completely isolated by Ponds."""
        # Cell 2 isolated: neighbors of 2 are (r=0,c=1) [1] and (r=1,c=2) [5] and (r=1,c=1) [4]
        cell_types = [TerrainType.PLAIN.value] * 9
        cell_types[1] = TerrainType.POND.value
        cell_types[4] = TerrainType.POND.value
        cell_types[5] = TerrainType.POND.value

        grid = HexGrid(self.width, self.height, cell_types=cell_types)
        dijkstra = DijkstraPlanner(grid)
        bfs = BFSPlanner(grid)

        res_dijkstra = dijkstra.plan(0, 2)
        self.assertFalse(res_dijkstra.reachable)
        self.assertEqual(res_dijkstra.path, [])

        res_bfs = bfs.plan(0, 2)
        self.assertFalse(res_bfs.reachable)
        self.assertEqual(res_bfs.path, [])

    def test_fuel_constraint(self):
        """Test fuel limit constraint."""
        # Plain grid: each hop costs 1 fuel for patrol agent
        # Path from 0 to 8 takes 4 hops (4 fuel)
        grid = HexGrid(4, 4)
        dijkstra = DijkstraPlanner(grid)

        # Insufficient fuel (fuel_limit=2)
        res_no_fuel = dijkstra.plan(0, 15, fuel_limit=2)
        self.assertFalse(res_no_fuel.reachable)

        # Sufficient fuel (fuel_limit=10)
        res_with_fuel = dijkstra.plan(0, 15, fuel_limit=10)
        self.assertTrue(res_with_fuel.reachable)
        self.assertLessEqual(res_with_fuel.fuel_consumption, 10)

    def test_multi_target_selection(self):
        """Test selecting the nearest target among multiple candidates."""
        grid = HexGrid(5, 5)
        dijkstra = DijkstraPlanner(grid)

        # Start at 0. Candidates at 1 (1 hop), 12 (3 hops), 24 (6 hops)
        res = dijkstra.plan(start_index=0, target_indices=[1, 12, 24])
        self.assertTrue(res.reachable)
        self.assertEqual(res.target, 1)  # Nearest candidate picked


if __name__ == "__main__":
    unittest.main()
