"""Independent Q-Learning (IQL) for Multi-Agent Cooperative Task Allocation."""
from typing import Any, Dict, List, Tuple

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
    ):
        self.num_agents = num_agents
        self.encoder = StateEncoder()
        self.allocator = TaskAllocator()

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

        for agent in sim_state.agents:
            a_id = agent.agent_id
            state_key = self.encoder.encode_agent_state(agent, sim_state)
            available_tasks = self.allocator.get_available_tasks_for_agent(agent, sim_state)
            legal_actions = list(range(len(available_tasks)))

            q_agent = self.agents[a_id]
            action_idx = q_agent.select_action(state_key, legal_actions)
            selected_task = available_tasks[action_idx]

            chosen_tasks[a_id] = (selected_task, state_key, action_idx)

        return chosen_tasks

    def update_agents(
        self,
        transitions: List[Tuple[int, Any, int, float, Any, bool]],
    ) -> Dict[int, float]:
        """Perform IQL update across all agent transitions.
        
        transitions: list of (agent_id, state, action, reward, next_state, done)
        """
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
