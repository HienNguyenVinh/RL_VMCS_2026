"""Unit tests for Dynamic Programming algorithms: Policy Evaluation, Policy Iteration, Value Iteration."""
import unittest

from client.protocol import Direction
from env.hex_grid import HexGrid, TerrainType
from planner.policy_evaluation import IterativePolicyEvaluation
from planner.policy_iteration import PolicyIteration
from planner.value_iteration import ValueIteration


class TestDPPlanners(unittest.TestCase):
    def setUp(self):
        self.width = 6
        self.height = 6
        self.grid = HexGrid(self.width, self.height)
        self.target = 15  # Target cell

    def test_policy_evaluation(self):
        evaluator = IterativePolicyEvaluation(self.grid, gamma=0.9, theta=1e-3)
        # Uniform policy
        all_actions = Direction.all_movements()
        uniform_policy = {s: {a: 1.0 / len(all_actions) for a in all_actions} for s in range(self.grid.num_cells)}
        V, sweeps = evaluator.evaluate(uniform_policy, [self.target])

        self.assertAlmostEqual(V[self.target], 50.0, places=1)
        self.assertGreater(sweeps, 0)
        self.assertGreater(len(evaluator.convergence_deltas), 0)

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

    def test_vi_and_pi_policy_agreement(self):
        """Definition of Done: VI / PI agree on optimal policy on small test grid."""
        vi = ValueIteration(self.grid, gamma=0.95, theta=1e-4)
        vi_policy, _, _ = vi.plan([self.target])

        pi = PolicyIteration(self.grid, gamma=0.95, theta=1e-4)
        pi_policy, _, _, _ = pi.plan([self.target])

        passable_cells = [s for s in range(self.grid.num_cells) if self.grid.is_passable(s)]
        agreement = sum(1 for s in passable_cells if vi_policy[s] == pi_policy[s]) / len(passable_cells)
        self.assertGreaterEqual(agreement, 0.95)

    def test_route_extraction_and_loop_detection(self):
        vi = ValueIteration(self.grid, gamma=0.9, theta=1e-3)
        policy, _, _ = vi.plan([self.target])

        start_cell = 0
        path, actions, reached = vi.extract_route(start_cell, [self.target], policy, max_steps=50)

        self.assertTrue(reached)
        self.assertEqual(path[0], start_cell)
        self.assertEqual(path[-1], self.target)
        self.assertEqual(len(actions), len(path) - 1)
        # Ensure no duplicates in path (no loops)
        self.assertEqual(len(path), len(set(path)))


if __name__ == "__main__":
    unittest.main()
