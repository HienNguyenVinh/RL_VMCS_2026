"""Multi-Agent Reinforcement Learning (IQL) Experiments & Ablation (Phase 6).
Evaluates cooperative task allocation, conflict penalties, shared vs individual reward,
and plots learning & conflict reduction curves.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import random
import matplotlib.pyplot as plt
import numpy as np

from client.protocol import Direction
from env.hex_grid import HexGrid
from env.simulator import HexGridSimulator
from marl.iql import IndependentQLearning


def run_marl_training(
    episodes: int = 120,
    with_conflict_penalty: bool = True,
    shared_weight: float = 0.7,
    seed: int = 42,
):
    sim = HexGridSimulator(
        width=10,
        height=10,
        day_steps=6,
        num_patrol=2,
        num_refuel=1,
        num_spots=3,
        seed=seed,
    )
    sim.reward_fn.shared_weight = shared_weight
    sim.reward_fn.individual_weight = 1.0 - shared_weight
    sim.reward_fn.conflict_penalty = -15.0 if with_conflict_penalty else 0.0

    iql = IndependentQLearning(
        num_agents=3,
        action_space_size=5,
        learning_rate=0.15,
        gamma=0.90,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.97,
        conflict_penalty=sim.reward_fn.conflict_penalty,
        shared_weight=shared_weight,
    )

    returns = []
    conflict_counts = []

    for ep in range(episodes):
        state = sim.reset(seed=seed + ep)
        ep_reward = 0.0
        ep_conflicts = 0

        for step in range(sim.day_steps):
            task_assignments = iql.select_macro_tasks(state)

            # Check duplicate target assignments between agents
            chosen_targets = [task[0].target_pos for task in task_assignments.values()]
            if len(chosen_targets) != len(set(chosen_targets)):
                ep_conflicts += 1

            # Move agents towards chosen targets (1-step primitive direction)
            step_actions = {}
            for a_id, (task, _, _) in task_assignments.items():
                curr = state.agents[a_id].pos
                if curr == task.target_pos:
                    step_actions[a_id] = Direction.STAY
                else:
                    # Move towards target
                    best_d = Direction.STAY
                    best_dist = 999
                    for d in Direction.all_movements():
                        nxt = sim.grid.get_neighbor_index(curr, d)
                        if nxt is not None and sim.grid.is_passable(nxt):
                            dist = sim.grid.get_neighbor(curr // 10, curr % 10, d).distance_to(
                                sim.grid.get_neighbor(task.target_pos // 10, task.target_pos % 10, Direction.STAY)
                            )
                            if dist < best_dist:
                                best_dist = dist
                                best_d = d
                    step_actions[a_id] = best_d

            next_state, rewards, done, info = sim.step(step_actions)
            ep_reward += sum(rewards.values())

            # IQL Transitions
            transitions = []
            for a_id, (macro_task, s_enc, action_idx) in task_assignments.items():
                r = rewards.get(a_id, 0.0)
                next_agent = next_state.agents[a_id]
                next_s_enc = iql.encoder.encode_agent_state(
                    next_agent, next_state, other_assignments=iql.last_assignments
                )
                transitions.append((a_id, s_enc, action_idx, r, next_s_enc, done))

            iql.update_agents(transitions)
            state = next_state
            if done:
                break

        iql.decay_exploration()
        returns.append(ep_reward)
        conflict_counts.append(ep_conflicts)

    return returns, conflict_counts, iql


def run_marl_experiment():
    print("=== Running Multi-Agent RL (IQL) Cooperative Allocation Experiments (Phase 6) ===")

    # 1. Train with Coordination (Conflict Penalty + Shared Team Reward)
    print("\n[1/3] Training IQL with Shared Reward & Conflict Penalty...")
    ret_coop, conf_coop, trained_iql = run_marl_training(episodes=100, with_conflict_penalty=True, shared_weight=0.7)

    # 2. Train without Conflict Penalty (Individualistic)
    print("[2/3] Training IQL without Conflict Penalty (Ablation)...")
    ret_indiv, conf_indiv, _ = run_marl_training(episodes=100, with_conflict_penalty=False, shared_weight=0.0)

    # 3. Random Baseline
    print("[3/3] Evaluating Random Action Baseline...")
    ret_rand = []
    conf_rand = []
    sim = HexGridSimulator(width=10, height=10, day_steps=6, num_patrol=2, num_refuel=1, num_spots=3, seed=999)
    rng = random.Random(999)
    for ep in range(50):
        sim.reset(seed=999 + ep)
        ep_ret = 0
        ep_conf = 0
        for _ in range(sim.day_steps):
            acts = {a.agent_id: rng.choice(Direction.all_movements()) for a in sim.state.agents}
            _, r, done, info = sim.step(acts)
            ep_ret += sum(r.values())
            ep_conf += info["conflicts"]
        ret_rand.append(ep_ret)
        conf_rand.append(ep_conf)

    initial_conf = np.mean(conf_coop[:20])
    final_conf = np.mean(conf_coop[-20:])
    initial_ret = np.mean(ret_coop[:20])
    final_ret = np.mean(ret_coop[-20:])
    rand_conf = np.mean(conf_rand)
    rand_ret = np.mean(ret_rand)

    print("\n--- BẢNG TỔNG HỢP KẾT QUẢ MULTI-AGENT RL (IQL) ---")
    print(f"{'Cấu hình':<30} | {'Team Reward (Đầu -> Cuối)':<28} | {'Conflict Rate':<18}")
    print("-" * 82)
    print(f"{'IQL + Conflict Penalty':<30} | {f'{initial_ret:6.1f} -> {final_ret:6.1f}':<28} | {f'{final_conf:.2f} / ep (giảm {((initial_conf - final_conf)/max(1, initial_conf))*100:.1f}%)':<18}")
    print(f"{'IQL không Penalty (Ablation)':<30} | {f'{np.mean(ret_indiv[:20]):6.1f} -> {np.mean(ret_indiv[-20:]):6.1f}':<28} | {f'{np.mean(conf_indiv[-20:]):.2f} / ep':<18}")
    print(f"{'Random Action Baseline':<30} | {f'{rand_ret:6.1f}':<28} | {f'{rand_conf:.2f} / ep':<18}")

    # Save models
    models_dir = Path("experiments/models/marl")
    models_dir.mkdir(parents=True, exist_ok=True)
    trained_iql.save(models_dir)
    print(f"\n[OK] Đã lưu mô hình IQL tại: {models_dir}")

    # Plot Coordination Curves
    plots_dir = Path("plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plots_dir / "marl_coordination_curve.png"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Plot 1: Team Return
    w = 8
    ax1.plot(range(1, len(ret_coop) - w + 2), np.convolve(ret_coop, np.ones(w)/w, mode="valid"), label="IQL (Shared + Penalty)", color="royalblue", lw=2)
    ax1.plot(range(1, len(ret_indiv) - w + 2), np.convolve(ret_indiv, np.ones(w)/w, mode="valid"), label="IQL (No Penalty)", color="darkorange", lw=1.8, linestyle=":")
    ax1.axhline(y=rand_ret, color="crimson", linestyle="--", label=f"Random ({rand_ret:.1f})")
    ax1.set_xlabel("Episode")
    ax1.set_ylabel("Team Return")
    ax1.set_title("Team Return Convergence")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend()

    # Plot 2: Conflict Reduction
    ax2.plot(range(1, len(conf_coop) - w + 2), np.convolve(conf_coop, np.ones(w)/w, mode="valid"), label="IQL (Shared + Penalty)", color="forestgreen", lw=2)
    ax2.plot(range(1, len(conf_indiv) - w + 2), np.convolve(conf_indiv, np.ones(w)/w, mode="valid"), label="IQL (No Penalty)", color="darkorange", lw=1.8, linestyle=":")
    ax2.axhline(y=rand_conf, color="crimson", linestyle="--", label=f"Random ({rand_conf:.1f})")
    ax2.set_xlabel("Episode")
    ax2.set_ylabel("Conflicts per Episode")
    ax2.set_title("Conflict Reduction Curve")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend()

    plt.suptitle("Phase 6: Multi-Agent Independent Q-Learning Coordination Analysis", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"[OK] Đã lưu biểu đồ phân tích phối hợp đa tác nhân tại: {plot_path}")


if __name__ == "__main__":
    run_marl_experiment()
