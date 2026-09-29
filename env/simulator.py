"""Offline Hex Grid Simulator for PTIT PROCON 2026."""
import random
from typing import Any, Dict, List, Optional, Tuple, Union

from client.protocol import ActionPlan, AgentKind, Direction
from env.hex_grid import HexCoord, HexGrid, TerrainType, TrafficLevel
from env.reward import RewardFunction
from env.state import EnvAgent, SimulationState, UdonSpot


class HexGridSimulator:
    """Offline environment simulating Hex Grid movement, udon collection, fuel, and traffic.
    
    Standard API:
    - state = env.reset(seed)
    - next_state, reward, done, info = env.step(actions)
    """

    def __init__(
        self,
        width: int = 15,
        height: int = 15,
        day_steps: int = 10,
        num_patrol: int = 2,
        num_refuel: int = 1,
        num_spots: int = 5,
        fuel_limit_patrol: int = 50,
        fuel_limit_refuel: int = 100,
        seed: Optional[int] = None,
        grid: Optional[HexGrid] = None,
    ):
        self.width = width
        self.height = height
        self.day_steps = day_steps
        self.num_patrol = num_patrol
        self.num_refuel = num_refuel
        self.num_spots = num_spots
        self.fuel_limit_patrol = fuel_limit_patrol
        self.fuel_limit_refuel = fuel_limit_refuel
        self.seed = seed
        self.reward_fn = RewardFunction()

        self.grid = grid or self._generate_default_grid(width, height, seed)
        self.state: Optional[SimulationState] = None
        self.reset(seed)

    def _generate_default_grid(self, width: int, height: int, seed: Optional[int] = None) -> HexGrid:
        """Create a randomized grid with mixed terrain (Plain, Mountain, Pond, Road)."""
        rng = random.Random(seed)
        num_cells = width * height
        cell_types = [TerrainType.PLAIN.value] * num_cells
        traffics = [TrafficLevel.CLEAR.value] * num_cells

        # Add mountains (~10%)
        num_mountains = max(1, int(num_cells * 0.10))
        for idx in rng.sample(range(num_cells), num_mountains):
            cell_types[idx] = TerrainType.MOUNTAIN.value

        # Add ponds (~5% impassable)
        num_ponds = max(1, int(num_cells * 0.05))
        for idx in rng.sample(range(num_cells), num_ponds):
            cell_types[idx] = TerrainType.POND.value

        # Add roads (~15%)
        num_roads = max(1, int(num_cells * 0.15))
        for idx in rng.sample(range(num_cells), num_roads):
            if cell_types[idx] != TerrainType.POND.value:
                cell_types[idx] = TerrainType.ROAD.value
                traffics[idx] = rng.choice([TrafficLevel.CLEAR.value, TrafficLevel.CROWDED.value])

        return HexGrid(width, height, cell_types=cell_types, traffic_levels=traffics)

    def reset(self, seed: Optional[int] = None) -> SimulationState:
        """Reset environment to initial state."""
        if seed is not None:
            self.seed = seed
        rng = random.Random(self.seed)

        # Place agents on passable cells only
        passable_cells = [i for i in range(self.grid.num_cells) if self.grid.is_passable(i)]
        num_agents = self.num_patrol + self.num_refuel
        agent_positions = rng.sample(passable_cells, num_agents)

        agents: List[EnvAgent] = []
        for i in range(self.num_patrol):
            agents.append(
                EnvAgent(
                    agent_id=i,
                    kind=AgentKind.PATROL,
                    pos=agent_positions[i],
                    fuel=self.fuel_limit_patrol,
                    max_fuel=self.fuel_limit_patrol,
                )
            )

        for i in range(self.num_refuel):
            a_id = self.num_patrol + i
            agents.append(
                EnvAgent(
                    agent_id=a_id,
                    kind=AgentKind.REFUEL,
                    pos=agent_positions[a_id],
                    fuel=self.fuel_limit_refuel,
                    max_fuel=self.fuel_limit_refuel,
                )
            )

        # Place Udon spots on passable cells
        remaining_passable = [c for c in passable_cells if c not in agent_positions]
        spot_positions = rng.sample(remaining_passable, min(self.num_spots, len(remaining_passable)))

        spots: List[UdonSpot] = []
        for s_id, pos in enumerate(spot_positions):
            initial_stock = rng.randint(10, 25)
            spots.append(
                UdonSpot(
                    spot_id=s_id,
                    pos=pos,
                    udon_type=s_id % 3,
                    initial_stock=initial_stock,
                    current_stock=initial_stock,
                )
            )

        self.state = SimulationState(
            day=0,
            step=0,
            grid=self.grid,
            agents=agents,
            spots=spots,
            traffics=list(self.grid.traffic_levels),
        )
        return self.state

    def get_valid_actions(self, agent_id: int) -> List[Direction]:
        """Return list of valid directions agent can execute given position, boundaries, terrain, and fuel."""
        assert self.state is not None
        agent = self.state.get_agent(agent_id)
        if not agent or not agent.is_active:
            return [Direction.STAY]

        valid = [Direction.STAY]
        for d in Direction.all_movements():
            nxt_idx = self.grid.get_neighbor_index(agent.pos, d)
            if nxt_idx is not None and self.grid.is_passable(nxt_idx):
                step_cost, fuel_cost = self.grid.get_movement_cost(agent.pos, nxt_idx, agent.kind)
                if agent.fuel >= fuel_cost:
                    valid.append(d)

        return valid

    def step(
        self, actions: Union[Dict[int, Direction], Dict[int, int], ActionPlan]
    ) -> Tuple[SimulationState, Dict[int, float], bool, Dict[str, Any]]:
        """Execute one step (or plan) across all agents."""
        assert self.state is not None, "Simulator must be reset before step()"
        prev_state = self.state

        # Normalize actions to Dict[int, Direction]
        step_actions: Dict[int, Direction] = {}
        if isinstance(actions, list):
            # ActionPlan format: list of plans for each agent
            for a_idx, p in enumerate(actions):
                if p:
                    step_actions[a_idx] = Direction(p[0])
                else:
                    step_actions[a_idx] = Direction.STAY
        else:
            for a_id, d in actions.items():
                step_actions[a_id] = Direction(d) if not isinstance(d, Direction) else d

        collected_per_agent: Dict[int, int] = {a.agent_id: 0 for a in self.state.agents}
        new_positions: Dict[int, int] = {}
        conflicts: List[Tuple[int, int]] = []
        total_step_fuel = 0

        # 1. Move execution & fuel consumption
        for agent in self.state.agents:
            a_id = agent.agent_id
            direction = step_actions.get(a_id, Direction.STAY)

            if not agent.is_active or (agent.fuel <= 0 and agent.kind == AgentKind.PATROL):
                new_positions[a_id] = agent.pos
                continue

            if direction == Direction.STAY:
                new_positions[a_id] = agent.pos
                continue

            nxt_pos = self.grid.get_neighbor_index(agent.pos, direction)
            if nxt_pos is not None and self.grid.is_passable(nxt_pos):
                step_cost, fuel_cost = self.grid.get_movement_cost(agent.pos, nxt_pos, agent.kind)
                if agent.fuel >= fuel_cost:
                    agent.pos = nxt_pos
                    agent.fuel = max(0, agent.fuel - fuel_cost)
                    total_step_fuel += fuel_cost
                    agent.steps_taken += 1

            new_positions[a_id] = agent.pos

        # 2. Collision / Conflict detection
        pos_to_agents: Dict[int, List[int]] = {}
        for a_id, pos in new_positions.items():
            pos_to_agents.setdefault(pos, []).append(a_id)

        for pos, agent_ids in pos_to_agents.items():
            if len(agent_ids) > 1:
                for i in range(len(agent_ids)):
                    for j in range(i + 1, len(agent_ids)):
                        conflicts.append((agent_ids[i], agent_ids[j]))

        # 3. Udon Collection
        for agent in self.state.agents:
            if agent.kind == AgentKind.PATROL:
                for spot in self.state.spots:
                    if spot.pos == agent.pos and spot.current_stock > 0:
                        if agent.agent_id not in spot.visited_by_agents:
                            spot.visited_by_agents.append(agent.agent_id)
                            collected = min(5, spot.current_stock)
                            spot.current_stock -= collected
                            agent.collected_udon += collected
                            collected_per_agent[agent.agent_id] += collected

        # 4. Refueling logic: refuel agent transfers fuel to adjacent or collocated patrol agents
        refuel_agents = [a for a in self.state.agents if a.kind == AgentKind.REFUEL]
        patrol_agents = [a for a in self.state.agents if a.kind == AgentKind.PATROL]

        for ra in refuel_agents:
            for pa in patrol_agents:
                coord_ra = HexCoord.from_index(ra.pos, self.width)
                coord_pa = HexCoord.from_index(pa.pos, self.width)
                if coord_ra.distance_to(coord_pa) <= 1:
                    needed = pa.max_fuel - pa.fuel
                    transfer = min(needed, 10, ra.fuel)
                    if transfer > 0:
                        pa.fuel += transfer
                        ra.fuel -= transfer
                        self.state.total_fuel_transferred += transfer

        # Update environment statistics
        self.state.step += 1
        self.state.total_conflicts += len(conflicts)
        self.state.total_fuel_consumed += total_step_fuel
        self.state.total_team_score += sum(collected_per_agent.values())

        done = self.state.step >= self.day_steps

        # Compute rewards
        rewards = self.reward_fn.compute_rewards(
            prev_state, self.state, collected_per_agent, conflicts
        )

        info = {
            "step": self.state.step,
            "day": self.state.day,
            "conflicts": len(conflicts),
            "total_conflicts": self.state.total_conflicts,
            "step_collected": sum(collected_per_agent.values()),
            "total_collected": self.state.total_team_score,
            "step_fuel": total_step_fuel,
            "total_fuel": self.state.total_fuel_consumed,
            "total_fuel_transferred": self.state.total_fuel_transferred,
        }


        return self.state, rewards, done, info
