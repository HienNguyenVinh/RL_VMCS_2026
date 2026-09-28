"""Unit tests for Dynamic Programming algorithms (Value Iteration & Policy Iteration)."""
import unittest
from client.protocol import Direction
from env.hex_grid import HexGrid
from planner.policy_iteration import PolicyIteration
from planner.value_iteration import ValueIteration


class TestDPPlanners(unittest.TestCase):
    def setUp(self):
        self.width = 6
        self.height = 6
        self.grid = HexGrid(self.width, self.height)
        self.target = 15  # Target cell

    def test_value_iteration_converges(self):
        vi = ValueIteration(self.grid, gamma=0.9, theta=1e-3)
        policy, values, iters = vi.plan([self.target])

        # Target cell value should be target reward (50.0)
        self.assertAlmostEqual(values[self.target], 50.0, places=1)
        self.assertGreater(iters, 0)
        # Policy on target should be STAY
        self.assertEqual(policy[self.target], Direction.STAY)

    def test_policy_iteration_converges(self):
        pi = PolicyIteration(self.grid, gamma=0.9, theta=1e-3)
        policy, values, iters, total_sweeps = pi.plan([self.target])

        self.assertAlmostEqual(values[self.target], 50.0, places=1)
        self.assertGreater(iters, 0)
        self.assertGreater(total_sweeps, 0)


if __name__ == "__main__":
    unittest.main()
