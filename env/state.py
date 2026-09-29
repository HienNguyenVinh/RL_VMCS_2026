"""Environment state representations and conversion utilities for PTIT PROCON 2026."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from client.protocol import AgentKind, Direction, MatchSetup, MatchState
from env.hex_grid import HexCoord, HexGrid, TerrainType, TrafficLevel


@dataclass
class UdonSpot:
    """Represents an Udon shop on the grid."""
    spot_id: int
    pos: int
    udon_type: int
    initial_stock: int
    current_stock: int
    visited_by_agents: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_id: int = 0) -> "UdonSpot":
        pos = data.get("pos", 0)
        stock = data.get("stock", data.get("current_stock", 10))
        return cls(
            spot_id=data.get("id", default_id),
            pos=pos,
            udon_type=data.get("type", 0),
            initial_stock=stock,
            current_stock=stock,
        )


@dataclass
class EnvAgent:
    """State of an active agent in the environment."""
    agent_id: int
    kind: AgentKind
    pos: int
    fuel: int
    max_fuel: int = 50
    target_pos: Optional[int] = None
    collected_udon: int = 0
    is_active: bool = True
    steps_taken: int = 0

    def coord(self, width: int) -> HexCoord:
        return HexCoord.from_index(self.pos, width)


@dataclass
class SimulationState:
    """Complete snapshot of the environment state at a given day/step."""
    day: int
    step: int
    grid: HexGrid
    agents: List[EnvAgent]
    spots: List[UdonSpot]
    traffics: List[int] = field(default_factory=list)
    total_team_score: int = 0
    total_fuel_consumed: int = 0
    total_conflicts: int = 0
    total_fuel_transferred: int = 0


    def get_agent(self, agent_id: int) -> Optional[EnvAgent]:
        for a in self.agents:
            if a.agent_id == agent_id:
                return a
        return None

    def get_spot_at(self, pos: int) -> Optional[UdonSpot]:
        for s in self.spots:
            if s.pos == pos:
                return s
        return None

    @classmethod
    def from_match(cls, setup: MatchSetup, state: MatchState) -> "SimulationState":
        """Build SimulationState from server MatchSetup and MatchState."""
        grid = HexGrid.from_setup(setup)

        agents: List[EnvAgent] = []
        for a in state.agents:
            fuel_limit = setup.fuel_limits.get(
                "patrol" if a.kind == AgentKind.PATROL else "refuel",
                50 if a.kind == AgentKind.PATROL else 100,
            )
            agents.append(
                EnvAgent(
                    agent_id=a.agent_id,
                    kind=a.kind,
                    pos=a.pos,
                    fuel=a.fuel,
                    max_fuel=fuel_limit,
                    collected_udon=a.score,
                )
            )

        spots: List[UdonSpot] = []
        for idx, s in enumerate(setup.spots):
            spots.append(UdonSpot.from_dict(s, default_id=idx))

        return cls(
            day=state.day,
            step=0,
            grid=grid,
            agents=agents,
            spots=spots,
            traffics=state.traffics or [0] * grid.num_cells,
        )
