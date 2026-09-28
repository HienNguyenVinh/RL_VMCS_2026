"""Tabular Q-Learning Agent for macro-task decision making."""
import random
from typing import Any, Dict, List, Optional


class TabularQAgent:
    """Tabular Q-Learning Agent with epsilon-greedy action selection."""

    def __init__(
        self,
        agent_id: int,
        action_space_size: int,
        learning_rate: float = 0.1,
        gamma: float = 0.9,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
    ):
        self.agent_id = agent_id
        self.action_space_size = action_space_size
        self.lr = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Q-table: Dict[state_tuple, List[float]]
        self.q_table: Dict[Any, List[float]] = {}

    def get_q_values(self, state: Any) -> List[float]:
        """Get or initialize Q-values for a given discrete state."""
        if state not in self.q_table:
            self.q_table[state] = [0.0] * self.action_space_size
        return self.q_table[state]

    def select_action(self, state: Any, legal_actions: Optional[List[int]] = None) -> int:
        """Select action using epsilon-greedy policy."""
        actions = legal_actions if legal_actions is not None else list(range(self.action_space_size))
        if not actions:
            return 0

        # Exploration
        if random.random() < self.epsilon:
            return random.choice(actions)

        # Exploitation
        q_vals = self.get_q_values(state)
        best_val = -float("inf")
        best_actions = []

        for a in actions:
            val = q_vals[a]
            if val > best_val:
                best_val = val
                best_actions = [a]
            elif val == best_val:
                best_actions.append(a)

        return random.choice(best_actions)

    def update(
        self, state: Any, action: int, reward: float, next_state: Any, done: bool = False
    ) -> float:
        """Perform Bellman Q-Learning update: Q(s, a) <- Q(s, a) + alpha * [r + gamma * max_a' Q(s', a') - Q(s, a)]."""
        curr_q = self.get_q_values(state)[action]
        next_max_q = 0.0 if done else max(self.get_q_values(next_state))

        td_target = reward + self.gamma * next_max_q
        td_error = td_target - curr_q
        self.q_table[state][action] = curr_q + self.lr * td_error

        return td_error

    def decay_epsilon(self) -> None:
        """Decay exploration rate epsilon."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
