"""State Encoder for discretizing continuous/combinatorial states into tabular features."""
from typing import Any, List, Tuple
from env.hex_grid import HexCoord
from env.state import EnvAgent, SimulationState, UdonSpot


class StateEncoder:
    """Discretizes PROCON game state into compact tuples for tabular Q-learning."""

    def __init__(self, num_fuel_buckets: int = 3, num_dist_buckets: int = 3):
        self.num_fuel_buckets = num_fuel_buckets
        self.num_dist_buckets = num_dist_buckets

    def get_fuel_bucket(self, fuel: int, max_fuel: int) -> int:
        """Categorize fuel into: 0 (Low), 1 (Medium), 2 (High)."""
        ratio = fuel / max(1, max_fuel)
        if ratio < 0.25:
            return 0
        elif ratio < 0.65:
            return 1
        return 2

    def encode_agent_state(
        self, agent: EnvAgent, sim_state: SimulationState
    ) -> Tuple[Any, ...]:
        """Encode an agent's local perspective into a compact state tuple."""
        fuel_b = self.get_fuel_bucket(agent.fuel, agent.max_fuel)
        agent_coord = HexCoord.from_index(agent.pos, sim_state.grid.width)

        # Find closest spot with remaining stock
        closest_spot_dist = 999
        closest_spot_id = -1
        for spot in sim_state.spots:
            if spot.current_stock > 0:
                s_coord = HexCoord.from_index(spot.pos, sim_state.grid.width)
                dist = agent_coord.distance_to(s_coord)
                if dist < closest_spot_dist:
                    closest_spot_dist = dist
                    closest_spot_id = spot.spot_id

        dist_bucket = min(2, closest_spot_dist // 4)

        return (
            agent.kind.value,
            fuel_b,
            closest_spot_id,
            dist_bucket,
        )
