"""Unit tests for Phase 7: Hybrid MARL + DP Strategy and Baselines."""
import unittest

from client.protocol import AgentKind, Direction, validate_action_plan
from env.hex_grid import HexGrid, TerrainType
from env.simulator import HexGridSimulator
from marl.state_encoder import StateEncoder
from marl.task_allocator import TaskAllocator
from strategy import (
    DPOnlyStrategy,
    GreedyDPStrategy,
    GreedyDijkstraStrategy,
    GreedyStrategy,
    HybridMARLDPStrategy,
    IQLDijkstraStrategy,
    RandomStrategy,
)


class TestHybridStrategy(unittest.TestCase):
    """Test suite for Phase 7: MARL + DP Integration and Baselines."""

    def setUp(self):
        self.sim = HexGridSimulator(
            width=10,
            height=10,
            day_steps=8,
            num_patrol=2,
            num_refuel=1,
            num_spots=4,
            fuel_limit_patrol=30,
            fuel_limit_refuel=60,
            seed=42,
        )
        self.strategy = HybridMARLDPStrategy(
            grid=self.sim.grid,
            num_agents=3,
            weights_dir=None,  # test without pre-saved file requirement
            evaluation_mode=True,
        )

    def test_candidate_task_generation(self):
        """Test candidate task generation and feasibility detection."""
        allocator = TaskAllocator(num_spots=4)
        patrol_agent = self.sim.state.agents[0]
        tasks = allocator.get_available_tasks_for_agent(patrol_agent, self.sim.state)

        # Should have tasks for each spot + 1 standby task
        self.assertGreaterEqual(len(tasks), 5)
        standby_task = tasks[-1]
        self.assertEqual(standby_task.task_type, "STANDBY")
        self.assertTrue(standby_task.is_feasible)

    def test_dp_cost_to_go_computation(self):
        """Test computation of DP cost-to-go maps for active spots."""
        cost_maps, policy_maps = self.strategy.compute_dp_cost_to_go(self.sim.state)
        self.assertGreater(len(cost_maps), 0)

        # Cost at the spot itself should be minimal (0.0)
        for spot_pos, c_map in cost_maps.items():
            self.assertIn(spot_pos, c_map)
            self.assertAlmostEqual(c_map[spot_pos], 0.0, places=1)
            # Cost at impassable cell should be 999.0
            for idx in range(self.sim.grid.num_cells):
                if not self.sim.grid.is_passable(idx):
                    self.assertEqual(c_map[idx], 999.0)

    def test_state_encoder_with_cost_to_go(self):
        """Test StateEncoder integrates DP cost-to-go into discrete features."""
        encoder = StateEncoder()
        agent = self.sim.state.agents[0]
        cost_maps, _ = self.strategy.compute_dp_cost_to_go(self.sim.state)

        agent_costs = {s_pos: c_map.get(agent.pos, 99.0) for s_pos, c_map in cost_maps.items()}
        state_key = encoder.encode_agent_state(
            agent=agent,
            sim_state=self.sim.state,
            cost_to_go=agent_costs,
        )

        self.assertIsInstance(state_key, tuple)
        self.assertEqual(len(state_key), 5)
        # Agent kind, fuel bucket, cost bucket 1, cost bucket 2, teammate act
        self.assertEqual(state_key[0], agent.kind.value)
        self.assertIn(state_key[1], [0, 1, 2])
        self.assertIn(state_key[2], [0, 1, 2, 3])
        self.assertIn(state_key[3], [0, 1, 2, 3])

    def test_fuel_validation_and_truncation(self):
        """Test that low fuel truncates route and pads with STAY (-1) without exceeding fuel."""
        # Set agent 0 to very low fuel (1 unit, Plain costs 1 fuel per move for Patrol)
        self.sim.state.agents[0].fuel = 1

        plan = self.strategy.plan_day(self.sim.state, day_steps=self.sim.day_steps)

        # Plan must be valid
        validate_action_plan(plan, len(self.sim.state.agents), self.sim.day_steps)
        self.assertLessEqual(len(plan[0]), self.sim.day_steps)

        # At most 1 movement step possible with 1 fuel
        move_steps = [a for a in plan[0] if a >= 0]
        self.assertLessEqual(len(move_steps), 1)


    def test_impossible_target_detection_and_fallback(self):
        """Test detection of impossible targets and automatic fallback."""
        # Force a spot to be in a pond (impassable)
        pond_cell = -1
        for idx in range(self.sim.grid.num_cells):
            if self.sim.grid.cell_types[idx] == TerrainType.POND.value:
                pond_cell = idx
                break

        if pond_cell != -1:
            self.sim.state.spots[0].pos = pond_cell
            # Strategy must handle impassable target gracefully via fallback
            plan = self.strategy.plan_day(self.sim.state, day_steps=self.sim.day_steps)
            validate_action_plan(plan, len(self.sim.state.agents), self.sim.day_steps)

    def test_all_baselines_produce_valid_plans(self):
        """Test that Random, Greedy, Greedy-Dijkstra, Greedy-DP, DP-Only, and IQL-Dijkstra all produce valid plans."""
        strategies = {
            "Random": RandomStrategy(self.sim.grid, seed=123),
            "Greedy": GreedyStrategy(self.sim.grid),
            "Greedy-Dijkstra": GreedyDijkstraStrategy(self.sim.grid),
            "Greedy-DP": GreedyDPStrategy(self.sim.grid),
            "DP-Only": DPOnlyStrategy(self.sim.grid),
            "IQL-Dijkstra": IQLDijkstraStrategy(self.sim.grid, num_agents=3, weights_dir=None),
            "Hybrid-MARL-DP": self.strategy,
        }

        for name, strat in strategies.items():
            plan = strat.plan_day(self.sim.state, self.sim.day_steps)
            self.assertEqual(len(plan), len(self.sim.state.agents), f"Strategy {name} agent count mismatch")
            for i, p in enumerate(plan):
                self.assertLessEqual(
                    len(p),
                    self.sim.day_steps,
                    f"Strategy {name} agent {i} step count exceeds day_steps: {len(p)} vs {self.sim.day_steps}",
                )
            # Should pass validation without error
            validate_action_plan(plan, len(self.sim.state.agents), self.sim.day_steps)

    def test_offline_multi_day_execution(self):
        """Test full multi-day simulation stepping with Hybrid strategy."""
        num_days = 3
        total_score = 0

        for day in range(num_days):
            plan = self.strategy.plan_day(self.sim.state, self.sim.day_steps)
            for step_idx in range(self.sim.day_steps):
                step_actions = {
                    a_id: (plan[a_id][step_idx] if step_idx < len(plan[a_id]) and plan[a_id][step_idx] >= 0 else Direction.STAY.value)
                    for a_id in range(len(self.sim.state.agents))
                }
                next_state, rewards, done, info = self.sim.step(step_actions)
                self.assertIsNotNone(next_state)

            total_score = self.sim.state.total_team_score
            self.sim.state.day += 1
            self.sim.state.step = 0

        self.assertGreaterEqual(total_score, 0)


if __name__ == "__main__":
    unittest.main()
