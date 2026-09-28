"""Tabular Q-Learning Agent for single-agent and multi-agent reinforcement learning."""
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Union


class TabularQAgent:
    """Tabular Q-Learning Agent with epsilon-greedy action selection, save/load, and decay."""

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
        self.epsilon_initial = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Q-table: Dict[state_key, List[float]]
        self.q_table: Dict[Any, List[float]] = {}

    def _state_key(self, state: Any) -> Any:
        if isinstance(state, (list, tuple)):
            return tuple(state)
        return state

    def get_q_values(self, state: Any, min_size: int = 0) -> List[float]:
        """Get or initialize Q-values for a given discrete state, ensuring at least min_size entries."""
        key = self._state_key(state)
        target_size = max(self.action_space_size, min_size)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * target_size
        elif len(self.q_table[key]) < target_size:
            self.q_table[key].extend([0.0] * (target_size - len(self.q_table[key])))
        return self.q_table[key]

    def select_action(self, state: Any, legal_actions: Optional[List[int]] = None) -> int:
        """Select action using epsilon-greedy policy."""
        actions = legal_actions if legal_actions is not None else list(range(self.action_space_size))
        if not actions:
            return 0

        # Exploration
        if random.random() < self.epsilon:
            return random.choice(actions)

        # Exploitation
        max_action = max(actions)
        q_vals = self.get_q_values(state, min_size=max_action + 1)
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
        """Perform Bellman Q-Learning update:
        Q(s, a) <- Q(s, a) + alpha * [r + gamma * max_a' Q(s', a') - Q(s, a)]
        """
        key = self._state_key(state)
        next_key = self._state_key(next_state)

        curr_q = self.get_q_values(key, min_size=action + 1)[action]
        next_max_q = 0.0 if done else max(self.get_q_values(next_key))

        td_target = reward + self.gamma * next_max_q
        td_error = td_target - curr_q
        self.q_table[key][action] = curr_q + self.lr * td_error

        return td_error


    def decay_epsilon(self) -> None:
        """Decay exploration rate epsilon."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, filepath: Union[str, Path]) -> None:
        """Save Q-table and agent configuration to JSON."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)

        serializable_table = {str(k): v for k, v in self.q_table.items()}
        data = {
            "agent_id": self.agent_id,
            "action_space_size": self.action_space_size,
            "learning_rate": self.lr,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "q_table": serializable_table,
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: Union[str, Path]) -> None:
        """Load Q-table and agent configuration from JSON."""
        target = Path(filepath)
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.agent_id = data.get("agent_id", self.agent_id)
        self.action_space_size = data.get("action_space_size", self.action_space_size)
        self.lr = data.get("learning_rate", self.lr)
        self.gamma = data.get("gamma", self.gamma)
        self.epsilon = data.get("epsilon", self.epsilon)
        self.epsilon_min = data.get("epsilon_min", self.epsilon_min)
        self.epsilon_decay = data.get("epsilon_decay", self.epsilon_decay)

        # Reconstruct table with evaluated tuple keys if applicable
        raw_table = data.get("q_table", {})
        self.q_table = {}
        for k, v in raw_table.items():
            try:
                # Try evaluating tuple string "(0, 1, 2)"
                parsed_key = eval(k) if (k.startswith("(") and k.endswith(")")) else k
            except Exception:
                parsed_key = k
            self.q_table[parsed_key] = v
