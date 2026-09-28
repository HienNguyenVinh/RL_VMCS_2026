"""HTTP Client for PTIT PROCON 2026 Server."""
import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests

from client.protocol import ActionPlan, MatchSetup, MatchState

logger = logging.getLogger(__name__)


class ProconHttpClient:
    """Client for interacting with the PROCON 2026 HTTP API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        match_id: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.base_url = (base_url or os.getenv("PROCON_BASE_URL", "https://procon.ptit.edu.vn")).rstrip("/")
        self.match_id = match_id or os.getenv("PROCON_MATCH_ID", "")
        self.token = token or os.getenv("PROCON_TOKEN", "")
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    @property
    def api_prefix(self) -> str:
        return f"{self.base_url}/api/v1/matches/{self.match_id}"

    def get_setup(self) -> MatchSetup:
        """Fetch match setup configuration (GET /setup)."""
        url = f"{self.api_prefix}/setup"
        logger.info(f"Fetching setup from {url}")
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return MatchSetup.from_dict(self.match_id, data)

    def post_assignment(self, assignment: List[int]) -> Dict[str, Any]:
        """Assign roles to agents (POST /assignment).
        
        Args:
            assignment: List of integers (0 = Patrol, 1 = Refuel).
        """
        url = f"{self.api_prefix}/assignment"
        logger.info(f"Submitting role assignment: {assignment}")
        resp = self.session.post(url, json=assignment, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def wait_for_start(self, poll_interval: float = 0.5, max_wait_seconds: float = 120.0) -> Dict[str, Any]:
        """Poll GET /start until match commences (handles HTTP 425)."""
        url = f"{self.api_prefix}/start"
        logger.info(f"Waiting for match {self.match_id} to start...")
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("Match started!")
                return resp.json() if resp.text else {}
            elif resp.status_code == 425:
                # HTTP 425 Too Early: match not yet ready
                time.sleep(poll_interval)
                continue
            else:
                resp.raise_for_status()

        raise TimeoutError(f"Match did not start within {max_wait_seconds} seconds.")

    def get_state(self) -> MatchState:
        """Fetch current match state for the day (GET /state)."""
        url = f"{self.api_prefix}/state"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return MatchState.from_dict(resp.json())

    def post_actions(self, actions: ActionPlan) -> Dict[str, Any]:
        """Submit plan of actions for all agents (POST /actions)."""
        url = f"{self.api_prefix}/actions"
        resp = self.session.post(url, json=actions, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def get_result(self) -> Dict[str, Any]:
        """Fetch final match result (GET /result)."""
        url = f"{self.api_prefix}/result"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json() if resp.text else {}
