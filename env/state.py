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
    def from_dict(cls, data: Any, default_id: int = 0) -> "UdonSpot":
        if isinstance(data, int):
            return cls(
                spot_id=default_id,
                pos=data,
                udon_type=0,
                initial_stock=10,
                current_stock=10,
            )
        elif isinstance(data, dict):
            pos = data.get("pos", 0)
            stock = data.get("stock", data.get("current_stock", 10))
            return cls(
                spot_id=data.get("id", default_id),
                pos=pos,
                udon_type=data.get("type", 0),
                initial_stock=stock,
                current_stock=stock,
            )
        return cls(spot_id=default_id, pos=0, udon_type=0, initial_stock=10, current_stock=10)


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

        # Parse fuel limit robustly (handles dict, number multiplier, or None)
        fuel_limits = setup.fuel_limits if isinstance(setup.fuel_limits, dict) else {}
        multiplier = setup.fuel_limits if isinstance(setup.fuel_limits, (int, float)) else 1.0

        agents: List[EnvAgent] = []
        for a in state.agents:
            base_limit = 50 if a.kind == AgentKind.PATROL else 100
            if fuel_limits:
                fuel_limit = fuel_limits.get(
                    "patrol" if a.kind == AgentKind.PATROL else "refuel", base_limit
                )
            else:
                fuel_limit = int(base_limit * multiplier) if multiplier > 0 else base_limit

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

        # Normalize traffics to flat list of ints of length grid.num_cells
        traffic_array = [0] * grid.num_cells
        if isinstance(state.traffics, list):
            for idx, item in enumerate(state.traffics):
                if isinstance(item, dict) and "pos" in item:
                    p = item.get("pos", 0)
                    if 0 <= p < grid.num_cells:
                        traffic_array[p] = item.get("status", 0)
                elif isinstance(item, int) and idx < grid.num_cells:
                    traffic_array[idx] = item
        elif isinstance(state.traffics, dict):
            for p, st in state.traffics.items():
                if isinstance(p, int) and 0 <= p < grid.num_cells:
                    traffic_array[p] = st

        # Sync grid traffic levels
        grid.traffic_levels = list(traffic_array)

        return cls(
            day=state.day,
            step=0,
            grid=grid,
            agents=agents,
            spots=spots,
            traffics=traffic_array,
        )
