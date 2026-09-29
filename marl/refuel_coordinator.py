"""Refueling Coordination and Rendezvous Management (Phase 8).
Manages low-fuel thresholds, refuel requests, meeting point (rendezvous) selection,
time synchronization, and stationary fallback.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from client.protocol import AgentKind, Direction
from env.hex_grid import HexCoord, HexGrid
from env.state import EnvAgent, SimulationState
from planner.dijkstra import DijkstraPlanner


@dataclass
class RefuelRequest:
    """Request issued by a low-fuel Patrol agent."""
    patrol_agent_id: int
    current_fuel: int
    max_fuel: int
    fuel_ratio: float
    current_pos: int
    urgency: float  # 1.0 - fuel_ratio


@dataclass
class RendezvousPlan:
    """Coordinated multi-agent plan for a refueling rendezvous."""
    patrol_id: int
    refuel_id: int
    rendezvous_cell: int
    patrol_actions: List[int]
    refuel_actions: List[int]
    patrol_arrival_step: int
    refuel_arrival_step: int
    is_feasible: bool = True
    reason: str = "OK"


class RefuelCoordinator:
    """Coordinates refueling rendezvous between Patrol agents and Refuel agents."""

    def __init__(
        self,
        grid: HexGrid,
        low_fuel_threshold: float = 0.35,  # Request refuel when <= 35% fuel
        critical_fuel_threshold: float = 0.15,  # Critical emergency when <= 15%
    ):
        self.grid = grid
        self.low_fuel_threshold = low_fuel_threshold
        self.critical_fuel_threshold = critical_fuel_threshold
        self.dijkstra = DijkstraPlanner(grid)

    def check_refuel_requests(
        self, sim_state: SimulationState, day_steps: int = 30
    ) -> List[RefuelRequest]:
        """Detect patrol agents needing refueling, sorted by urgency."""
        requests: List[RefuelRequest] = []
        safe_buffer = max(20, int(day_steps * 0.65))
        for agent in sim_state.agents:
            if agent.kind == AgentKind.PATROL and agent.is_active:
                ratio = agent.fuel / max(1, agent.max_fuel)
                # Request refuel if fuel cannot safely cover next day's full patrol or ratio is low
                if agent.fuel <= safe_buffer or ratio <= self.low_fuel_threshold:
                    requests.append(
                        RefuelRequest(
                            patrol_agent_id=agent.agent_id,
                            current_fuel=agent.fuel,
                            max_fuel=agent.max_fuel,
                            fuel_ratio=ratio,
                            current_pos=agent.pos,
                            urgency=1.0 - ratio,
                        )
                    )
        requests.sort(key=lambda r: r.urgency, reverse=True)
        return requests

    def get_available_refuel_agents(self, sim_state: SimulationState) -> List[EnvAgent]:
        """Return active refuel agents with fuel remaining, sorted by fuel descending."""
        refuelers = [
            a for a in sim_state.agents
            if a.kind == AgentKind.REFUEL and a.is_active and a.fuel > 0
        ]
        refuelers.sort(key=lambda a: a.fuel, reverse=True)
        return refuelers

    def find_rendezvous_cell(
        self,
        patrol: EnvAgent,
        refuel: EnvAgent,
        sim_state: SimulationState,
        day_steps: int,
    ) -> Tuple[int, Optional[RendezvousPlan]]:
        """Select optimal rendezvous cell balancing travel steps and fuel preservation."""
        p_coord = HexCoord.from_index(patrol.pos, self.grid.width)
        r_coord = HexCoord.from_index(refuel.pos, self.grid.width)

        # Candidate 1: Patrol current position (Stationary refuel - safest when critical)
        candidates: Set[int] = {patrol.pos}

        # If patrol is not critically low, consider intermediate / midpoint cells
        if patrol.fuel > int(patrol.max_fuel * self.critical_fuel_threshold):
            # Midpoint approximation
            mid_row = (p_coord.row + r_coord.row) // 2
            mid_col = (p_coord.col + r_coord.col) // 2
            mid_idx = mid_row * self.grid.width + mid_col
            if self.grid.is_valid_index(mid_idx) and self.grid.is_passable(mid_idx):
                candidates.add(mid_idx)

            # Cells along patrol's path to active Udon spots
            for spot in sim_state.spots:
                if spot.current_stock > 0 and self.grid.is_passable(spot.pos):
                    # Inspect 1-2 steps towards this spot
                    path_to_spot = self.dijkstra.plan(
                        patrol.pos, spot.pos, agent_kind=AgentKind.PATROL, fuel_limit=patrol.fuel
                    )
                    if path_to_spot.reachable and len(path_to_spot.path) > 1:
                        mid_step = min(2, len(path_to_spot.path) - 1)
                        candidates.add(path_to_spot.path[mid_step])

            # Neighbors around patrol within 2 hexes
            for d in Direction.all_movements():
                n1 = self.grid.get_neighbor_index(patrol.pos, d)
                if n1 is not None and self.grid.is_passable(n1):
                    candidates.add(n1)

        best_cell = patrol.pos
        best_score = float("inf")
        best_p_actions: List[Direction] = []
        best_r_actions: List[Direction] = []
        best_t_p = 0
        best_t_r = 0

        for cell in candidates:
            if not self.grid.is_passable(cell):
                continue

            # Path for Patrol
            p_res = self.dijkstra.plan(
                start_index=patrol.pos,
                target_indices=cell,
                agent_kind=AgentKind.PATROL,
                fuel_limit=patrol.fuel,
            )
            if not p_res.reachable:
                continue

            # Path for Refuel
            r_res = self.dijkstra.plan(
                start_index=refuel.pos,
                target_indices=cell,
                agent_kind=AgentKind.REFUEL,
                fuel_limit=refuel.fuel,
            )
            if not r_res.reachable:
                continue

            t_p = p_res.route_length
            t_r = r_res.route_length
            max_t = max(t_p, t_r)
            if max_t > day_steps:
                continue

            # Score: minimize max arrival time, arrival discrepancy, and fuel spent by patrol
            score = max_t * 2.0 + abs(t_p - t_r) * 1.0 + p_res.fuel_consumption * 1.5

            if score < best_score:
                best_score = score
                best_cell = cell
                best_p_actions = p_res.actions
                best_r_actions = r_res.actions
                best_t_p = t_p
                best_t_r = t_r

        # Time synchronization: faster agent stays and waits for slower agent
        p_plan: List[int] = [a.value for a in best_p_actions]
        r_plan: List[int] = [a.value for a in best_r_actions]

        # Pad to synchronize meeting
        max_arr = max(best_t_p, best_t_r)
        while len(p_plan) < max_arr:
            p_plan.append(Direction.STAY.value)
        while len(r_plan) < max_arr:
            r_plan.append(Direction.STAY.value)

        # Pad to full daySteps
        while len(p_plan) < day_steps:
            p_plan.append(Direction.STAY.value)
        while len(r_plan) < day_steps:
            r_plan.append(Direction.STAY.value)

        plan = RendezvousPlan(
            patrol_id=patrol.agent_id,
            refuel_id=refuel.agent_id,
            rendezvous_cell=best_cell,
            patrol_actions=p_plan[:day_steps],
            refuel_actions=r_plan[:day_steps],
            patrol_arrival_step=best_t_p,
            refuel_arrival_step=best_t_r,
            is_feasible=True,
            reason="Optimal Rendezvous Found",
        )
        return best_cell, plan

    def plan_fallback_stationary(
        self,
        patrol: EnvAgent,
        refuel: EnvAgent,
        day_steps: int,
    ) -> RendezvousPlan:
        """Fallback: Patrol stays still, Refuel moves straight to Patrol's position."""
        p_plan = [Direction.STAY.value] * day_steps

        r_res = self.dijkstra.plan(
            start_index=refuel.pos,
            target_indices=patrol.pos,
            agent_kind=AgentKind.REFUEL,
            fuel_limit=refuel.fuel,
        )

        r_plan = [a.value for a in r_res.actions] if r_res.reachable else []
        t_r = len(r_plan)

        while len(r_plan) < day_steps:
            r_plan.append(Direction.STAY.value)

        return RendezvousPlan(
            patrol_id=patrol.agent_id,
            refuel_id=refuel.agent_id,
            rendezvous_cell=patrol.pos,
            patrol_actions=p_plan,
            refuel_actions=r_plan[:day_steps],
            patrol_arrival_step=0,
            refuel_arrival_step=t_r,
            is_feasible=True,
            reason="Fallback Stationary Rendezvous",
        )
