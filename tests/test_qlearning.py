"""Unit tests for Tabular Q-Learning, save/load, and Multi-Agent Independent Q-Learning."""
import tempfile
from pathlib import Path
import unittest

from env.simulator import HexGridSimulator
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

    def test_q_agent_save_and_load(self):
        agent = TabularQAgent(agent_id=1, action_space_size=3, learning_rate=0.2, gamma=0.8, epsilon=0.3)
        agent.update((0, 1), 2, 15.0, (0, 2), done=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "test_qtable.json"
            agent.save(path)
            self.assertTrue(path.exists())

            # Load into new agent
            new_agent = TabularQAgent(agent_id=1, action_space_size=3)
            new_agent.load(path)

            self.assertEqual(new_agent.lr, 0.2)
            self.assertEqual(new_agent.gamma, 0.8)
            self.assertAlmostEqual(new_agent.epsilon, 0.3)
            # Verify Q-values restored
            q_vals = new_agent.get_q_values((0, 1))
            self.assertAlmostEqual(q_vals[2], 3.0)  # 0 + 0.2 * 15

    def test_iql_initialization_and_decay(self):
        iql = IndependentQLearning(num_agents=3, epsilon=1.0, epsilon_decay=0.9, epsilon_min=0.1)
        self.assertEqual(len(iql.agents), 3)

        iql.decay_exploration()
        for agent in iql.agents.values():
            self.assertAlmostEqual(agent.epsilon, 0.9)

    def test_iql_multi_agent_save_and_load(self):
        iql = IndependentQLearning(num_agents=2, action_space_size=4)
        iql.agents[0].update((0, 0), 1, 10.0, (0, 1), done=False)
        iql.agents[1].update((1, 1), 2, 20.0, (1, 2), done=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir) / "marl_models"
            iql.save(dir_path)

            loaded_iql = IndependentQLearning(num_agents=2, action_space_size=4)
            loaded_iql.load(dir_path)

            self.assertAlmostEqual(loaded_iql.agents[0].get_q_values((0, 0))[1], 1.0)
            self.assertAlmostEqual(loaded_iql.agents[1].get_q_values((1, 1))[2], 2.0)

    def test_iql_macro_task_selection(self):
        sim = HexGridSimulator(width=8, height=8, day_steps=5, num_patrol=2, num_refuel=1, seed=42)
        iql = IndependentQLearning(num_agents=3)

        chosen = iql.select_macro_tasks(sim.state)
        self.assertEqual(len(chosen), 3)
        for a_id in (0, 1, 2):
            self.assertIn(a_id, chosen)
            task, s_enc, act_idx = chosen[a_id]
            self.assertIsNotNone(task)
            self.assertIsInstance(s_enc, tuple)


if __name__ == "__main__":
    unittest.main()
