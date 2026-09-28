"""Phase 8 Tournament Benchmark: Multi-Agent Refueling Coordination & Fuel Management.
Evaluates the impact of Rendezvous Coordination vs Ad-hoc Refueling vs No Refueling
on long-horizon matches (8 days, low initial fuel).
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from typing import Any, Dict, List
import matplotlib.pyplot as plt
import numpy as np

from client.protocol import AgentKind, Direction
from env.hex_grid import HexCoord
from env.simulator import HexGridSimulator
from experiments.experiment_logger import ExperimentLogger
from marl.refuel_coordinator import RefuelCoordinator
from strategy.hybrid import HybridMARLDPStrategy


class AdHocRefuelStrategy:
    """Baseline: Refueler simply chases nearest patrol, but without rendezvous or schedule synchronization."""

    def __init__(self, base_hybrid: HybridMARLDPStrategy):
        self.hybrid = base_hybrid
        self.grid = base_hybrid.grid

    def plan_day(self, sim_state, day_steps: int):
        plan = self.hybrid.plan_day(sim_state, day_steps)
        # Override refueler to simply walk toward closest patrol
        patrols = [a for a in sim_state.agents if a.kind == AgentKind.PATROL]
        refuelers = [a for a in sim_state.agents if a.kind == AgentKind.REFUEL]

        for r in refuelers:
            if patrols and r.fuel > 0:
                r_coord = HexCoord.from_index(r.pos, self.grid.width)
                patrols.sort(key=lambda p: r_coord.distance_to(HexCoord.from_index(p.pos, self.grid.width)))
                target_p = patrols[0]
                p_res = self.hybrid.dijkstra_planner.plan(r.pos, target_p.pos, agent_kind=AgentKind.REFUEL, fuel_limit=r.fuel)
                r_acts = [a.value for a in p_res.actions]
                while len(r_acts) < day_steps:
                    r_acts.append(Direction.STAY.value)
                plan[r.agent_id] = r_acts[:day_steps]
        return plan


def run_tournament_trial(
    strategy_name: str,
    strategy: Any,
    sim: HexGridSimulator,
    num_days: int = 8,
) -> Dict[str, Any]:
    """Execute tournament match tracking fuel trajectories and starvation."""
    day_steps = sim.day_steps
    patrol_fuel_history: List[List[int]] = []
    stranded_steps = 0
    total_patrol_steps = 0

    for day in range(num_days):
        plan = strategy.plan_day(sim.state, day_steps)

        for step_idx in range(day_steps):
            step_actions = {a.agent_id: plan[a.agent_id][step_idx] for a in sim.state.agents}
            sim.step(step_actions)

            # Record fuel of patrol agents
            patrols = [a for a in sim.state.agents if a.kind == AgentKind.PATROL]
            step_fuels = [p.fuel for p in patrols]
            patrol_fuel_history.append(step_fuels)

            # Check for stranded patrol agents (fuel == 0)
            for p in patrols:
                total_patrol_steps += 1
                if p.fuel <= 0:
                    stranded_steps += 1

        sim.state.day += 1
        sim.state.step = 0

    patrols = [a for a in sim.state.agents if a.kind == AgentKind.PATROL]
    starvation_rate = (stranded_steps / max(1, total_patrol_steps)) * 100.0
    end_fuels = [p.fuel for p in patrols]
    avg_end_fuel = float(np.mean(end_fuels))
    fuel_failure_count = sum(1 for f in end_fuels if f == 0)

    return {
        "score": float(sim.state.total_team_score),
        "fuel_transferred": float(sim.state.total_fuel_transferred),
        "fuel_consumed": float(sim.state.total_fuel_consumed),
        "starvation_rate": starvation_rate,
        "fuel_failure_count": fuel_failure_count,
        "avg_end_fuel": avg_end_fuel,
        "fuel_history": patrol_fuel_history,
    }


def run_refuel_tournament(
    seeds: List[int] = [42, 101, 777, 999],
    num_days: int = 8,
    day_steps: int = 6,
):
    print("=========================================================================================")
    print("   PTIT PROCON 2026: PHASE 8 TOURNAMENT BENCHMARK (REFUELING COORDINATION & FUEL MGMT)  ")
    print("=========================================================================================")
    print(f"Seeds: {seeds} | Days: {num_days} | DaySteps: {day_steps} | Patrol Initial Fuel: 22 (Tight Budget)\n")

    configs = [
        "C1: No Refueling",
        "C2: Ad-Hoc Refueling",
        "C3: Rendezvous Coordination (Proposed)",
    ]

    results: Dict[str, Dict[str, List[float]]] = {
        c: {"score": [], "transferred": [], "starvation_rate": [], "fuel_failure": [], "avg_end_fuel": []}
        for c in configs
    }

    sample_histories: Dict[str, List[float]] = {}

    for seed in seeds:
        print(f"--- Running Tournament Match on Seed {seed} ---")
        sim_base = HexGridSimulator(
            width=12,
            height=12,
            day_steps=day_steps,
            num_patrol=2,
            num_refuel=1,
            num_spots=5,
            fuel_limit_patrol=22,  # Tight budget requiring refueling over 8 days
            fuel_limit_refuel=90,  # Refueler has ample reserve
            seed=seed,
        )

        strat_no_refuel = HybridMARLDPStrategy(
            sim_base.grid, num_agents=3, weights_dir="experiments/models/marl", enable_refueling=False
        )
        strat_ad_hoc = AdHocRefuelStrategy(
            HybridMARLDPStrategy(sim_base.grid, num_agents=3, weights_dir="experiments/models/marl", enable_refueling=False)
        )
        strat_rendezvous = HybridMARLDPStrategy(
            sim_base.grid, num_agents=3, weights_dir="experiments/models/marl", enable_refueling=True, low_fuel_threshold=0.40
        )

        match_strats = {
            "C1: No Refueling": strat_no_refuel,
            "C2: Ad-Hoc Refueling": strat_ad_hoc,
            "C3: Rendezvous Coordination (Proposed)": strat_rendezvous,
        }

        for c_name, strat in match_strats.items():
            sim_base.reset(seed=seed)
            res = run_tournament_trial(c_name, strat, sim_base, num_days=num_days)

            results[c_name]["score"].append(res["score"])
            results[c_name]["transferred"].append(res["fuel_transferred"])
            results[c_name]["starvation_rate"].append(res["starvation_rate"])
            results[c_name]["fuel_failure"].append(float(res["fuel_failure_count"]))
            results[c_name]["avg_end_fuel"].append(res["avg_end_fuel"])

            if seed == 42:
                # Save average patrol fuel across steps for plotting
                avg_traj = [float(np.mean(step_f)) for step_f in res["fuel_history"]]
                sample_histories[c_name] = avg_traj

            print(
                f"  [{c_name:<36}] Score: {res['score']:>4.0f} | "
                f"Transferred: {res['fuel_transferred']:>4.0f} | "
                f"Starvation: {res['starvation_rate']:>5.1f}% | "
                f"Stranded: {res['fuel_failure_count']:>2} | "
                f"End Fuel: {res['avg_end_fuel']:>4.1f}"
            )

    print("\n" + "=" * 115)
    print(f"{'Configuration':<38} | {'Team Score (Mean±Std)':<24} | {'Fuel Transferred':<18} | {'Starvation Rate':<18} | {'Stranded Agents':<12}")
    print("=" * 115)

    summary_records = []
    for c in configs:
        scores = np.array(results[c]["score"])
        transferred = np.array(results[c]["transferred"])
        starvations = np.array(results[c]["starvation_rate"])
        failures = np.array(results[c]["fuel_failure"])

        score_str = f"{scores.mean():>6.1f} ± {scores.std():>4.1f}"
        trans_str = f"{transferred.mean():>6.1f} ± {transferred.std():>4.1f}"
        starv_str = f"{starvations.mean():>5.1f}% ± {starvations.std():>4.1f}%"
        fail_str = f"{failures.mean():>4.1f} ± {failures.std():>3.1f}"

        print(f"{c:<38} | {score_str:<24} | {trans_str:<18} | {starv_str:<18} | {fail_str:<12}")
        summary_records.append({
            "config": c,
            "score_mean": float(scores.mean()),
            "score_std": float(scores.std()),
            "transferred_mean": float(transferred.mean()),
            "transferred_std": float(transferred.std()),
            "starvation_mean": float(starvations.mean()),
            "starvation_std": float(starvations.std()),
            "stranded_mean": float(failures.mean()),
        })

    print("=" * 115)

    # Plot results
    plot_path = Path("plots/refuel_tournament.png")
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("PROCON 2026: Phase 8 Fuel Management & Rendezvous Coordination Tournament", fontsize=15, fontweight="bold")

    colors = ["#d62728", "#ff7f0e", "#2ca02c"]
    x = np.arange(len(configs))

    # Subplot 1: Team Score
    scores_mean = [np.mean(results[c]["score"]) for c in configs]
    scores_std = [np.std(results[c]["score"]) for c in configs]
    axes[0, 0].bar(x, scores_mean, yerr=scores_std, capsize=5, color=colors, alpha=0.85)
    axes[0, 0].set_title("Total Team Udon Score (Higher is Better)", fontweight="bold")
    axes[0, 0].set_ylabel("Udon Collected")
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(["No Refuel", "Ad-Hoc", "Rendezvous"], fontsize=11)
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 2: Fuel Transferred
    t_mean = [np.mean(results[c]["transferred"]) for c in configs]
    t_std = [np.std(results[c]["transferred"]) for c in configs]
    axes[0, 1].bar(x, t_mean, yerr=t_std, capsize=5, color=colors, alpha=0.85)
    axes[0, 1].set_title("Total Fuel Transferred to Patrols (Units)", fontweight="bold")
    axes[0, 1].set_ylabel("Fuel Transferred")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(["No Refuel", "Ad-Hoc", "Rendezvous"], fontsize=11)
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 3: Starvation Rate
    s_mean = [np.mean(results[c]["starvation_rate"]) for c in configs]
    s_std = [np.std(results[c]["starvation_rate"]) for c in configs]
    axes[1, 0].bar(x, s_mean, yerr=s_std, capsize=5, color=colors, alpha=0.85)
    axes[1, 0].set_title("Patrol Fuel Starvation Rate % (Lower is Better)", fontweight="bold")
    axes[1, 0].set_ylabel("Starvation Rate (%)")
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(["No Refuel", "Ad-Hoc", "Rendezvous"], fontsize=11)
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 4: Patrol Fuel Trajectory Over Time (Seed 42)
    for c_idx, c in enumerate(configs):
        if c in sample_histories:
            traj = sample_histories[c]
            axes[1, 1].plot(traj, label=c.split(":")[1].strip(), color=colors[c_idx], linewidth=2.2)
    axes[1, 1].axhline(0, color="black", linestyle=":", alpha=0.7)
    axes[1, 1].axhline(8, color="red", linestyle="--", alpha=0.6, label="Low Fuel Threshold")
    axes[1, 1].set_title("Patrol Fuel Trajectory Over Match Steps (Seed 42)", fontweight="bold")
    axes[1, 1].set_xlabel("Match Steps (Day * DaySteps)")
    axes[1, 1].set_ylabel("Average Patrol Fuel")
    axes[1, 1].legend()
    axes[1, 1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    plt.close()
    print(f"\n[OK] Phase 8 Tournament plot generated and saved to: {plot_path}")

    # Log to ExperimentLogger
    logger = ExperimentLogger()
    for item in summary_records:
        logger.log_run(
            run_id=f"EXP-004_{item['config'].split(':')[1].strip().replace(' ', '_')}",
            metadata={"phase": 8, "config": item["config"], "seeds": seeds, "num_days": num_days},
            metrics=item,
        )

    return summary_records


if __name__ == "__main__":
    run_refuel_tournament()
