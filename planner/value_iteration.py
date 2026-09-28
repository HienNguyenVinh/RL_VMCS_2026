"""Value Iteration for Hex Grid MDP."""
from typing import Dict, List, Tuple
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

    def plan(
        self,
        target_indices: List[int],
        step_cost: float = -1.0,
        target_reward: float = 50.0,
    ) -> Tuple[Dict[int, Direction], np.ndarray, int]:
        """Run Value Iteration until convergence.
        
        Returns:
            optimal_policy: Dict mapping cell index -> optimal Direction
            V: State-value array
            iterations: Number of Bellman optimality sweeps
        """
        V = np.zeros(self.grid.num_cells, dtype=np.float64)
        targets = set(target_indices)
        all_actions = Direction.all_movements()

        iterations = 0
        for iteration in range(self.max_iterations):
            delta = 0.0
            new_V = np.copy(V)

            for s in range(self.grid.num_cells):
                if s in targets:
                    new_V[s] = target_reward
                    continue

                best_val = -float("inf")
                for a in all_actions:
                    nxt_s = self.grid.get_neighbor_index(s, a)
                    if nxt_s is None:
                        val = (step_cost - 5.0) + self.gamma * V[s]
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
            if delta < self.theta:
                break

        # Extract deterministic policy greedily from V*
        policy: Dict[int, Direction] = {}
        for s in range(self.grid.num_cells):
            if s in targets:
                policy[s] = Direction.STAY
                continue

            best_a = Direction.STAY
            best_q = -float("inf")
            for a in all_actions:
                nxt_s = self.grid.get_neighbor_index(s, a)
                if nxt_s is None:
                    q = (step_cost - 5.0) + self.gamma * V[s]
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
