"""Independent Q-Learning (IQL) for Multi-Agent Cooperative Task Allocation (Phase 6)."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from client.protocol import AgentKind
from env.state import EnvAgent, SimulationState
from marl.q_agent import TabularQAgent
from marl.state_encoder import StateEncoder
from marl.task_allocator import MacroTask, TaskAllocator


class IndependentQLearning:
    """Coordinates multiple TabularQAgents learning independently in a shared environment."""

    def __init__(
        self,
        num_agents: int,
        action_space_size: int = 6,
        learning_rate: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        conflict_penalty: float = -10.0,
        shared_weight: float = 0.7,
    ):
        self.num_agents = num_agents
        self.conflict_penalty = conflict_penalty
        self.shared_weight = shared_weight
        self.encoder = StateEncoder()
        self.allocator = TaskAllocator()
        self.last_assignments: Dict[int, int] = {}

        # Independent agent for each team member
        self.agents: Dict[int, TabularQAgent] = {
            i: TabularQAgent(
                agent_id=i,
                action_space_size=action_space_size,
                learning_rate=learning_rate,
                gamma=gamma,
                epsilon=epsilon,
                epsilon_min=epsilon_min,
                epsilon_decay=epsilon_decay,
            )
            for i in range(num_agents)
        }

    def select_macro_tasks(
        self, sim_state: SimulationState
    ) -> Dict[int, Tuple[MacroTask, Any, int]]:
        """For each agent, encode state and select a macro task.
        
        Returns:
            Dict mapping agent_id -> (chosen_task, state_encoding, action_index)
        """
        chosen_tasks: Dict[int, Tuple[MacroTask, Any, int]] = {}
        current_step_assignments: Dict[int, int] = {}

        for agent in sim_state.agents:
            a_id = agent.agent_id
            state_key = self.encoder.encode_agent_state(
                agent, sim_state, other_assignments=self.last_assignments
            )
            available_tasks = self.allocator.get_available_tasks_for_agent(agent, sim_state)
            legal_actions = list(range(len(available_tasks)))

            q_agent = self.agents[a_id]
            action_idx = q_agent.select_action(state_key, legal_actions)
            selected_task = available_tasks[action_idx]

            chosen_tasks[a_id] = (selected_task, state_key, action_idx)
            current_step_assignments[a_id] = action_idx

        self.last_assignments = current_step_assignments
        return chosen_tasks

    def update_agents(
        self,
        transitions: List[Tuple[int, Any, int, float, Any, bool]],
    ) -> Dict[int, float]:
        """Perform IQL update across all agent transitions."""
        errors = {}
        for a_id, state, action, reward, next_state, done in transitions:
            if a_id in self.agents:
                td_err = self.agents[a_id].update(state, action, reward, next_state, done)
                errors[a_id] = td_err
        return errors

    def decay_exploration(self) -> None:
        """Decay epsilon across all agents."""
        for agent in self.agents.values():
            agent.decay_epsilon()

    def save(self, dir_path: Union[str, Path]) -> None:
        """Save all agent Q-tables to directory."""
        target_dir = Path(dir_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        for a_id, agent in self.agents.items():
            agent.save(target_dir / f"agent_{a_id}_qtable.json")

    def load(self, dir_path: Union[str, Path]) -> None:
        """Load all agent Q-tables from directory."""
        target_dir = Path(dir_path)
        for a_id, agent in self.agents.items():
            model_file = target_dir / f"agent_{a_id}_qtable.json"
            if model_file.exists():
                agent.load(model_file)
