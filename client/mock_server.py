"""Mock PROCON Server for offline protocol verification and smoke testing."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MockProconServer:
    """Simulates the PTIT PROCON 2026 HTTP API on localhost for testing."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        total_days: int = 2,
        start_425_count: int = 1,
        enforce_rate_limit: bool = False,
    ):
        self.host = host
        self.port = port
        self.total_days = total_days
        self.start_425_count = start_425_count
        self.enforce_rate_limit = enforce_rate_limit

        self.start_calls = 0
        self.current_day = 1
        self.assignment_received = False
        self.actions_received: list = []
        self.last_req_time = 0.0

        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        if self.server:
            actual_port = self.server.server_address[1]
            return f"http://{self.host}:{actual_port}"
        return f"http://{self.host}:{self.port}"

    def start(self) -> str:
        mock_instance = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default std logging

            def _send_json(self, status: int, data: Any):
                body = json.dumps(data).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                # Rate limit check if enabled
                now = time.monotonic()
                if mock_instance.enforce_rate_limit and (now - mock_instance.last_req_time < 0.20):
                    mock_instance.last_req_time = now
                    self.send_response(429)
                    self.send_header("Retry-After", "0.25")
                    self.end_headers()
                    self.wfile.write(b'{"error": "Too Many Requests"}')
                    return
                mock_instance.last_req_time = now

                path = self.path.split("?")[0]

                if path.endswith("/setup"):
                    setup_data = {
                        "daySteps": 5,
                        "map": {"width": 10, "height": 10},
                        "agents": [{"id": 0}, {"id": 1}, {"id": 2}],
                        "fuelLimits": {"patrol": 50, "refuel": 100},
                        "cells": [],
                        "spots": [
                            {"pos": 12, "stock": 10, "type": 0},
                            {"pos": 45, "stock": 15, "type": 1},
                        ],
                    }
                    self._send_json(200, setup_data)

                elif path.endswith("/start"):
                    mock_instance.start_calls += 1
                    if mock_instance.start_calls <= mock_instance.start_425_count:
                        # Return HTTP 425 Too Early to test retry handling
                        self._send_json(425, {"status": "match_not_ready"})
                    else:
                        self._send_json(200, {"status": "started"})

                elif path.endswith("/state"):
                    state_data = {
                        "day": mock_instance.current_day,
                        "agents": [
                            {"kind": 0, "pos": 0, "fuel": 50, "score": 10},
                            {"kind": 0, "pos": 10, "fuel": 45, "score": 5},
                            {"kind": 1, "pos": 20, "fuel": 90, "score": 0},
                        ],
                        "others": [],
                        "traffics": [0] * 100,
                    }
                    self._send_json(200, state_data)

                elif path.endswith("/result"):
                    result_data = {
                        "finished": True,
                        "winner": "Our Team",
                        "teamScores": {"our_team": 120, "opponent": 80},
                    }
                    self._send_json(200, result_data)

                else:
                    self._send_json(404, {"error": "Not Found"})

            def do_POST(self):
                content_len = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
                try:
                    data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    data = None

                path = self.path.split("?")[0]

                if path.endswith("/assignment"):
                    mock_instance.assignment_received = True
                    self._send_json(200, {"status": "assigned", "roles": data})

                elif path.endswith("/actions"):
                    mock_instance.actions_received.append(data)
                    mock_instance.current_day += 1
                    finished = mock_instance.current_day > mock_instance.total_days
                    self._send_json(200, {"status": "accepted", "finished": finished})

                else:
                    self._send_json(404, {"error": "Not Found"})

        self.server = HTTPServer((self.host, self.port), Handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        return self.base_url

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
