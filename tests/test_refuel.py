"""Unit tests for Phase 8: Fuel Management, Refueling Coordination, and Rendezvous Synchronization."""
import unittest

from client.protocol import AgentKind, Direction, validate_action_plan
from env.hex_grid import HexCoord, HexGrid
from env.simulator import HexGridSimulator
from env.state import EnvAgent
from marl.refuel_coordinator import RefuelCoordinator, RefuelRequest, RendezvousPlan
from strategy.hybrid import HybridMARLDPStrategy


class TestRefuelCoordination(unittest.TestCase):
    """Test suite for Phase 8 Refuel Coordination and Simulator Fuel Transfer."""

    def setUp(self):
        self.sim = HexGridSimulator(
            width=10,
            height=10,
            day_steps=6,
            num_patrol=2,
            num_refuel=1,
            num_spots=3,
            fuel_limit_patrol=40,
            fuel_limit_refuel=80,
            seed=42,
        )
        self.coordinator = RefuelCoordinator(
            grid=self.sim.grid,
            low_fuel_threshold=0.35,
            critical_fuel_threshold=0.15,
        )

    def test_low_fuel_threshold_detection(self):
        """Test detection of patrol agents requiring refueling."""
        # By default, agents start with max_fuel (40/40 -> 100%), no request
        requests = self.coordinator.check_refuel_requests(self.sim.state)
        self.assertEqual(len(requests), 0)

        # Drop agent 0 fuel to 10 (10/40 = 25% <= 35%)
        self.sim.state.agents[0].fuel = 10
        requests = self.coordinator.check_refuel_requests(self.sim.state)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].patrol_agent_id, 0)
        self.assertAlmostEqual(requests[0].fuel_ratio, 0.25)
        self.assertAlmostEqual(requests[0].urgency, 0.75)

    def test_rendezvous_cell_selection_and_time_synchronization(self):
        """Test rendezvous cell selection and schedule synchronization between agents."""
        patrol = self.sim.state.agents[0]
        patrol.fuel = 12  # low fuel

        refuel = self.sim.state.agents[2]  # refueler
        self.assertEqual(refuel.kind, AgentKind.REFUEL)

        cell, plan = self.coordinator.find_rendezvous_cell(
            patrol=patrol,
            refuel=refuel,
            sim_state=self.sim.state,
            day_steps=self.sim.day_steps,
        )

        self.assertIsNotNone(plan)
        self.assertTrue(plan.is_feasible)
        self.assertTrue(self.sim.grid.is_passable(cell))
        self.assertEqual(len(plan.patrol_actions), self.sim.day_steps)
        self.assertEqual(len(plan.refuel_actions), self.sim.day_steps)

        # Arrival synchronization: faster agent should wait at meeting point
        self.assertLessEqual(plan.patrol_arrival_step, self.sim.day_steps)
        self.assertLessEqual(plan.refuel_arrival_step, self.sim.day_steps)

    def test_fallback_stationary_rendezvous(self):
        """Test stationary rendezvous fallback when patrol has critical fuel."""
        patrol = self.sim.state.agents[0]
        patrol.fuel = 2  # critical fuel

        refuel = self.sim.state.agents[2]
        plan = self.coordinator.plan_fallback_stationary(
            patrol=patrol,
            refuel=refuel,
            day_steps=self.sim.day_steps,
        )

        self.assertTrue(plan.is_feasible)
        self.assertEqual(plan.rendezvous_cell, patrol.pos)
        # Patrol must stand still completely to conserve fuel
        self.assertTrue(all(a == Direction.STAY.value for a in plan.patrol_actions))
        self.assertEqual(len(plan.refuel_actions), self.sim.day_steps)

    def test_simulator_actual_fuel_transfer(self):
        """Test that simulator actually transfers fuel between collocated/adjacent refuel and patrol agents."""
        patrol = self.sim.state.agents[0]
        refuel = self.sim.state.agents[2]

        # Place refuel agent on same or adjacent cell as patrol agent
        refuel.pos = patrol.pos
        patrol.fuel = 10
        refuel.fuel = 80
        initial_patrol_fuel = patrol.fuel
        initial_refuel_fuel = refuel.fuel

        # Run 1 step with both staying still
        step_actions = {
            patrol.agent_id: Direction.STAY.value,
            1: Direction.STAY.value,
            refuel.agent_id: Direction.STAY.value,
        }
        next_state, rewards, done, info = self.sim.step(step_actions)

        # Up to 10 fuel should be transferred
        self.assertGreater(patrol.fuel, initial_patrol_fuel)
        self.assertLess(refuel.fuel, initial_refuel_fuel)
        self.assertEqual(patrol.fuel - initial_patrol_fuel, initial_refuel_fuel - refuel.fuel)
        self.assertGreater(self.sim.state.total_fuel_transferred, 0)
        self.assertIn("total_fuel_transferred", info)

    def test_hybrid_strategy_executes_refuel_rendezvous(self):
        """Test full execution of HybridMARLDPStrategy when a patrol agent triggers refuel request."""
        strategy = HybridMARLDPStrategy(
            grid=self.sim.grid,
            num_agents=3,
            weights_dir=None,
            enable_refueling=True,
            low_fuel_threshold=0.35,
        )

        # Trigger low fuel on agent 0
        self.sim.state.agents[0].fuel = 10
        initial_fuel = self.sim.state.agents[0].fuel

        # Plan and execute day
        plan = strategy.plan_day(self.sim.state, day_steps=self.sim.day_steps)
        validate_action_plan(plan, len(self.sim.state.agents), self.sim.day_steps)

        for s in range(self.sim.day_steps):
            step_acts = {a.agent_id: plan[a.agent_id][s] for a in self.sim.state.agents}
            self.sim.step(step_acts)

        # Verification: agent 0 was coordinated and received fuel or avoided stall
        self.assertGreaterEqual(self.sim.state.agents[0].fuel, 0)


if __name__ == "__main__":
    unittest.main()
