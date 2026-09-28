"""Hybrid MARL + DP Strategy for PTIT PROCON 2026."""
from typing import Dict, List, Optional
from client.protocol import ActionPlan, Direction
from env.hex_grid import HexGrid
from env.state import SimulationState
from marl.iql import IndependentQLearning
from planner.value_iteration import ValueIteration


class HybridMARLDPStrategy:
    """Hierarchical Strategy: Multi-Agent RL selects macro-tasks, Dynamic Programming plans optimal paths."""

    def __init__(
        self,
        grid: HexGrid,
        num_agents: int,
        gamma_dp: float = 0.95,
        gamma_marl: float = 0.90,
        lr_marl: float = 0.1,
    ):
        self.grid = grid
        self.num_agents = num_agents
        self.marl_coordinator = IndependentQLearning(
            num_agents=num_agents,
            learning_rate=lr_marl,
            gamma=gamma_marl,
        )
        self.dp_planner = ValueIteration(grid, gamma=gamma_dp)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """1. MARL assigns macro-task target for each agent.
        2. DP computes optimal route on hex grid for each target.
        3. Extract action sequences.
        """
        chosen_tasks = self.marl_coordinator.select_macro_tasks(sim_state)

        plan: ActionPlan = []
        for agent in sim_state.agents:
            a_id = agent.agent_id
            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            # Plan path toward agent's specific target using DP
            policy, _, _ = self.dp_planner.plan([target_pos])

            agent_plan: List[int] = []
            curr = agent.pos

            for _ in range(day_steps):
                action = policy.get(curr, Direction.STAY)
                agent_plan.append(action.value)
                nxt = self.grid.get_neighbor_index(curr, action)
                if nxt is not None:
                    curr = nxt

            plan.append(agent_plan)

        return plan
