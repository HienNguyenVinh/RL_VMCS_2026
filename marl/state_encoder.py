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

    def encode_agent_state(
        self,
        agent: EnvAgent,
        sim_state: SimulationState,
        other_assignments: Optional[Dict[int, int]] = None,
    ) -> Tuple[Any, ...]:
        """Encode state with local position, fuel, distances to available targets, and teammate actions.
        
        Features:
        - agent_kind: 0 (Patrol) or 1 (Refuel)
        - fuel_bucket: 0, 1, 2
        - distances to top 2 closest active targets: (d1, d2)
        - other_teammate_assignment: action chosen by other agent in previous step
        """
        fuel_b = self.get_fuel_bucket(agent.fuel, agent.max_fuel)
        agent_coord = HexCoord.from_index(agent.pos, sim_state.grid.width)

        # Distances to top 2 spots with remaining stock
        distances = []
        for spot in sim_state.spots:
            if spot.current_stock > 0:
                s_coord = HexCoord.from_index(spot.pos, sim_state.grid.width)
                distances.append(agent_coord.distance_to(s_coord))
            else:
                distances.append(99)

        distances.sort()
        d1 = self.get_dist_bucket(distances[0]) if len(distances) > 0 else 3
        d2 = self.get_dist_bucket(distances[1]) if len(distances) > 1 else 3

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
