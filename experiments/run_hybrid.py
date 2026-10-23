"""Comprehensive Multi-Seed Benchmark comparing Hybrid MARL+DP against all Baselines (Phase 7)."""
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from typing import Any, Dict, List
import matplotlib.pyplot as plt
import numpy as np

from env.simulator import HexGridSimulator
from experiments.experiment_logger import ExperimentLogger
from strategy import (
    DPOnlyStrategy,
    GreedyDPStrategy,
    GreedyDijkstraStrategy,
    GreedyStrategy,
    HybridMARLDPStrategy,
    IQLDijkstraStrategy,
    RandomStrategy,
)


def run_strategy_trial(
    strategy_name: str,
    strategy: Any,
    sim: HexGridSimulator,
    num_days: int = 5,
) -> Dict[str, float]:
    """Run one simulation trial over multiple match days with given strategy."""
    total_planning_time_ms = 0.0
    day_steps = sim.day_steps
    num_agents = len(sim.state.agents)

    for day in range(num_days):
        t0 = time.perf_counter()
        plan = strategy.plan_day(sim.state, day_steps)
        t1 = time.perf_counter()
        total_planning_time_ms += (t1 - t0) * 1000.0

        for step_idx in range(day_steps):
            step_actions = {a_id: plan[a_id][step_idx] for a_id in range(num_agents)}
            sim.step(step_actions)

        sim.state.day += 1
        sim.state.step = 0

    avg_latency = total_planning_time_ms / max(1, num_days)
    team_score = float(sim.state.total_team_score)
    fuel_consumed = float(sim.state.total_fuel_consumed)
    conflicts = float(sim.state.total_conflicts)
    fuel_efficiency = team_score / max(1.0, fuel_consumed)

    return {
        "score": team_score,
        "fuel": fuel_consumed,
        "conflicts": conflicts,
        "latency_ms": avg_latency,
        "fuel_efficiency": fuel_efficiency,
    }


def run_hybrid_comparison(
    seeds: List[int] = [42, 101, 777, 999],
    num_days: int = 5,
    day_steps: int = 8,
):
    print("=========================================================================================")
    print("   PTIT PROCON 2026: PHASE 7 HIERARCHICAL HYBRID MARL + DP BENCHMARK COMPARISON         ")
    print("=========================================================================================")
    print(f"Seeds: {seeds} | Days per match: {num_days} | Steps per day: {day_steps} | Map: 12x12\n")

    methods = [
        "B0 (Random)",
        "B1 (Greedy + Dijkstra)",
        "B2 (Greedy + DP)",
        "B3 (IQL + Dijkstra)",
        "Proposed (IQL + DP)",
    ]

    results: Dict[str, Dict[str, List[float]]] = {
        m: {"score": [], "fuel": [], "conflicts": [], "latency_ms": [], "fuel_efficiency": []}
        for m in methods
    }

    for seed in seeds:
        print(f"--- Running Evaluation on Seed {seed} ---")
        base_sim = HexGridSimulator(
            width=12,
            height=12,
            day_steps=day_steps,
            num_patrol=2,
            num_refuel=1,
            num_spots=5,
            fuel_limit_patrol=40,
            fuel_limit_refuel=80,
            seed=seed,
        )

        strategies = {
            "B0 (Random)": RandomStrategy(base_sim.grid, seed=seed),
            "B1 (Greedy + Dijkstra)": GreedyDijkstraStrategy(base_sim.grid),
            "B2 (Greedy + DP)": GreedyDPStrategy(base_sim.grid),
            "B3 (IQL + Dijkstra)": IQLDijkstraStrategy(
                base_sim.grid, num_agents=3, weights_dir="experiments/models/marl"
            ),
            "Proposed (IQL + DP)": HybridMARLDPStrategy(
                base_sim.grid, num_agents=3, weights_dir="experiments/models/marl"
            ),
        }

        for name, strat in strategies.items():
            base_sim.reset(seed=seed)
            trial_metrics = run_strategy_trial(name, strat, base_sim, num_days=num_days)
            for k, v in trial_metrics.items():
                results[name][k].append(v)
            print(
                f"  [{name:<22}] Score: {trial_metrics['score']:>4.0f} | "
                f"Fuel: {trial_metrics['fuel']:>4.0f} | "
                f"Conflicts: {trial_metrics['conflicts']:>3.0f} | "
                f"Latency: {trial_metrics['latency_ms']:>6.2f}ms"
            )

    # Summarize stats
    print("\n" + "=" * 105)
    print(f"{'Method':<24} | {'Team Score (Mean±Std)':<24} | {'Conflicts (Mean±Std)':<22} | {'Fuel (Mean±Std)':<18} | {'Latency/Day':<12}")
    print("=" * 105)

    summary_table = []
    for m in methods:
        scores = np.array(results[m]["score"])
        conflicts = np.array(results[m]["conflicts"])
        fuels = np.array(results[m]["fuel"])
        latencies = np.array(results[m]["latency_ms"])

        score_str = f"{scores.mean():>6.1f} ± {scores.std():>4.1f}"
        conflict_str = f"{conflicts.mean():>5.1f} ± {conflicts.std():>4.1f}"
        fuel_str = f"{fuels.mean():>5.1f} ± {fuels.std():>4.1f}"
        lat_str = f"{latencies.mean():>5.2f}ms"

        print(f"{m:<24} | {score_str:<24} | {conflict_str:<22} | {fuel_str:<18} | {lat_str:<12}")
        summary_table.append({
            "method": m,
            "score_mean": float(scores.mean()),
            "score_std": float(scores.std()),
            "conflict_mean": float(conflicts.mean()),
            "conflict_std": float(conflicts.std()),
            "fuel_mean": float(fuels.mean()),
            "fuel_std": float(fuels.std()),
            "latency_mean": float(latencies.mean()),
        })

    print("=" * 105)

    # Plot results
    plot_path = Path("plots/hybrid_comparison.png")
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("PROCON 2026: Hierarchical Hybrid MARL + DP vs Baselines (Phase 7)", fontsize=15, fontweight="bold")

    colors = ["#7f7f7f", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    x = np.arange(len(methods))

    # Subplot 1: Team Score
    means = [results[m]["score"] for m in methods]
    axes[0, 0].bar(x, [np.mean(v) for v in means], yerr=[np.std(v) for v in means], capsize=5, color=colors, alpha=0.85)
    axes[0, 0].set_title("Total Team Udon Score (Higher is Better)", fontweight="bold")
    axes[0, 0].set_ylabel("Udon Collected")
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels([m.split()[0] for m in methods], rotation=15)
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 2: Conflicts
    c_means = [results[m]["conflicts"] for m in methods]
    axes[0, 1].bar(x, [np.mean(v) for v in c_means], yerr=[np.std(v) for v in c_means], capsize=5, color=colors, alpha=0.85)
    axes[0, 1].set_title("Agent Conflicts / Contention (Lower is Better)", fontweight="bold")
    axes[0, 1].set_ylabel("Total Conflicts")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels([m.split()[0] for m in methods], rotation=15)
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 3: Fuel Consumed
    f_means = [results[m]["fuel"] for m in methods]
    axes[1, 0].bar(x, [np.mean(v) for v in f_means], yerr=[np.std(v) for v in f_means], capsize=5, color=colors, alpha=0.85)
    axes[1, 0].set_title("Fuel Consumption", fontweight="bold")
    axes[1, 0].set_ylabel("Fuel Units")
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels([m.split()[0] for m in methods], rotation=15)
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 4: Average Latency per Day
    l_means = [results[m]["latency_ms"] for m in methods]
    axes[1, 1].bar(x, [np.mean(v) for v in l_means], color=colors, alpha=0.85)
    axes[1, 1].axhline(1000.0, color="red", linestyle="--", label="PROCON Latency Limit (1000ms)")
    axes[1, 1].set_title("Decision Latency per Day (Must be < 1000ms)", fontweight="bold")
    axes[1, 1].set_ylabel("Milliseconds (ms)")
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels([m.split()[0] for m in methods], rotation=15)
    axes[1, 1].legend()
    axes[1, 1].grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"\n[OK] Comparison plot generated and saved to: {plot_path}")

    # Log to ExperimentLogger
    logger = ExperimentLogger()
    for item in summary_table:
        logger.log_run(
            run_id=f"EXP-003_{item['method'].replace(' ', '_').replace('(', '').replace(')', '')}",
            metadata={"phase": 7, "method": item["method"], "seeds": seeds, "num_days": num_days},
            metrics=item,
        )

    return summary_table


run_hybrid_benchmark = run_hybrid_comparison

if __name__ == "__main__":
    run_hybrid_comparison()

