"""Unit tests for Tabular Q-Learning and Independent Q-Learning."""
import unittest
from marl.iql import IndependentQLearning
from marl.q_agent import TabularQAgent


class TestQLearning(unittest.TestCase):
    def test_q_agent_update(self):
        agent = TabularQAgent(agent_id=0, action_space_size=4, learning_rate=0.5, gamma=0.9, epsilon=0.0)
        s0 = "state_0"
        s1 = "state_1"

        # Action 1 gives reward 10.0
        td_err = agent.update(s0, 1, 10.0, s1, done=False)
        self.assertAlmostEqual(td_err, 10.0)

        q_vals = agent.get_q_values(s0)
        self.assertAlmostEqual(q_vals[1], 5.0)  # 0 + 0.5 * (10 - 0)

        # Select action greedily (epsilon=0.0) -> should choose 1
        best_act = agent.select_action(s0)
        self.assertEqual(best_act, 1)

    def test_iql_initialization_and_decay(self):
        iql = IndependentQLearning(num_agents=3, epsilon=1.0, epsilon_decay=0.9, epsilon_min=0.1)
        self.assertEqual(len(iql.agents), 3)

        iql.decay_exploration()
        for agent in iql.agents.values():
            self.assertAlmostEqual(agent.epsilon, 0.9)


if __name__ == "__main__":
    unittest.main()
