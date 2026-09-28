"""Benchmark comparing BFS and Dijkstra path planning baselines with metrics."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random
from env.hex_grid import HexCoord, HexGrid, TerrainType, TrafficLevel
from planner.bfs import BFSPlanner
from planner.dijkstra import DijkstraPlanner


def run_baseline_benchmark(num_trials: int = 5):
    print("=== Running Baseline Path Planning Benchmark: BFS vs Dijkstra ===")
    width, height = 15, 15
    grid = HexGrid(width=width, height=height)

    # Populate some terrain
    rng = random.Random(42)
    for idx in range(grid.num_cells):
        r_val = rng.random()
        if r_val < 0.10:
            grid.cell_types[idx] = TerrainType.MOUNTAIN.value
        elif r_val < 0.15:
            grid.cell_types[idx] = TerrainType.POND.value
        elif r_val < 0.35:
            grid.cell_types[idx] = TerrainType.ROAD.value
            grid.traffic_levels[idx] = rng.choice([TrafficLevel.CLEAR.value, TrafficLevel.CROWDED.value])

    bfs = BFSPlanner(grid)
    dijkstra = DijkstraPlanner(grid)

    print(f"Map size: {width}x{height} ({grid.num_cells} cells) with mixed terrain.\n")
    print(f"{'Trial':<6} | {'Start->Target':<14} | {'BFS Cost':<9} | {'Dijkstra Cost':<14} | {'BFS Len':<8} | {'Dijkstra Len':<13} | {'BFS Time':<9} | {'Dijkstra Time':<13}")
    print("-" * 105)

    passable_cells = [i for i in range(grid.num_cells) if grid.is_passable(i)]
    pairs = [
        (passable_cells[0], passable_cells[len(passable_cells) // 4]),
        (passable_cells[10], passable_cells[len(passable_cells) // 2]),
        (passable_cells[20], passable_cells[-10]),
        (passable_cells[5], passable_cells[-1]),
        (passable_cells[15], passable_cells[70]),
    ][:num_trials]

    total_bfs_cost = 0.0
    total_dijkstra_cost = 0.0
    total_bfs_time = 0.0
    total_dijkstra_time = 0.0

    for i, (start, target) in enumerate(pairs, 1):
        res_bfs = bfs.plan(start, target)
        res_dijk = dijkstra.plan(start, target)

        if res_bfs.reachable and res_dijk.reachable:
            total_bfs_cost += res_bfs.movement_cost
            total_dijkstra_cost += res_dijk.movement_cost
            total_bfs_time += res_bfs.runtime_ms
            total_dijkstra_time += res_dijk.runtime_ms

            print(
                f"{i:<6} | {f'{start}->{target}':<14} | "
                f"{res_bfs.movement_cost:<9.1f} | {res_dijk.movement_cost:<14.1f} | "
                f"{res_bfs.route_length:<8} | {res_dijk.route_length:<13} | "
                f"{res_bfs.runtime_ms:<7.2f}ms | {res_dijk.runtime_ms:<11.2f}ms"
            )

    print("-" * 105)
    print(f"Total Movement Cost: BFS={total_bfs_cost:.1f} vs Dijkstra={total_dijkstra_cost:.1f} (Dijkstra savings: {total_bfs_cost - total_dijkstra_cost:.1f} cost units)")
    print(f"Average Runtime: BFS={total_bfs_time/len(pairs):.2f}ms vs Dijkstra={total_dijkstra_time/len(pairs):.2f}ms")


if __name__ == "__main__":
    run_baseline_benchmark()
