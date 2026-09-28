"""Run Dynamic Programming experiments: Value Iteration vs Policy Iteration vs Dijkstra."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import time
import matplotlib.pyplot as plt
import numpy as np

from env.hex_grid import HexGrid, TerrainType, TrafficLevel
from planner.dijkstra import DijkstraPlanner
from planner.policy_iteration import PolicyIteration
from planner.value_iteration import ValueIteration


def run_dp_experiment(save_plots: bool = True):
    print("=== Running Dynamic Programming Experiments (Hex Grid) ===")
    width, height = 15, 15
    grid = HexGrid(width=width, height=height)

    # Inject some varied terrain
    for i in range(grid.num_cells):
        if i % 17 == 0:
            grid.cell_types[i] = TerrainType.MOUNTAIN.value
        elif i % 23 == 0:
            grid.cell_types[i] = TerrainType.POND.value
        elif i % 7 == 0:
            grid.cell_types[i] = TerrainType.ROAD.value

    targets = [22, 112, 180]  # Sample target spots
    passable_targets = [t for t in targets if grid.is_passable(t)]

    # 1. Test Value Iteration
    start_time = time.perf_counter()
    vi = ValueIteration(grid, gamma=0.95, theta=1e-4)
    vi_policy, vi_values, vi_iters = vi.plan(passable_targets)
    vi_time = (time.perf_counter() - start_time) * 1000

    # 2. Test Policy Iteration
    start_time = time.perf_counter()
    pi = PolicyIteration(grid, gamma=0.95, theta=1e-4)
    pi_policy, pi_values, pi_iters, total_sweeps = pi.plan(passable_targets)
    pi_time = (time.perf_counter() - start_time) * 1000

    # 3. Test Dijkstra Baseline
    start_time = time.perf_counter()
    dijkstra = DijkstraPlanner(grid)
    dijkstra_dist, dijkstra_policy = dijkstra.compute_all_distances(passable_targets)
    dijkstra_time = (time.perf_counter() - start_time) * 1000

    # Compare Policy Agreement between VI and PI
    passable_cells = [s for s in range(grid.num_cells) if grid.is_passable(s)]
    matching_vi_pi = sum(1 for s in passable_cells if vi_policy[s] == pi_policy[s])
    agreement_vi_pi = (matching_vi_pi / len(passable_cells)) * 100

    matching_vi_dijk = sum(1 for s in passable_cells if vi_policy[s] == dijkstra_policy[s])
    agreement_vi_dijk = (matching_vi_dijk / len(passable_cells)) * 100

    print("\n--- BẢNG SO SÁNH HIỆU NĂNG: VI vs PI vs DIJKSTRA ---")
    print(f"{'Thuật toán':<20} | {'Sweeps / Steps':<16} | {'Runtime (ms)':<14} | {'Max Value':<12} | {'Độ tương đồng với VI':<22}")
    print("-" * 92)
    print(f"{'Value Iteration':<20} | {f'{vi_iters} sweeps':<16} | {f'{vi_time:.2f} ms':<14} | {f'{vi_values.max():.2f}':<12} | {'100.0% (Chuẩn)':<22}")
    print(f"{'Policy Iteration':<20} | {f'{pi_iters} iters ({total_sweeps} sw)':<16} | {f'{pi_time:.2f} ms':<14} | {f'{pi_values.max():.2f}':<12} | {f'{agreement_vi_pi:.1f}%':<22}")
    print(f"{'Dijkstra Baseline':<20} | {'N/A (Graph PQ)':<16} | {f'{dijkstra_time:.2f} ms':<14} | {'N/A (Cost-to-go)':<12} | {f'{agreement_vi_dijk:.1f}%':<22}")

    # Gamma sensitivity sweep
    print("\n--- KHẢO SÁT ẢNH HƯỞNG CỦA DISCOUNT FACTOR (GAMMA) TRÊN VALUE ITERATION ---")
    gamma_results = []
    for g in [0.80, 0.90, 0.95, 0.99]:
        t0 = time.perf_counter()
        vi_g = ValueIteration(grid, gamma=g, theta=1e-4)
        _, _, iters_g = vi_g.plan(passable_targets)
        t_g = (time.perf_counter() - t0) * 1000
        gamma_results.append((g, iters_g, t_g, vi_g.convergence_deltas))
        print(f"  gamma = {g:<4} -> Sweeps: {iters_g:<3} | Runtime: {t_g:.2f} ms")

    # Save convergence plot
    if save_plots:
        plots_dir = Path("plots")
        plots_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plots_dir / "dp_convergence.png"

        plt.figure(figsize=(9, 5))
        for g, iters_g, _, deltas in gamma_results:
            plt.plot(range(1, len(deltas) + 1), deltas, marker="o", markersize=3, label=f"gamma = {g} ({iters_g} sweeps)")

        plt.yscale("log")
        plt.xlabel("Bellman Optimality Sweep (k)", fontsize=11)
        plt.ylabel("Max Value Delta Δ (Log Scale)", fontsize=11)
        plt.title("Convergence of Value Iteration on Hex Grid (15x15)", fontsize=12, fontweight="bold")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend(fontsize=10)
        plt.tight_layout()
        plt.savefig(plot_path, dpi=200)
        plt.close()
        print(f"\n[OK] Đã lưu biểu đồ hội tụ Bellman sweep tại: {plot_path}")

    return {
        "vi_iters": vi_iters,
        "pi_iters": pi_iters,
        "vi_time_ms": vi_time,
        "pi_time_ms": pi_time,
        "agreement": agreement_vi_pi,
    }


if __name__ == "__main__":
    run_dp_experiment()
