"""Policy Iteration for Hex Grid MDP."""
from typing import Dict, List, Tuple
import numpy as np

from client.protocol import Direction
from env.hex_grid import HexGrid
from planner.policy_evaluation import IterativePolicyEvaluation


class PolicyIteration:
    """Finds optimal policy through alternating Policy Evaluation and Policy Improvement."""

    def __init__(
        self,
        grid: HexGrid,
        gamma: float = 0.95,
        theta: float = 1e-4,
        max_eval_iters: int = 500,
        max_policy_iters: int = 100,
    ):
        self.grid = grid
        self.gamma = gamma
        self.evaluator = IterativePolicyEvaluation(grid, gamma, theta, max_eval_iters)
        self.max_policy_iters = max_policy_iters
        self.sweeps_per_policy_iter: List[int] = []

    def plan(
        self,
        target_indices: List[int],
        step_cost: float = -1.0,
        target_reward: float = 50.0,
    ) -> Tuple[Dict[int, Direction], np.ndarray, int, int]:
        """Run Policy Iteration.
        
        Returns:
            deterministic_policy: Dict mapping state index -> optimal Direction
            V: State-value array
            policy_iters: Number of policy improvement steps
            total_eval_sweeps: Total Bellman sweeps across all evaluations
        """
        targets = set(target_indices)
        all_actions = Direction.all_movements()
        self.sweeps_per_policy_iter = []

        # Initialize uniform random policy
        policy: Dict[int, Dict[Direction, float]] = {}
        uniform_prob = 1.0 / len(all_actions)
        for s in range(self.grid.num_cells):
            policy[s] = {a: uniform_prob for a in all_actions}

        deterministic_policy: Dict[int, Direction] = {s: Direction.STAY for s in range(self.grid.num_cells)}
        total_eval_sweeps = 0
        policy_iters = 0

        for p_iter in range(self.max_policy_iters):
            policy_iters = p_iter + 1

            # 1. Policy Evaluation
            V, eval_sweeps = self.evaluator.evaluate(
                policy, target_indices, step_cost, target_reward
            )
            total_eval_sweeps += eval_sweeps
            self.sweeps_per_policy_iter.append(eval_sweeps)

            # 2. Policy Improvement
            policy_stable = True
            for s in range(self.grid.num_cells):
                if s in targets or not self.grid.is_passable(s):
                    deterministic_policy[s] = Direction.STAY
                    continue

                old_action = deterministic_policy[s]
                best_action = old_action
                best_q = -float("inf")

                for a in all_actions:
                    nxt_s = self.grid.get_neighbor_index(s, a)
                    if nxt_s is None or not self.grid.is_passable(nxt_s):
                        q_val = (step_cost - 10.0) + self.gamma * V[s]
                    elif nxt_s in targets:
                        q_val = target_reward
                    else:
                        move_cost = self.grid.get_move_cost(s, nxt_s)
                        q_val = (step_cost - move_cost) + self.gamma * V[nxt_s]

                    if q_val > best_q:
                        best_q = q_val
                        best_action = a

                if best_action != old_action:
                    policy_stable = False

                deterministic_policy[s] = best_action
                # Make policy deterministic for next evaluation
                policy[s] = {a: (1.0 if a == best_action else 0.0) for a in all_actions}

            if policy_stable:
                break

        return deterministic_policy, V, policy_iters, total_eval_sweeps

    def extract_route(
        self,
        start: int,
        target_indices: List[int],
        policy: Dict[int, Direction],
        max_steps: int = 100,
    ) -> Tuple[List[int], List[Direction], bool]:
        """Extract path and action sequence from policy with loop detection."""
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
                break

            visited.add(nxt)
            actions.append(act)
            path.append(nxt)
            curr = nxt

        return path, actions, (curr in targets)
