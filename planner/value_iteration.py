"""Value Iteration for Hex Grid MDP."""
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from client.protocol import Direction
from env.hex_grid import HexGrid


class ValueIteration:
    """Finds optimal value function and policy using Bellman optimality backup."""

    def __init__(
        self,
        grid: HexGrid,
        gamma: float = 0.95,
        theta: float = 1e-4,
        max_iterations: int = 1000,
    ):
        self.grid = grid
        self.gamma = gamma
        self.theta = theta
        self.max_iterations = max_iterations
        self.convergence_deltas: List[float] = []

    def _ensure_cache(self) -> None:
        """Cache static grid transitions and movement costs for ultra-fast vectorized Bellman updates."""
        current_traffic_tuple = tuple(self.grid.traffic_levels)
        if (
            hasattr(self, "_cached_traffic")
            and self._cached_traffic == current_traffic_tuple
            and hasattr(self, "_cached_num_cells")
            and self._cached_num_cells == self.grid.num_cells
        ):
            return

        num_cells = self.grid.num_cells
        all_actions = Direction.all_movements()
        num_actions = len(all_actions)

        neighbors = np.full((num_cells, num_actions), -1, dtype=np.int32)
        move_costs = np.full((num_cells, num_actions), 10.0, dtype=np.float64)
        is_passable = np.array([self.grid.is_passable(s) for s in range(num_cells)], dtype=bool)

        for s in range(num_cells):
            if not is_passable[s]:
                continue
            for a_idx, a in enumerate(all_actions):
                nxt = self.grid.get_neighbor_index(s, a)
                if nxt is not None and is_passable[nxt]:
                    neighbors[s, a_idx] = nxt
                    move_costs[s, a_idx] = self.grid.get_move_cost(s, nxt)

        self._cached_num_cells = num_cells
        self._cached_traffic = current_traffic_tuple
        self._cached_neighbors = neighbors
        self._cached_move_costs = move_costs
        self._cached_is_passable = is_passable
        self._cached_all_actions = all_actions

    def plan(
        self,
        target_indices: List[int],
        step_cost: float = -1.0,
        target_reward: float = 50.0,
    ) -> Tuple[Dict[int, Direction], np.ndarray, int]:
        """Run Value Iteration until convergence using vectorized Bellman optimality backup.
        
        Returns:
            optimal_policy: Dict mapping cell index -> optimal Direction
            V: State-value array of shape (num_cells,)
            iterations: Number of Bellman optimality sweeps
        """
        self._ensure_cache()
        num_cells = self._cached_num_cells
        neighbors = self._cached_neighbors
        move_costs = self._cached_move_costs
        is_passable = self._cached_is_passable
        all_actions = self._cached_all_actions

        targets_mask = np.isin(np.arange(num_cells), target_indices)

        is_target_nbr = np.isin(neighbors, target_indices)
        is_valid_nbr = (neighbors >= 0)

        # Base Bellman reward matrix:
        # If neighbor is a target: target_reward
        # Else if neighbor is valid & passable: step_cost - move_cost
        # Else (impassable/out-of-bounds): step_cost - 10.0
        R = np.where(
            is_target_nbr,
            target_reward,
            np.where(is_valid_nbr, step_cost - move_costs, step_cost - 10.0),
        )

        s_idx = np.arange(num_cells)[:, None]
        lookup_idx = np.where(is_valid_nbr, neighbors, s_idx)
        lookup_gamma = np.where(is_target_nbr, 0.0, self.gamma)

        V = np.zeros(num_cells, dtype=np.float64)
        V[~is_passable] = -100.0

        self.convergence_deltas = []
        iterations = 0

        for iteration in range(self.max_iterations):
            Q = R + lookup_gamma * V[lookup_idx]
            new_V = np.max(Q, axis=1)
            new_V[targets_mask] = target_reward
            new_V[~is_passable] = -100.0

            delta = float(np.max(np.abs(new_V - V)))
            V = new_V
            iterations = iteration + 1
            self.convergence_deltas.append(delta)

            if delta < self.theta:
                break

        # Extract deterministic policy greedily from Q*
        Q = R + lookup_gamma * V[lookup_idx]
        best_a_idx = np.argmax(Q, axis=1)

        policy: Dict[int, Direction] = {}
        for s in range(num_cells):
            if targets_mask[s] or not is_passable[s]:
                policy[s] = Direction.STAY
            else:
                policy[s] = all_actions[best_a_idx[s]]

        return policy, V, iterations

    def extract_route(
        self,
        start: int,
        target_indices: List[int],
        policy: Dict[int, Direction],
        max_steps: int = 100,
    ) -> Tuple[List[int], List[Direction], bool]:
        """Extract path and action sequence from policy, with loop detection.
        
        Returns:
            path: List of visited cell indices
            actions: List of Direction taken
            reached: True if reached any target, False if looped or timed out
        """
        targets = set(target_indices)
        curr = start
        path = [curr]
        actions: List[Direction] = []
        visited = {curr}

        for _ in range(max_steps):
            if curr in targets:
                return path, actions, True

            act = policy.get(curr, Direction.STAY)
            if act == Direction.STAY:
                break

            nxt = self.grid.get_neighbor_index(curr, act)
            if nxt is None or not self.grid.is_passable(nxt):
                break

            if nxt in visited and nxt not in targets:
                # Cycle / loop detected!
                break

            visited.add(nxt)
            actions.append(act)
            path.append(nxt)
            curr = nxt

        return path, actions, (curr in targets)
