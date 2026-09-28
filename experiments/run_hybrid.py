import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.simulator import HexGridSimulator
from strategy.dp_only import DPOnlyStrategy
from strategy.greedy import GreedyStrategy
from strategy.hybrid import HybridMARLDPStrategy


def run_hybrid_benchmark():
    print("=== Running Hybrid MARL + DP Benchmark against Baselines ===")
    sim = HexGridSimulator(width=12, height=12, day_steps=6, num_patrol=2, num_refuel=1, seed=123)

    strategies = {
        "Greedy Baseline": GreedyStrategy(sim.grid),
        "DP Only": DPOnlyStrategy(sim.grid),
        "Hybrid MARL+DP": HybridMARLDPStrategy(sim.grid, num_agents=3),
    }

    for name, strategy in strategies.items():
        sim.reset(seed=123)
        state = sim.state

        if name == "DP Only":
            # For DP only, target spots
            targets = [s.pos for s in state.spots]
            plan = strategy.plan_day(state, sim.day_steps, targets)
        else:
            plan = strategy.plan_day(state, sim.day_steps)

        print(f"\n--- Strategy: {name} ---")
        print(f"Generated Day Action Plan for {len(plan)} agents (steps={len(plan[0])}):")
        for i, p in enumerate(plan):
            print(f"  Agent {i}: {p}")


if __name__ == "__main__":
    run_hybrid_benchmark()
