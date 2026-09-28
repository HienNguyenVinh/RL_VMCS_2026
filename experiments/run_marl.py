import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.protocol import Direction
from env.simulator import HexGridSimulator
from marl.iql import IndependentQLearning


def run_marl_experiment(episodes: int = 20):
    print(f"=== Running Multi-Agent RL (IQL) Experiments ({episodes} episodes) ===")
    sim = HexGridSimulator(width=10, height=10, day_steps=5, num_patrol=2, num_refuel=1, seed=42)
    iql = IndependentQLearning(num_agents=3, learning_rate=0.1, gamma=0.9, epsilon=0.5)

    for ep in range(episodes):
        state = sim.reset(seed=42 + ep)
        ep_reward = 0.0

        for step in range(sim.day_steps):
            # Select macro tasks
            task_assignments = iql.select_macro_tasks(state)
            
            # Map macro tasks to primitive directions (dummy random/greedy for pure marl test)
            actions = {a_id: Direction.RIGHT for a_id in task_assignments}
            
            next_state, rewards, done, info = sim.step(actions)
            ep_reward += sum(rewards.values())

            # Update IQL agents
            transitions = []
            for a_id, (macro_task, s_enc, action_idx) in task_assignments.items():
                r = rewards.get(a_id, 0.0)
                next_agent = next_state.agents[a_id]
                next_s_enc = iql.encoder.encode_agent_state(next_agent, next_state)
                transitions.append((a_id, s_enc, action_idx, r, next_s_enc, done))

            iql.update_agents(transitions)
            state = next_state
            if done:
                break

        iql.decay_exploration()
        if (ep + 1) % 5 == 0 or ep == episodes - 1:
            print(f"Episode {ep+1:2d}/{episodes} | Total Team Reward: {ep_reward:7.2f} | Epsilon: {iql.agents[0].epsilon:.3f}")


if __name__ == "__main__":
    run_marl_experiment()
