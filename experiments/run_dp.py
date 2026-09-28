import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from env.hex_grid import HexGrid
from planner.policy_iteration import PolicyIteration
from planner.value_iteration import ValueIteration


def run_dp_experiment():
    print("=== Running Dynamic Programming Experiments (Hex Grid) ===")
    width, height = 15, 15
    grid = HexGrid(width=width, height=height)
    targets = [22, 112, 180]  # sample target spots

    # 1. Test Value Iteration
    start_time = time.perf_counter()
    vi = ValueIteration(grid, gamma=0.95, theta=1e-4)
    vi_policy, vi_values, vi_iters = vi.plan(targets)
    vi_time = time.perf_counter() - start_time
    print(f"[Value Iteration] Sweeps: {vi_iters} | Time: {vi_time*1000:.2f} ms | Max Value: {vi_values.max():.2f}")

    # 2. Test Policy Iteration
    start_time = time.perf_counter()
    pi = PolicyIteration(grid, gamma=0.95, theta=1e-4)
    pi_policy, pi_values, pi_iters, total_sweeps = pi.plan(targets)
    pi_time = time.perf_counter() - start_time
    print(f"[Policy Iteration] Policy Iters: {pi_iters} | Total Sweeps: {total_sweeps} | Time: {pi_time*1000:.2f} ms | Max Value: {pi_values.max():.2f}")

    # Compare policy agreement
    matching = sum(1 for s in range(grid.num_cells) if vi_policy[s] == pi_policy[s])
    print(f"Policy Agreement: {matching}/{grid.num_cells} cells ({matching / grid.num_cells * 100:.1f}%)")


if __name__ == "__main__":
    run_dp_experiment()
