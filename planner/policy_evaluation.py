"""Iterative Policy Evaluation for Hex Grid MDP."""
from typing import Dict, List, Tuple
import numpy as np

from client.protocol import Direction
from env.hex_grid import HexGrid


class IterativePolicyEvaluation:
    """Evaluates a given policy on the Hex Grid MDP using Bellman expectation backup."""

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

    def evaluate(
        self,
        policy: Dict[int, Dict[Direction, float]],
        target_indices: List[int],
        step_cost: float = -1.0,
        target_reward: float = 50.0,
    ) -> Tuple[np.ndarray, int]:
        """Compute state values V(s) under policy until convergence.
        
        Returns:
            V: numpy array of values of shape (num_cells,)
            iterations: number of sweeps until convergence
        """
        V = np.zeros(self.grid.num_cells, dtype=np.float64)
        targets = set(target_indices)

        iterations = 0
        for iteration in range(self.max_iterations):
            delta = 0.0
            new_V = np.copy(V)

            for s in range(self.grid.num_cells):
                if s in targets:
                    new_V[s] = target_reward
                    continue

                action_probs = policy.get(s, {})
                if not action_probs:
                    continue

                v_s = 0.0
                for action, prob in action_probs.items():
                    nxt_s = self.grid.get_neighbor_index(s, action)
                    if nxt_s is None:
                        # Out of bounds or invalid move
                        reward = step_cost - 5.0
                        expected_nxt_val = V[s]
                    elif nxt_s in targets:
                        reward = target_reward
                        expected_nxt_val = 0.0  # Terminal
                    else:
                        move_cost = self.grid.get_move_cost(s, nxt_s)
                        reward = step_cost - move_cost
                        expected_nxt_val = V[nxt_s]

                    v_s += prob * (reward + self.gamma * expected_nxt_val)

                delta = max(delta, abs(v_s - V[s]))
                new_V[s] = v_s

            V = new_V
            iterations = iteration + 1
            if delta < self.theta:
                break

        return V, iterations
