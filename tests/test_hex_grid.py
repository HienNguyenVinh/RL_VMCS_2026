"""Comprehensive unit tests for Hex Grid, terrain, movement costs, coordinates, and offline simulator (Phase 2)."""
import unittest

from client.protocol import AgentKind, Direction, MatchSetup, MatchState
from env.hex_grid import HexCoord, HexGrid, TerrainType, TrafficLevel
from env.simulator import HexGridSimulator
from env.state import EnvAgent, SimulationState, UdonSpot


class TestHexGridCoordinates(unittest.TestCase):
    def setUp(self):
        self.width = 8
        self.height = 8
        self.grid = HexGrid(self.width, self.height)

    def test_coord_index_conversions(self):
        """Test conversion between (row, col) and flat index across all cells."""
        for r in range(self.height):
            for c in range(self.width):
                coord = HexCoord(r, c)
                idx = coord.to_index(self.width)
                self.assertEqual(idx, r * self.width + c)
                restored = HexCoord.from_index(idx, self.width)
                self.assertEqual(restored.row, r)
                self.assertEqual(restored.col, c)

    def test_all_6_directions_even_row(self):
        """Test all 6 directions from an interior even row cell (r=2, c=2) matching BTC geometry."""
        r, c = 2, 2  # even row
        neighbors = {
            Direction.UP_LEFT: (1, 2),
            Direction.UP_RIGHT: (1, 3),
            Direction.RIGHT: (2, 3),
            Direction.DOWN_RIGHT: (3, 3),
            Direction.DOWN_LEFT: (3, 2),
            Direction.LEFT: (2, 1),
            Direction.STAY: (2, 2),
        }
        for direction, expected in neighbors.items():
            nxt = self.grid.get_neighbor(r, c, direction)
            self.assertIsNotNone(nxt)
            self.assertEqual((nxt.row, nxt.col), expected, f"Failed for {direction.name} on even row")

    def test_all_6_directions_odd_row(self):
        """Test all 6 directions from an interior odd row cell (r=3, c=2) matching BTC geometry."""
        r, c = 3, 2  # odd row
        neighbors = {
            Direction.UP_LEFT: (2, 1),
            Direction.UP_RIGHT: (2, 2),
            Direction.RIGHT: (3, 3),
            Direction.DOWN_RIGHT: (4, 2),
            Direction.DOWN_LEFT: (4, 1),
            Direction.LEFT: (3, 1),
            Direction.STAY: (3, 2),
        }
        for direction, expected in neighbors.items():
            nxt = self.grid.get_neighbor(r, c, direction)
            self.assertIsNotNone(nxt)
            self.assertEqual((nxt.row, nxt.col), expected, f"Failed for {direction.name} on odd row")

    def test_boundaries(self):
        """Test out-of-boundary neighbor detection."""
        # Top-left corner (0, 0) - even row
        self.assertIsNone(self.grid.get_neighbor(0, 0, Direction.UP_LEFT))
        self.assertIsNone(self.grid.get_neighbor(0, 0, Direction.UP_RIGHT))
        self.assertIsNone(self.grid.get_neighbor(0, 0, Direction.LEFT))

        # Bottom-right corner (7, 7) - odd row
        self.assertIsNone(self.grid.get_neighbor(7, 7, Direction.DOWN_RIGHT))
        self.assertIsNone(self.grid.get_neighbor(7, 7, Direction.RIGHT))

    def test_cube_distance(self):
        """Test distance metric symmetry and triangle inequality."""
        c1 = HexCoord(0, 0)
        c2 = HexCoord(3, 4)
        c3 = HexCoord(2, 1)

        d12 = c1.distance_to(c2)
        d21 = c2.distance_to(c1)
        self.assertEqual(d12, d21)

        d13 = c1.distance_to(c3)
        d32 = c3.distance_to(c2)
        self.assertLessEqual(d12, d13 + d32)


class TestTerrainAndMovementCosts(unittest.TestCase):
    def setUp(self):
        # 4x4 grid with different terrain types
        self.width = 4
        self.height = 4
        # Cell 0: Plain, Cell 1: Mountain, Cell 2: Pond, Cell 3: Road
        cell_types = [
            TerrainType.PLAIN.value,
            TerrainType.MOUNTAIN.value,
            TerrainType.POND.value,
            TerrainType.ROAD.value,
        ] + [TerrainType.PLAIN.value] * 12

        traffics = [TrafficLevel.CLEAR.value] * 16
        traffics[3] = TrafficLevel.CONGESTED.value

        self.grid = HexGrid(self.width, self.height, cell_types=cell_types, traffic_levels=traffics)

    def test_passable_and_blocked_cells(self):
        self.assertTrue(self.grid.is_passable(0))  # Plain
        self.assertTrue(self.grid.is_passable(1))  # Mountain
        self.assertFalse(self.grid.is_passable(2)) # Pond is blocked!
        self.assertTrue(self.grid.is_passable(3))  # Road

    def test_movement_costs(self):
        # Plain source (Cell 0 -> Cell 1)
        step, fuel = self.grid.get_movement_cost(0, 1, AgentKind.PATROL)
        self.assertEqual(step, 2.0)
        self.assertEqual(fuel, 1)

        # Mountain source (Cell 1 -> Cell 0)
        step, fuel = self.grid.get_movement_cost(1, 0, AgentKind.PATROL)
        self.assertEqual(step, 3.0)
        self.assertEqual(fuel, 2)

        # Move to Pond (impassable destination)
        step, fuel = self.grid.get_movement_cost(0, 2, AgentKind.PATROL)
        self.assertEqual(step, float("inf"))

        # Road Congested source (Cell 3 -> Cell 0)
        step, fuel = self.grid.get_movement_cost(3, 0, AgentKind.PATROL)
        self.assertEqual(step, 4.0)
        self.assertEqual(fuel, 2)

        # Refuel agent consumes 0 patrol fuel
        step, fuel = self.grid.get_movement_cost(0, 1, AgentKind.REFUEL)
        self.assertEqual(step, 2.0)
        self.assertEqual(fuel, 0)

    def test_from_setup_parsing(self):
        setup = MatchSetup(
            match_id="test_map",
            day_steps=10,
            width=3,
            height=3,
            num_agents=2,
            cells=[
                {"type": TerrainType.PLAIN.value, "traffic": 0},
                {"type": TerrainType.MOUNTAIN.value, "traffic": 0},
                {"type": TerrainType.POND.value, "traffic": 0},
            ],
            spots=[{"pos": 5, "stock": 10, "type": 0}],
        )
        parsed_grid = HexGrid.from_setup(setup)
        self.assertEqual(parsed_grid.width, 3)
        self.assertEqual(parsed_grid.height, 3)
        self.assertEqual(parsed_grid.cell_types[1], TerrainType.MOUNTAIN.value)
        self.assertFalse(parsed_grid.is_passable(2))


class TestOfflineSimulator(unittest.TestCase):
    def test_simulator_reset_and_step(self):
        sim = HexGridSimulator(width=10, height=10, day_steps=5, num_patrol=2, num_refuel=1, seed=42)
        state = sim.reset(seed=42)

        self.assertEqual(len(state.agents), 3)
        self.assertEqual(state.step, 0)
        self.assertGreater(len(state.spots), 0)

        # Valid actions for agent 0
        valid_acts = sim.get_valid_actions(0)
        self.assertIn(Direction.STAY, valid_acts)

        # Take one step
        actions = {0: Direction.RIGHT, 1: Direction.STAY, 2: Direction.STAY}
        nxt_state, rewards, done, info = sim.step(actions)

        self.assertEqual(nxt_state.step, 1)
        self.assertIn(0, rewards)
        self.assertIn(1, rewards)
        self.assertIn(2, rewards)
        self.assertFalse(done)

    def test_100_steps_offline_simulation(self):
        """Definition of Done: Có thể chạy 100 bước offline không lỗi."""
        sim = HexGridSimulator(width=12, height=12, day_steps=20, num_patrol=3, num_refuel=1, seed=999)
        sim.reset(seed=999)

        total_steps = 0
        for day in range(5):  # 5 days x 20 steps = 100 steps
            sim.state.step = 0
            sim.state.day = day
            for step in range(20):
                # Pick valid actions for all agents
                step_actions = {}
                for a in sim.state.agents:
                    valid_a = sim.get_valid_actions(a.agent_id)
                    step_actions[a.agent_id] = valid_a[0] if valid_a else Direction.STAY

                next_state, rewards, done, info = sim.step(step_actions)
                total_steps += 1
                self.assertIsNotNone(next_state)

        self.assertEqual(total_steps, 100)


if __name__ == "__main__":
    unittest.main()
