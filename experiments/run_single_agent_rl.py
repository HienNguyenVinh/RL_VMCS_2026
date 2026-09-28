"""Single-Agent Q-Learning Experiment (Phase 5).
Test Task: 1 Agent navigating on Hex Grid with 3 candidate targets.
Evaluates learning vs random baseline, multiple seeds, saves Q-table, and plots learning curves.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import random
import matplotlib.pyplot as plt
import numpy as np

from client.protocol import AgentKind, Direction
from env.hex_grid import HexCoord, HexGrid, TerrainType
from marl.q_agent import TabularQAgent


class SingleAgentGridworldEnv:
    """Simplified single-agent Gridworld environment with 3 candidate targets."""

    def __init__(self, width: int = 8, height: int = 8, seed: int = 42):
        self.width = width
        self.height = height
        self.grid = HexGrid(width, height)
        # Place targets with different values
        self.targets = {
            14: 20.0,   # Suboptimal near
            35: 50.0,   # High value mid
            58: 100.0,  # Best value far
        }
        self.start_pos = 0
        self.max_steps = 30
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> int:
        self.curr_pos = self.start_pos
        self.steps = 0
        return self.curr_pos

    def step(self, direction: Direction):
        self.steps += 1
        nxt = self.grid.get_neighbor_index(self.curr_pos, direction)

        if nxt is None or not self.grid.is_passable(nxt):
            # Invalid move / border hit
            reward = -2.0
            done = False
        else:
            self.curr_pos = nxt
            if self.curr_pos in self.targets:
                reward = self.targets[self.curr_pos]
                done = True
            else:
                reward = -0.5  # Step penalty
                done = False

        if self.steps >= self.max_steps:
            done = True

        return self.curr_pos, reward, done, {"steps": self.steps, "target": self.curr_pos}


def train_single_agent(episodes: int = 150, seeds: list = None, save_plot: bool = True):
    print("=== Running Single-Agent Q-Learning Experiments (Phase 5) ===")
    seeds = seeds or [42, 101, 777]
    all_seed_returns = []

    for seed in seeds:
        env = SingleAgentGridworldEnv(seed=seed)
        agent = TabularQAgent(
            agent_id=0,
            action_space_size=6,
            learning_rate=0.15,
            gamma=0.95,
            epsilon=1.0,
            epsilon_min=0.05,
            epsilon_decay=0.98,
        )

        returns = []
        for ep in range(episodes):
            s = env.reset()
            ep_reward = 0.0
            done = False

            while not done:
                legal_actions = [d.value for d in Direction.all_movements()]
                action_idx = agent.select_action(s, legal_actions)
                nxt_s, reward, done, _ = env.step(Direction(action_idx))
                agent.update(s, action_idx, reward, nxt_s, done)
                s = nxt_s
                ep_reward += reward

            agent.decay_epsilon()
            returns.append(ep_reward)

        all_seed_returns.append(returns)

    # Compute average performance
    mean_returns = np.mean(all_seed_returns, axis=0)
    final_avg = np.mean(mean_returns[-20:])
    initial_avg = np.mean(mean_returns[:20])

    print(f"\nInitial Avg Return (First 20 eps): {initial_avg:.2f}")
    print(f"Final Avg Return (Last 20 eps):   {final_avg:.2f}")
    print(f"Improvement over training:        +{final_avg - initial_avg:.2f} points")

    # Evaluate vs Random Policy Baseline
    random_returns = []
    test_env = SingleAgentGridworldEnv(seed=999)
    for _ in range(50):
        s = test_env.reset()
        ep_ret = 0
        done = False
        while not done:
            act = test_env.rng.choice(Direction.all_movements())
            s, r, done, _ = test_env.step(act)
            ep_ret += r
        random_returns.append(ep_ret)

    rand_avg = np.mean(random_returns)
    print(f"Random Agent Baseline Avg Return: {rand_avg:.2f}")
    print(f"Trained Agent vs Random:          +{final_avg - rand_avg:.2f} points superior!")

    # Save trained model
    models_dir = Path("experiments/models")
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "single_agent_qtable.json"
    agent.save(model_path)
    print(f"[OK] Saved trained Q-table to {model_path}")

    # Plot learning curve
    if save_plot:
        plots_dir = Path("plots")
        plots_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plots_dir / "single_agent_qlearning.png"

        plt.figure(figsize=(9, 5))
        # Window moving average
        window = 10
        smoothed = np.convolve(mean_returns, np.ones(window)/window, mode="valid")

        plt.plot(range(1, len(smoothed) + 1), smoothed, label=f"Trained Q-Learning (Smoothed w={window})", color="royalblue", lw=2.2)
        plt.axhline(y=rand_avg, color="crimson", linestyle="--", label=f"Random Baseline ({rand_avg:.1f})")
        plt.xlabel("Episode", fontsize=11)
        plt.ylabel("Episodic Return", fontsize=11)
        plt.title("Phase 5: Single-Agent Q-Learning Convergence Curve", fontsize=12, fontweight="bold")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend(fontsize=10)
        plt.tight_layout()
        plt.savefig(plot_path, dpi=200)
        plt.close()
        print(f"[OK] Saved learning curve plot to {plot_path}")

    return {
        "initial_avg": initial_avg,
        "final_avg": final_avg,
        "random_baseline": rand_avg,
        "model_path": str(model_path),
    }


if __name__ == "__main__":
    train_single_agent()
