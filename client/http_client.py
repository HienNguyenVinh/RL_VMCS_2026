"""HTTP Client for PTIT PROCON 2026 Server with rate-limiting, retry, and error handling."""
import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import HTTPError

from client.protocol import (
    ActionPlan,
    MatchResult,
    MatchSetup,
    MatchState,
    ProconAuthError,
    ProconMatchNotStartedError,
    ProconRateLimitError,
    validate_action_plan,
)

logger = logging.getLogger(__name__)


class ProconHttpClient:
    """Client for interacting with the PROCON 2026 HTTP API.
    
    Adheres to the official competition protocol:
    - Base URL: https://procon.ptit.edu.vn
    - Rate limit: Polling rate >= 200ms
    - Headers: Authorization: Bearer <TOKEN>
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        match_id: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 5.0,
        min_poll_interval: float = 0.25,  # >= 200ms as required by competition specs
        max_retries: int = 3,
    ):
        self.base_url = (base_url or os.getenv("PROCON_BASE_URL", "https://procon.ptit.edu.vn")).rstrip("/")
        self.match_id = match_id or os.getenv("PROCON_MATCH_ID", "")
        self.token = token or os.getenv("PROCON_TOKEN", "")
        self.timeout = timeout
        self.min_poll_interval = max(0.20, min_poll_interval)
        self.max_retries = max_retries

        self._last_request_time: float = 0.0

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    @property
    def api_prefix(self) -> str:
        return f"{self.base_url}/api/v1/matches/{self.match_id}"

    def _throttle(self) -> None:
        """Enforce minimum polling interval (>= 200ms) to avoid HTTP 429."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_poll_interval:
            sleep_time = self.min_poll_interval - elapsed
            time.sleep(sleep_time)

    def _request(self, method: str, path: str, json_body: Optional[Any] = None) -> requests.Response:
        """Internal helper executing throttled HTTP requests with 429 retry and error categorization."""
        url = f"{self.api_prefix}{path}"
        retries = 0

        while True:
            self._throttle()
            self._last_request_time = time.monotonic()

            start_t = time.perf_counter()
            logger.debug(f"HTTP {method} {url}")

            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    json=json_body,
                    timeout=self.timeout,
                )
                latency_ms = (time.perf_counter() - start_t) * 1000

                if resp.status_code == 401:
                    logger.error(f"HTTP 401 Unauthorized for {url}. Token invalid or expired.")
                    raise ProconAuthError(
                        f"Authentication failed (HTTP 401). Check PROCON_TOKEN={self.token[:8]}..."
                    )

                if resp.status_code == 429:
                    retries += 1
                    retry_after = float(resp.headers.get("Retry-After", 1.0))
                    logger.warning(
                        f"HTTP 429 Too Many Requests on {url}. Backing off for {retry_after}s (retry {retries}/{self.max_retries})"
                    )
                    if retries > self.max_retries:
                        raise ProconRateLimitError(f"HTTP 429: Rate limit exceeded after {self.max_retries} retries.")
                    time.sleep(retry_after)
                    continue

                logger.debug(f"HTTP {method} {url} -> {resp.status_code} ({latency_ms:.1f}ms)")
                return resp

            except requests.RequestException as e:
                if isinstance(e, (ProconAuthError, ProconRateLimitError)):
                    raise
                logger.error(f"Network error during {method} {url}: {e}")
                raise

    def get_setup(self, max_wait_seconds: float = 120.0) -> MatchSetup:
        """Fetch match setup configuration (GET /setup), retrying on HTTP 425 (map not open yet)."""
        logger.info(f"Fetching match setup: GET {self.api_prefix}/setup")
        start_t = time.monotonic()
        while time.monotonic() - start_t < max_wait_seconds:
            resp = self._request("GET", "/setup")
            if resp.status_code == 200:
                data = resp.json()
                setup = MatchSetup.from_dict(self.match_id, data)
                logger.info(
                    f"Setup parsed: map={setup.width}x{setup.height}, agents={setup.num_agents}, daySteps={setup.day_steps}"
                )
                return setup
            elif resp.status_code == 425:
                logger.info("Match setup not ready yet (HTTP 425: map not open), retrying in 200ms...")
                time.sleep(0.2)
                continue
            else:
                resp.raise_for_status()

        raise ProconMatchNotStartedError(
            f"Match setup for {self.match_id} timed out after {max_wait_seconds}s"
        )

    def post_assignment(self, assignment: List[int]) -> Dict[str, Any]:
        """Assign agent roles (POST /assignment).
        
        Args:
            assignment: List of integers (0 = Patrol, 1 = Refuel).
        """
        logger.info(f"Assigning agent roles: POST /assignment with {assignment}")
        resp = self._request("POST", "/assignment", json_body=assignment)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def wait_for_start(
        self, poll_interval: float = 0.5, max_wait_seconds: float = 120.0
    ) -> Dict[str, Any]:
        """Poll GET /start until match commences (handles HTTP 425 Too Early)."""
        logger.info(f"Waiting for match {self.match_id} to commence (GET /start)...")
        start_time = time.monotonic()
        poll_delay = max(poll_interval, self.min_poll_interval)

        while time.monotonic() - start_time < max_wait_seconds:
            resp = self._request("GET", "/start")
            if resp.status_code == 200:
                logger.info("Match has officially started!")
                return resp.json() if resp.text else {}
            elif resp.status_code in (425, 404):
                time.sleep(poll_delay)
                continue
            else:
                resp.raise_for_status()

        raise ProconMatchNotStartedError(
            f"Match {self.match_id} did not start within {max_wait_seconds} seconds."
        )

    def get_state(self) -> Optional[MatchState]:
        """Fetch current match state for the day (GET /state). Returns None if 425/404."""
        resp = self._request("GET", "/state")
        if resp.status_code == 200:
            data = resp.json()
            if data is not None:
                state = MatchState.from_dict(data)
                logger.debug(f"Fetched State: Day {state.day}, Active Agents: {len(state.agents)}")
                return state
            return None
        elif resp.status_code in (425, 404):
            return None
        resp.raise_for_status()
        return None

    def post_actions(
        self, actions: ActionPlan, setup: Optional[MatchSetup] = None
    ) -> Dict[str, Any]:
        """Validate and submit plan of actions for all agents (POST /actions)."""
        if setup is not None:
            validate_action_plan(actions, setup.num_agents, setup.day_steps)

        logger.info(f"Submitting action plan for {len(actions)} agents")
        resp = self._request("POST", "/actions", json_body=actions)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def get_result(self) -> MatchResult:
        """Fetch final match result (GET /result)."""
        logger.info(f"Fetching match result: GET {self.api_prefix}/result")
        resp = self._request("GET", "/result")
        resp.raise_for_status()
        data = resp.json() if resp.text else {}
        return MatchResult.from_dict(self.match_id, data)
