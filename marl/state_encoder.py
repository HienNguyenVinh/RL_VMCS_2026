"""State Encoder for discretizing continuous/combinatorial states into tabular features (Phase 6)."""
from typing import Any, Dict, List, Optional, Tuple
from env.hex_grid import HexCoord
from env.state import EnvAgent, SimulationState, UdonSpot


class StateEncoder:
    """Discretizes multi-agent state into compact discrete tuples for Tabular IQL."""

    def __init__(self, num_fuel_buckets: int = 3, num_dist_buckets: int = 4):
        self.num_fuel_buckets = num_fuel_buckets
        self.num_dist_buckets = num_dist_buckets

    def get_fuel_bucket(self, fuel: int, max_fuel: int) -> int:
        """Categorize fuel into 0 (Low <25%), 1 (Medium 25-65%), 2 (High >65%)."""
        ratio = fuel / max(1, max_fuel)
        if ratio < 0.25:
            return 0
        elif ratio < 0.65:
            return 1
        return 2

    def get_dist_bucket(self, dist: int) -> int:
        """Bucket distances: 0 (adjacent <=1), 1 (near 2-3), 2 (medium 4-6), 3 (far >=7)."""
        if dist <= 1:
            return 0
        elif dist <= 3:
            return 1
        elif dist <= 6:
            return 2
        return 3

    def get_cost_bucket(self, cost: float) -> int:
        """Bucket DP cost-to-go: 0 (<=2.0), 1 (2.1-5.0), 2 (5.1-9.0), 3 (>=9.1 or unreachable)."""
        if cost <= 2.0:
            return 0
        elif cost <= 5.0:
            return 1
        elif cost <= 9.0:
            return 2
        return 3

    def encode_agent_state(
        self,
        agent: EnvAgent,
        sim_state: SimulationState,
        other_assignments: Optional[Dict[int, int]] = None,
        cost_to_go: Optional[Dict[int, float]] = None,
    ) -> Tuple[Any, ...]:
        """Encode state with local position, fuel, distances/costs to available targets, and teammate actions.
        
        Features:
        - agent_kind: 0 (Patrol) or 1 (Refuel)
        - fuel_bucket: 0, 1, 2
        - distances/cost-to-go to top 2 closest active targets: (d1, d2)
        - other_teammate_assignment: action chosen by other agent in previous step
        """
        fuel_b = self.get_fuel_bucket(agent.fuel, agent.max_fuel)
        agent_coord = HexCoord.from_index(agent.pos, sim_state.grid.width)

        # Distances or DP cost-to-go to top 2 spots with remaining stock
        distances: List[float] = []
        for spot in sim_state.spots:
            if spot.current_stock > 0 and sim_state.grid.is_passable(spot.pos):
                if cost_to_go is not None and spot.pos in cost_to_go:
                    distances.append(cost_to_go[spot.pos])
                else:
                    s_coord = HexCoord.from_index(spot.pos, sim_state.grid.width)
                    distances.append(float(agent_coord.distance_to(s_coord)))
            else:
                distances.append(99.0)

        distances.sort()
        if cost_to_go is not None:
            d1 = self.get_cost_bucket(distances[0]) if len(distances) > 0 else 3
            d2 = self.get_cost_bucket(distances[1]) if len(distances) > 1 else 3
        else:
            d1 = self.get_dist_bucket(int(distances[0])) if len(distances) > 0 else 3
            d2 = self.get_dist_bucket(int(distances[1])) if len(distances) > 1 else 3

        # Teammate assignment feature for coordination
        other_act = -1
        if other_assignments:
            for other_id, act in other_assignments.items():
                if other_id != agent.agent_id:
                    other_act = act
                    break

        return (
            agent.kind.value,
            fuel_b,
            d1,
            d2,
            other_act,
        )

