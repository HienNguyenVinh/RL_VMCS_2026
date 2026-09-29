"""Client package for PTIT PROCON 2026."""
from client.http_client import ProconHttpClient
from client.mock_server import MockProconServer
from client.protocol import (
    ActionPlan,
    AgentKind,
    AgentState,
    Direction,
    MatchResult,
    MatchSetup,
    MatchState,
    ProconAuthError,
    ProconError,
    ProconMatchNotStartedError,
    ProconRateLimitError,
    create_idle_action_plan,
    validate_action_plan,
)
def __getattr__(name: str):
    if name == "MatchRunner":
        from client.runner import MatchRunner
        return MatchRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ProconHttpClient",
    "MatchRunner",
    "MockProconServer",
    "Direction",
    "AgentKind",
    "AgentState",
    "MatchSetup",
    "MatchState",
    "MatchResult",
    "ActionPlan",
    "ProconError",
    "ProconAuthError",
    "ProconRateLimitError",
    "ProconMatchNotStartedError",
    "validate_action_plan",
    "create_idle_action_plan",
]
