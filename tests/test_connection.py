"""Unit tests for PROCON connection, protocol validation, HTTP client, and mock server."""
import time
import unittest

from client.http_client import ProconHttpClient
from client.mock_server import MockProconServer
from client.protocol import (
    AgentKind,
    Direction,
    MatchResult,
    MatchSetup,
    MatchState,
    ProconAuthError,
    create_idle_action_plan,
    validate_action_plan,
)
from client.runner import MatchRunner


class TestClientProtocol(unittest.TestCase):
    def test_protocol_enums(self):
        self.assertEqual(Direction.UP_LEFT, 0)
        self.assertEqual(Direction.STAY, -1)
        self.assertEqual(AgentKind.PATROL, 0)
        self.assertEqual(AgentKind.REFUEL, 1)

    def test_match_setup_parsing(self):
        sample_raw = {
            "daySteps": 20,
            "map": {"width": 10, "height": 10},
            "agents": [{"id": 0}, {"id": 1}],
            "cells": [],
            "spots": [{"pos": 15, "stock": 10}],
        }
        setup = MatchSetup.from_dict("match_123", sample_raw)
        self.assertEqual(setup.match_id, "match_123")
        self.assertEqual(setup.day_steps, 20)
        self.assertEqual(setup.width, 10)
        self.assertEqual(setup.height, 10)
        self.assertEqual(setup.num_agents, 2)

    def test_idle_action_plan_creation(self):
        plan = create_idle_action_plan(num_agents=3, day_steps=5)
        self.assertEqual(len(plan), 3)
        for p in plan:
            self.assertEqual(p, [-1, -1, -1, -1, -1])

    def test_action_plan_validation(self):
        # Valid plan
        valid_plan = [[-1, 0, 1], [2, 3, 4]]
        validate_action_plan(valid_plan, num_agents=2, day_steps=3)

        # Mismatched agent count
        with self.assertRaises(ValueError):
            validate_action_plan(valid_plan, num_agents=3, day_steps=3)

        # Exceeds daySteps
        with self.assertRaises(ValueError):
            validate_action_plan(valid_plan, num_agents=2, day_steps=2)

        # Invalid direction
        invalid_direction_plan = [[-1, 99], [0, 1]]
        with self.assertRaises(ValueError):
            validate_action_plan(invalid_direction_plan, num_agents=2, day_steps=3)


class TestMockServerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server = MockProconServer(total_days=2, start_425_count=1)
        cls.base_url = cls.mock_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()

    def test_full_match_lifecycle_smoke_test(self):
        client = ProconHttpClient(
            base_url=self.base_url,
            match_id="test_mock_match",
            token="test_bot_token",
            min_poll_interval=0.20,
        )

        # 1. GET /setup
        setup = client.get_setup()
        self.assertEqual(setup.num_agents, 3)
        self.assertEqual(setup.day_steps, 5)

        # 2. POST /assignment
        res_assign = client.post_assignment([0, 0, 1])
        self.assertEqual(res_assign.get("status"), "assigned")

        # 3. GET /start (Should handle first 425 then return 200)
        res_start = client.wait_for_start(poll_interval=0.20, max_wait_seconds=5.0)
        self.assertEqual(res_start.get("status"), "started")
        self.assertGreaterEqual(self.mock_server.start_calls, 2)

        # 4. Day 1: GET /state -> POST /actions
        state1 = client.get_state()
        self.assertEqual(state1.day, 1)
        idle_plan = create_idle_action_plan(setup.num_agents, setup.day_steps)
        res_act1 = client.post_actions(idle_plan, setup=setup)
        self.assertEqual(res_act1.get("status"), "accepted")

        # 5. Day 2: GET /state -> POST /actions
        state2 = client.get_state()
        self.assertEqual(state2.day, 2)
        res_act2 = client.post_actions(idle_plan, setup=setup)
        self.assertTrue(res_act2.get("finished"))

        # 6. GET /result
        result = client.get_result()
        self.assertTrue(result.finished)
        self.assertEqual(result.winner, "Our Team")

    def test_runner_automated_execution(self):
        # Reset server state
        self.mock_server.current_day = 1
        self.mock_server.start_calls = 0

        client = ProconHttpClient(
            base_url=self.base_url,
            match_id="runner_mock_match",
            token="test_bot_token",
            min_poll_interval=0.20,
        )
        runner = MatchRunner(client=client, poll_interval=0.20)
        outcome = runner.run()

        self.assertTrue(outcome["success"])
        self.assertGreaterEqual(outcome["days_played"], 2)


if __name__ == "__main__":
    unittest.main()
