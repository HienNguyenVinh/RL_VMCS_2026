"""Dijkstra Minimum-Cost Path Planner for Hex Grid baseline."""
import heapq
import time
from typing import Dict, List, Optional, Set, Tuple, Union

from client.protocol import AgentKind, Direction
from env.hex_grid import HexGrid
from planner.bfs import PathResult


class DijkstraPlanner:
    """Dijkstra algorithm finding minimum-cost paths on Hex Grid with terrain and traffic costs.
    
    Guarantees the optimal path according to cumulative movement step cost.
    Supports fuel constraints, multi-target queries, and policy extraction.
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
        """Find minimum movement-cost path from start to closest reachable target.
        
        Args:
            start_index: Starting flat cell index.
            target_indices: Target index or set of candidate target indices.
            agent_kind: AgentKind determining fuel consumption rules.
            fuel_limit: Optional maximum allowed fuel consumption.
            
        Returns:
            PathResult with path, actions, length, movement_cost, fuel_consumption, runtime.
        """
        start_time = time.perf_counter()

        if isinstance(target_indices, int):
            targets = {target_indices}
        else:
            targets = set(target_indices)

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

        # Priority Queue entries: (cost, cell, path, actions, fuel)
        # Counter tie-breaker to prevent comparing lists in heapq
        counter = 0
        pq: List[Tuple[float, int, int, List[int], List[Direction], int]] = [
            (0.0, counter, start_index, [start_index], [], 0)
        ]
        best_costs: Dict[int, float] = {start_index: 0.0}
        chosen_result: Optional[PathResult] = None

        while pq:
            cost, _, curr, path, actions, fuel = heapq.heappop(pq)

            if curr in targets:
                chosen_result = PathResult(
                    start=start_index,
                    target=curr,
                    path=path,
                    actions=actions,
                    route_length=len(actions),
                    movement_cost=cost,
                    fuel_consumption=fuel,
                    reachable=True,
                )
                break

            if cost > best_costs.get(curr, float("inf")):
                continue

            neighbors = self.grid.get_all_neighbors(curr, check_passable=True)
            for direction, nxt in neighbors.items():
                move_cost, fuel_cost = self.grid.get_movement_cost(curr, nxt, agent_kind)
                if move_cost == float("inf"):
                    continue

                new_cost = cost + move_cost
                new_fuel = fuel + fuel_cost

                if fuel_limit is not None and new_fuel > fuel_limit:
                    continue

                if new_cost < best_costs.get(nxt, float("inf")):
                    best_costs[nxt] = new_cost
                    counter += 1
                    heapq.heappush(
                        pq,
                        (
                            new_cost,
                            counter,
                            nxt,
                            path + [nxt],
                            actions + [direction],
                            new_fuel,
                        ),
                    )

        runtime = (time.perf_counter() - start_time) * 1000
        if chosen_result is not None:
            chosen_result.runtime_ms = runtime
            return chosen_result

        target_repr = next(iter(targets)) if targets else -1
        return PathResult(
            start=start_index,
            target=target_repr,
            runtime_ms=runtime,
            reachable=False,
        )

    def compute_all_distances(
        self, target_indices: Union[int, List[int], Set[int]], agent_kind: AgentKind = AgentKind.PATROL
    ) -> Tuple[Dict[int, float], Dict[int, Direction]]:
        """Compute shortest distance from all cells to the nearest target (reverse Dijkstra).
        
        Returns:
            distances: Dict mapping cell_idx -> min_cost to target
            policy: Dict mapping cell_idx -> optimal Direction toward target
        """
        if isinstance(target_indices, int):
            targets = {target_indices}
        else:
            targets = set(target_indices)

        distances: Dict[int, float] = {t: 0.0 for t in targets}
        policy: Dict[int, Direction] = {t: Direction.STAY for t in targets}

        for cell in range(self.grid.num_cells):
            if cell in targets:
                continue
            res = self.plan(cell, targets, agent_kind=agent_kind)
            if res.reachable and res.actions:
                distances[cell] = res.movement_cost
                policy[cell] = res.actions[0]
            else:
                distances[cell] = float("inf")
                policy[cell] = Direction.STAY

        return distances, policy
