"""PROCON 2026 Protocol Definitions and Data Structures."""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional


class Direction(IntEnum):
    """Hexagonal movement directions for PTIT PROCON 2026."""
    STAY = -1
    UP_LEFT = 0
    UP_RIGHT = 1
    RIGHT = 2
    DOWN_RIGHT = 3
    DOWN_LEFT = 4
    LEFT = 5

    @classmethod
    def all_movements(cls) -> List["Direction"]:
        return [
            cls.UP_LEFT,
            cls.UP_RIGHT,
            cls.RIGHT,
            cls.DOWN_RIGHT,
            cls.DOWN_LEFT,
            cls.LEFT,
        ]


class AgentKind(IntEnum):
    """Agent role types in PTIT PROCON 2026."""
    PATROL = 0   # Xe tuần tra
    REFUEL = 1   # Xe tiếp nhiên liệu


@dataclass
class AgentState:
    """State representation for a single agent."""
    agent_id: int
    kind: AgentKind
    pos: int  # Cell index (row * width + col)
    fuel: int
    score: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchSetup:
    """Initial match setup received from GET /setup."""
    match_id: str
    day_steps: int
    width: int
    height: int
    num_agents: int
    fuel_limits: Dict[str, int] = field(default_factory=dict)
    cells: List[Dict[str, Any]] = field(default_factory=list)
    spots: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, match_id: str, data: Dict[str, Any]) -> "MatchSetup":
        map_info = data.get("map", {})
        width = map_info.get("width", 0)
        height = map_info.get("height", 0)
        day_steps = data.get("daySteps", 0)
        agents = data.get("agents", [])
        return cls(
            match_id=match_id,
            day_steps=day_steps,
            width=width,
            height=height,
            num_agents=len(agents),
            fuel_limits=data.get("fuelLimits", {}),
            cells=data.get("cells", []),
            spots=data.get("spots", []),
            raw=data,
        )


@dataclass
class MatchState:
    """Current day state received from GET /state."""
    day: int
    agents: List[AgentState] = field(default_factory=list)
    others: List[Dict[str, Any]] = field(default_factory=list)
    traffics: List[int] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchState":
        day = data.get("day", 0)
        agent_list: List[AgentState] = []
        for i, a in enumerate(data.get("agents", [])):
            agent_list.append(
                AgentState(
                    agent_id=i,
                    kind=AgentKind(a.get("kind", 0)),
                    pos=a.get("pos", 0),
                    fuel=a.get("fuel", 0),
                    score=a.get("score", 0),
                    raw=a,
                )
            )
        return cls(
            day=day,
            agents=agent_list,
            others=data.get("others", []),
            traffics=data.get("traffics", []),
            raw=data,
        )


ActionPlan = List[List[int]]  # List of action steps for each agent, e.g. [[0, 1, -1], [5, 4, -1]]


@dataclass
class MatchResult:
    """Final match result received from GET /result."""
    match_id: str
    winner: Optional[str] = None
    scores: Dict[str, Any] = field(default_factory=dict)
    finished: bool = True
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, match_id: str, data: Dict[str, Any]) -> "MatchResult":
        return cls(
            match_id=match_id,
            winner=data.get("winner"),
            scores=data.get("scores", data.get("teamScores", {})),
            finished=data.get("finished", True),
            raw=data,
        )


class ProconError(Exception):
    """Base exception for PROCON client errors."""
    pass


class ProconAuthError(ProconError):
    """Raised when authentication fails (HTTP 401)."""
    pass


class ProconRateLimitError(ProconError):
    """Raised when rate limit is exceeded (HTTP 429)."""
    pass


class ProconMatchNotStartedError(ProconError):
    """Raised when match has not started yet (HTTP 425 timeout)."""
    pass


def validate_action_plan(actions: ActionPlan, num_agents: int, day_steps: int) -> None:
    """Validate action plan format before submitting to server.
    
    Raises:
        ValueError: If plan structure or direction values are invalid.
    """
    if not isinstance(actions, list):
        raise ValueError(f"Action plan must be a list of lists, got {type(actions)}")

    if len(actions) != num_agents:
        raise ValueError(
            f"Action plan agent count mismatch: expected {num_agents} agents, got {len(actions)}"
        )

    valid_directions = {-1, 0, 1, 2, 3, 4, 5}
    for i, agent_plan in enumerate(actions):
        if not isinstance(agent_plan, list):
            raise ValueError(f"Agent {i} plan must be a list, got {type(agent_plan)}")

        if len(agent_plan) > day_steps:
            raise ValueError(
                f"Agent {i} plan exceeds daySteps: {len(agent_plan)} > {day_steps}"
            )

        for step_idx, direction in enumerate(agent_plan):
            if direction not in valid_directions:
                raise ValueError(
                    f"Agent {i} step {step_idx} invalid direction: {direction}. Must be in {valid_directions}"
                )


def create_idle_action_plan(num_agents: int, day_steps: int) -> ActionPlan:
    """Create a smoke-test plan where all agents stay still for all steps."""
    return [[Direction.STAY.value] * day_steps for _ in range(num_agents)]
