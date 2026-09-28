"""Unit tests for client protocol and HTTP client configuration."""
import unittest
from client.http_client import ProconHttpClient
from client.protocol import AgentKind, Direction, MatchSetup, MatchState


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

    def test_http_client_url_construction(self):
        client = ProconHttpClient(
            base_url="https://procon.ptit.edu.vn",
            match_id="test_match",
            token="dummy_token",
        )
        self.assertEqual(client.api_prefix, "https://procon.ptit.edu.vn/api/v1/matches/test_match")


if __name__ == "__main__":
    unittest.main()
