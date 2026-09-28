"""Unit tests for Phase 9: Real Server / Mock Lifecycle, MatchRunner, and Match Automation."""
import json
from pathlib import Path
import unittest

from client.http_client import ProconHttpClient
from client.mock_server import MockProconServer
from client.protocol import AgentKind, Direction, MatchSetup, MatchState, validate_action_plan
from client.runner import MatchRunner
from env.hex_grid import HexGrid
from env.state import SimulationState
from strategy.hybrid import HybridMARLDPStrategy


class TestRealServerPhase9(unittest.TestCase):
    """Test suite for Phase 9 Server Protocol, MatchRunner robustness, and logging."""

    @classmethod
    def setUpClass(cls):
        # Start a local Mock PROCON Server simulating HTTP 425 on start and 2 match days
        cls.mock_server = MockProconServer(total_days=2, start_425_count=1)
        cls.base_url = cls.mock_server.start()
        cls.match_id = "test_match_phase9_001"
        cls.token = "test_bearer_token_123"

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()

    def setUp(self):
        self.client = ProconHttpClient(
            base_url=self.base_url,
            match_id=self.match_id,
            token=self.token,
            min_poll_interval=0.20,
        )

    def test_setup_and_state_parsing_into_simulation_state(self):
        """Test that server MatchSetup and MatchState parse cleanly into SimulationState."""
        setup = self.client.get_setup()
        self.assertEqual(setup.width, 10)
        self.assertEqual(setup.height, 10)
        self.assertEqual(setup.day_steps, 5)

        # Wait past 425
        self.client.wait_for_start(poll_interval=0.25)

        state = self.client.get_state()
        self.assertEqual(state.day, 1)
        self.assertEqual(len(state.agents), 3)

        sim_state = SimulationState.from_match(setup, state)
        self.assertIsNotNone(sim_state)
        self.assertEqual(sim_state.grid.width, 10)
        self.assertEqual(len(sim_state.agents), 3)
        self.assertEqual(len(sim_state.spots), 2)

    def test_strategy_fallback_on_exception(self):
        """Test that MatchRunner catches planner exceptions and falls back to safe action plan."""
        runner = MatchRunner(client=self.client)

        setup = MatchSetup(
            match_id="test", day_steps=5, width=10, height=10, num_agents=2
        )
        state = MatchState(day=1)

        # Defective strategy that raises an unhandled error
        def buggy_strategy(s, st):
            raise RuntimeError("Unexpected planner crash!")

        runner.strategy = buggy_strategy
        actions, latency_ms, source = runner._execute_strategy(setup, state)

        # Must not crash! Must produce valid idle actions
        self.assertEqual(len(actions), 2)
        self.assertEqual(len(actions[0]), 5)
        self.assertTrue(all(a == Direction.STAY.value for a in actions[0]))
        self.assertTrue("fallback_error" in source)
        validate_action_plan(actions, 2, 5)

    def test_duplicate_day_prevention(self):
        """Test that runner prevents duplicate actions for the same day."""
        runner = MatchRunner(client=self.client)
        runner.last_acted_day = 3

        state = MatchState(day=3)
        # Same day should be skipped
        self.assertLessEqual(state.day, runner.last_acted_day)

    def test_full_match_lifecycle_with_hybrid_strategy_and_logging(self):
        """Test full match run through MockProconServer with HybridMARLDPStrategy and log saving."""
        # Create fresh mock server for complete clean match
        server = MockProconServer(total_days=2, start_425_count=1)
        base_url = server.start()

        try:
            client = ProconHttpClient(
                base_url=base_url,
                match_id="test_full_match_002",
                token="token_456",
                min_poll_interval=0.20,
            )

            # Auto-initialized HybridMARLDPStrategy
            runner = MatchRunner(
                client=client,
                strategy=None,  # will auto-initialize from setup
                poll_interval=0.25,
                log_dir="logs/matches",
            )

            summary = runner.run()

            # Verify outcome
            self.assertTrue(summary["success"])
            self.assertEqual(summary["match_id"], "test_full_match_002")
            self.assertGreaterEqual(summary["days_played"], 2)
            self.assertIn("log_file", summary)

            # Check that log file exists and is valid JSON
            log_path = Path(summary["log_file"])
            self.assertTrue(log_path.exists())

            with open(log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)

            self.assertEqual(log_data["match_id"], "test_full_match_002")
            self.assertIn("telemetry", log_data)
            self.assertGreaterEqual(len(log_data["telemetry"]), 2)

            # Check telemetry structure
            first_day_log = log_data["telemetry"][0]
            self.assertEqual(first_day_log["day"], 1)
            self.assertIn("planning_latency_ms", first_day_log)
            self.assertIn("actions", first_day_log)
            self.assertIn("server_response", first_day_log)

        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
