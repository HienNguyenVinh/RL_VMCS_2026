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

    def plan(
        self,
        target_indices: List[int],
        step_cost: float = -1.0,
        target_reward: float = 50.0,
    ) -> Tuple[Dict[int, Direction], np.ndarray, int]:
        """Run Value Iteration until convergence.
        
        Returns:
            optimal_policy: Dict mapping cell index -> optimal Direction
            V: State-value array of shape (num_cells,)
            iterations: Number of Bellman optimality sweeps
        """
        V = np.zeros(self.grid.num_cells, dtype=np.float64)
        targets = set(target_indices)
        all_actions = Direction.all_movements()
        self.convergence_deltas = []

        iterations = 0
        for iteration in range(self.max_iterations):
            delta = 0.0
            new_V = np.copy(V)

            for s in range(self.grid.num_cells):
                if s in targets:
                    new_V[s] = target_reward
                    continue

                if not self.grid.is_passable(s):
                    new_V[s] = -100.0  # Impassable cell penalty
                    continue

                best_val = -float("inf")
                for a in all_actions:
                    nxt_s = self.grid.get_neighbor_index(s, a)
                    if nxt_s is None or not self.grid.is_passable(nxt_s):
                        val = (step_cost - 10.0) + self.gamma * V[s]
                    elif nxt_s in targets:
                        val = target_reward
                    else:
                        move_cost = self.grid.get_move_cost(s, nxt_s)
                        val = (step_cost - move_cost) + self.gamma * V[nxt_s]

                    if val > best_val:
                        best_val = val

                delta = max(delta, abs(best_val - V[s]))
                new_V[s] = best_val

            V = new_V
            iterations = iteration + 1
            self.convergence_deltas.append(float(delta))

            if delta < self.theta:
                break

        # Extract deterministic policy greedily from V*
        policy: Dict[int, Direction] = {}
        for s in range(self.grid.num_cells):
            if s in targets:
                policy[s] = Direction.STAY
                continue

            if not self.grid.is_passable(s):
                policy[s] = Direction.STAY
                continue

            best_a = Direction.STAY
            best_q = -float("inf")
            for a in all_actions:
                nxt_s = self.grid.get_neighbor_index(s, a)
                if nxt_s is None or not self.grid.is_passable(nxt_s):
                    q = (step_cost - 10.0) + self.gamma * V[s]
                elif nxt_s in targets:
                    q = target_reward
                else:
                    move_cost = self.grid.get_move_cost(s, nxt_s)
                    q = (step_cost - move_cost) + self.gamma * V[nxt_s]

                if q > best_q:
                    best_q = q
                    best_a = a
            policy[s] = best_a

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
