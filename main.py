"""Main entry point for PTIT PROCON 2026 DP-MARL Bot."""
import argparse
import logging
import os
import sys
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import load_config
from client.protocol import Direction, AgentKind
from env.hex_grid import HexCoord, HexGrid
from env.simulator import HexGridSimulator
from planner.policy_iteration import PolicyIteration
from planner.value_iteration import ValueIteration
from marl.iql import IndependentQLearning
from strategy.hybrid import HybridMARLDPStrategy


def setup_logger(log_level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_banner():
    banner = r"""
========================================================================
   ____  ____  ____  ____  ____  ____       ____  ____        __  __ 
  / __ \/ __ \/ __ \/ __ \/ __ \/ __ \     / __ \/ __ \      / / / / 
 / /_/ / /_/ / /_/ / /_/ / /_/ / /_/ /    / / / / /_/ /_____/ /_/ /  
/ ____/ _, _/ ____/ ____/ _, _/ ____/    / /_/ / ____/_____/ __  /   
\/   /_/ |_|\____/\____/_/ |_|\____/____/_____/_/         /_/ /_/    
                                  /_____/                            
 PTIT PROCON 2026 — Dynamic Programming & Multi-Agent RL Bot
========================================================================
    """
    print(banner)


def run_demo(config: dict):
    print(">>> Running End-to-End System Demonstration...")
    width = config.get("hex_grid", {}).get("width", 10)
    height = config.get("hex_grid", {}).get("height", 10)
    grid = HexGrid(width=width, height=height)

    print(f"1. Hex Grid initialized: {width}x{height} ({grid.num_cells} cells).")

    # Value Iteration test
    vi = ValueIteration(grid, gamma=0.95, theta=1e-4)
    target_pos = 45
    policy, values, sweeps = vi.plan([target_pos])
    print(f"2. Value Iteration converged in {sweeps} sweeps toward target cell {target_pos}.")

    # Offline Simulator & Hybrid Strategy test
    sim = HexGridSimulator(width=width, height=height, day_steps=5, num_patrol=2, num_refuel=1, seed=42)
    hybrid_strat = HybridMARLDPStrategy(sim.grid, num_agents=3)
    plan = hybrid_strat.plan_day(sim.state, sim.day_steps)
    print(f"3. Hybrid MARL+DP generated valid day plan for {len(plan)} agents:")
    for i, p in enumerate(plan):
        print(f"   Agent {i}: {p}")

    print("\n[SUCCESS] Phase 0 environment and modules validated successfully!")


def main():
    parser = argparse.ArgumentParser(description="PTIT PROCON 2026 DP-MARL Bot")
    parser.add_argument(
        "--mode",
        choices=["demo", "dp", "marl", "hybrid", "server"],
        default="demo",
        help="Execution mode (default: demo)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Validate module imports and exit",
    )

    args = parser.parse_args()

    if args.check_imports:
        print("[OK] All modules imported successfully without errors.")
        sys.exit(0)

    print_banner()
    config = load_config(args.config)
    setup_logger(config.get("logging", {}).get("level", "INFO"))

    print(f"Mode: {args.mode}")
    print(f"Server Base URL: {config.get('server', {}).get('base_url')}")
    print(f"Match ID: {os.getenv('PROCON_MATCH_ID', 'Not set (using offline mode)')}")

    if args.mode == "demo":
        run_demo(config)
    elif args.mode == "dp":
        from experiments.run_dp import run_dp_experiment
        run_dp_experiment()
    elif args.mode == "marl":
        from experiments.run_marl import run_marl_experiment
        run_marl_experiment()
    elif args.mode == "hybrid":
        from experiments.run_hybrid import run_hybrid_benchmark
        run_hybrid_benchmark()
    elif args.mode == "server":
        print("Server mode selected. Connects using client/http_client.py (Phase 1).")


if __name__ == "__main__":
    main()
