"""Breadth-First Search (BFS) Path Planner for Hex Grid baseline."""
from collections import deque
from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Set, Tuple, Union

from client.protocol import AgentKind, Direction
from env.hex_grid import HexGrid


@dataclass
class PathResult:
    """Standardized path planning result metric bundle."""
    start: int
    target: int
    path: List[int] = field(default_factory=list)
    actions: List[Direction] = field(default_factory=list)
    route_length: int = 0
    movement_cost: float = float("inf")
    fuel_consumption: int = 0
    runtime_ms: float = 0.0
    reachable: bool = False


class BFSPlanner:
    """Breadth-First Search baseline planner on Hex Grid.
    
    Finds the shortest path in terms of number of hops (edges traversed),
    ignoring terrain movement costs but strictly respecting impassable obstacles.
    """

    def __init__(self, grid: HexGrid):
        self.grid = grid

    def plan(
        self,
        start_index: int,
        target_indices: Union[int, List[int], Set[int]],
        agent_kind: AgentKind = AgentKind.PATROL,
        fuel_limit: Optional[int] = None,
    ) -> PathResult:
        """Find hop-shortest path from start to the nearest reachable target.
        
        Args:
            start_index: Starting flat cell index.
            target_indices: Target index or collection of candidate target indices.
            agent_kind: AgentKind for fuel calculation.
            fuel_limit: Optional fuel constraint limit.
            
        Returns:
            PathResult with path, actions, length, costs, and runtime.
        """
        start_time = time.perf_counter()

        if isinstance(target_indices, int):
            targets = {target_indices}
        else:
            targets = set(target_indices)

        # Validate start and target
        if not self.grid.is_passable(start_index):
            runtime = (time.perf_counter() - start_time) * 1000
            return PathResult(start=start_index, target=-1, runtime_ms=runtime, reachable=False)

        if start_index in targets:
            runtime = (time.perf_counter() - start_time) * 1000
            return PathResult(
                start=start_index,
                target=start_index,
                path=[start_index],
                actions=[],
                route_length=0,
                movement_cost=0.0,
                fuel_consumption=0,
                runtime_ms=runtime,
                reachable=True,
            )

        # BFS queue stores: (current_cell, path, actions, fuel_spent, step_cost)
        queue = deque([(start_index, [start_index], [], 0, 0.0)])
        visited = {start_index}
        chosen_result: Optional[PathResult] = None

        while queue:
            curr, path, actions, fuel_spent, step_cost = queue.popleft()

            if curr in targets:
                # Target reached
                chosen_result = PathResult(
                    start=start_index,
                    target=curr,
                    path=path,
                    actions=actions,
                    route_length=len(actions),
                    movement_cost=step_cost,
                    fuel_consumption=fuel_spent,
                    reachable=True,
                )
                break

            neighbors = self.grid.get_all_neighbors(curr, check_passable=True)
            for direction, nxt in neighbors.items():
                if nxt not in visited:
                    move_cost, fuel_cost = self.grid.get_movement_cost(curr, nxt, agent_kind)
                    if move_cost == float("inf"):
                        continue

                    new_fuel = fuel_spent + fuel_cost
                    if fuel_limit is not None and new_fuel > fuel_limit:
                        continue

                    visited.add(nxt)
                    queue.append((
                        nxt,
                        path + [nxt],
                        actions + [direction],
                        new_fuel,
                        step_cost + move_cost,
                    ))

        runtime = (time.perf_counter() - start_time) * 1000
        if chosen_result is not None:
            chosen_result.runtime_ms = runtime
            return chosen_result

        # Target unreachable
        target_repr = next(iter(targets)) if targets else -1
        return PathResult(
            start=start_index,
            target=target_repr,
            runtime_ms=runtime,
            reachable=False,
        )
