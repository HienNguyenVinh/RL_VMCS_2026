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
        choices=["demo", "baseline", "dp", "marl", "hybrid", "server", "smoke_test"],
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
        "--mock",
        action="store_true",
        help="Run against a local mock PROCON server (ideal for Phase 1 verification without live server)",
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

    base_url = config.get("server", {}).get("base_url", "https://procon.ptit.edu.vn")
    match_id = os.getenv("PROCON_MATCH_ID", "")
    token = os.getenv("PROCON_TOKEN", "")

    mock_server = None
    if args.mock:
        from client.mock_server import MockProconServer
        mock_server = MockProconServer(total_days=2, start_425_count=1)
        base_url = mock_server.start()
        match_id = match_id or "mock_match_001"
        token = token or "mock_test_token"
        print(f"[*] Started local Mock PROCON Server at {base_url}")

    print(f"Mode: {args.mode}")
    print(f"Server Base URL: {base_url}")
    print(f"Match ID: {match_id if match_id else 'Not set'}")

    try:
        if args.mode == "demo":
            run_demo(config)
        elif args.mode == "baseline":
            from experiments.run_baseline_comparison import run_baseline_benchmark
            run_baseline_benchmark()
        elif args.mode == "dp":
            from experiments.run_dp import run_dp_experiment
            run_dp_experiment()
        elif args.mode == "marl":
            from experiments.run_marl import run_marl_experiment
            run_marl_experiment()
        elif args.mode == "hybrid":
            from experiments.run_hybrid import run_hybrid_benchmark
            run_hybrid_benchmark()
        elif args.mode in ("smoke_test", "server"):
            if not args.mock and (not match_id or not token):
                print("\n[ERROR] Missing PROCON_MATCH_ID or PROCON_TOKEN.")
                print("Please create a .env file from .env.example with your credentials,")
                print("or test with the mock server using: python main.py --mode smoke_test --mock")
                sys.exit(1)

            from client.http_client import ProconHttpClient
            from client.runner import MatchRunner

            client = ProconHttpClient(
                base_url=base_url,
                match_id=match_id,
                token=token,
                min_poll_interval=float(config.get("server", {}).get("poll_interval", 0.25)),
            )

            # In smoke_test mode: strategy is None -> all agents stay still ([-1] * daySteps)
            runner = MatchRunner(client=client, strategy_fn=None if args.mode == "smoke_test" else None)
            outcome = runner.run()
            print(f"\n[PHASE 1 COMPLETE] Match finished: {outcome}")

    finally:
        if mock_server:
            mock_server.stop()
            print("[*] Mock server stopped.")


if __name__ == "__main__":
    main()
