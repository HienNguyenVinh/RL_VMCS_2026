"""Reward calculation for MARL task allocation and DP routing."""
from typing import Dict, List, Tuple
from env.state import EnvAgent, SimulationState, UdonSpot


class RewardFunction:
    """Computes cooperative shared and individual rewards with conflict penalties."""

    def __init__(
        self,
        shared_weight: float = 0.7,
        individual_weight: float = 0.3,
        conflict_penalty: float = -10.0,
        step_cost: float = -0.1,
        out_of_fuel_penalty: float = -50.0,
        udon_reward_scale: float = 10.0,
    ):
        self.shared_weight = shared_weight
        self.individual_weight = individual_weight
        self.conflict_penalty = conflict_penalty
        self.step_cost = step_cost
        self.out_of_fuel_penalty = out_of_fuel_penalty
        self.udon_reward_scale = udon_reward_scale

    def compute_rewards(
        self,
        prev_state: SimulationState,
        curr_state: SimulationState,
        collected_per_agent: Dict[int, int],
        conflicts: List[Tuple[int, int]],
    ) -> Dict[int, float]:
        """Compute reward for each agent based on actions taken."""
        team_collected = sum(collected_per_agent.values())
        team_reward = team_collected * self.udon_reward_scale

        rewards = {}
        for agent in curr_state.agents:
            a_id = agent.agent_id
            indiv_reward = collected_per_agent.get(a_id, 0) * self.udon_reward_scale

            # Blend shared and individual
            r = self.shared_weight * team_reward + self.individual_weight * indiv_reward
            r += self.step_cost

            # Penalty if agent ran out of fuel
            if agent.fuel <= 0 and agent.is_active:
                r += self.out_of_fuel_penalty

            # Penalty if involved in conflicts
            agent_conflicts = sum(1 for (a1, a2) in conflicts if a_id in (a1, a2))
            r += agent_conflicts * self.conflict_penalty

            rewards[a_id] = r

        return rewards
