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
