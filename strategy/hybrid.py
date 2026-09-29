"""Hybrid MARL + DP Strategy and IQL+Dijkstra Strategy for PTIT PROCON 2026."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from client.protocol import ActionPlan, AgentKind, Direction, validate_action_plan
from env.hex_grid import HexCoord, HexGrid
from env.state import EnvAgent, SimulationState, UdonSpot
from marl.iql import IndependentQLearning
from marl.refuel_coordinator import RefuelCoordinator, RefuelRequest, RendezvousPlan
from marl.state_encoder import StateEncoder
from marl.task_allocator import MacroTask, TaskAllocator
from planner.dijkstra import DijkstraPlanner
from planner.value_iteration import ValueIteration


class HybridMARLDPStrategy:
    """Hierarchical Strategy (Proposed Method):
    1. Multi-Agent RL (IQL) selects coordinated macro-tasks with conflict penalties.
    2. Dynamic Programming (Value Iteration) computes optimal minimum-cost routes.
    3. Low-level execution validates fuel, detects impossible targets, and applies fallback.
    4. Refueling Coordinator handles low-fuel requests and rendezvous time synchronization.
    """

    def __init__(
        self,
        grid: HexGrid,
        num_agents: int = 3,
        weights_dir: Optional[Union[str, Path]] = "experiments/models/marl",
        gamma_dp: float = 0.95,
        gamma_marl: float = 0.90,
        lr_marl: float = 0.1,
        evaluation_mode: bool = True,
        enable_refueling: bool = True,
        low_fuel_threshold: float = 0.35,
    ):
        self.grid = grid
        self.num_agents = num_agents
        self.enable_refueling = enable_refueling
        self.encoder = StateEncoder()
        self.allocator = TaskAllocator()
        self.dp_planner = ValueIteration(grid, gamma=gamma_dp)
        self.dijkstra_planner = DijkstraPlanner(grid)
        self.refuel_coordinator = RefuelCoordinator(
            grid, low_fuel_threshold=low_fuel_threshold
        )
        self.last_assignments: Dict[int, int] = {}


        # Initialize IQL coordinator
        self.marl_coordinator = IndependentQLearning(
            num_agents=num_agents,
            learning_rate=lr_marl,
            gamma=gamma_marl,
            conflict_penalty=-15.0,
            shared_weight=0.5,
        )

        # Load pre-trained weights if available
        if weights_dir is not None:
            w_path = Path(weights_dir)
            if w_path.exists():
                self.marl_coordinator.load(w_path)

        # Set evaluation mode (greedy exploitation)
        if evaluation_mode:
            for q_agent in self.marl_coordinator.agents.values():
                q_agent.epsilon = 0.0

    def compute_dp_cost_to_go(
        self, sim_state: SimulationState
    ) -> Tuple[Dict[int, Dict[int, float]], Dict[int, Dict[int, Direction]]]:
        """Compute DP cost-to-go maps from all cells to each active candidate spot."""
        cost_maps: Dict[int, Dict[int, float]] = {}
        policy_maps: Dict[int, Dict[int, Direction]] = {}

        for spot in sim_state.spots:
            if spot.current_stock > 0 and self.grid.is_passable(spot.pos):
                policy, V, _ = self.dp_planner.plan([spot.pos])
                policy_maps[spot.pos] = policy
                # Derive cost-to-go: distance to target reward
                target_val = 50.0
                costs = {}
                for cell in range(self.grid.num_cells):
                    if not self.grid.is_passable(cell):
                        costs[cell] = 999.0
                    else:
                        costs[cell] = max(0.0, target_val - float(V[cell]))
                cost_maps[spot.pos] = costs

        return cost_maps, policy_maps

    def select_macro_tasks(
        self,
        sim_state: SimulationState,
        cost_maps: Dict[int, Dict[int, float]],
    ) -> Dict[int, Tuple[MacroTask, Any, int]]:
        """Select coordinated macro-tasks for all agents incorporating DP cost-to-go."""
        chosen_tasks: Dict[int, Tuple[MacroTask, Any, int]] = {}
        current_step_assignments: Dict[int, int] = {}

        for agent in sim_state.agents:
            a_id = agent.agent_id
            # Build agent-specific cost-to-go mapping for spots
            agent_cost_to_go: Dict[int, float] = {}
            for spot_pos, c_map in cost_maps.items():
                agent_cost_to_go[spot_pos] = c_map.get(agent.pos, 99.0)

            # Encode state with DP cost-to-go
            state_key = self.encoder.encode_agent_state(
                agent=agent,
                sim_state=sim_state,
                other_assignments=self.last_assignments,
                cost_to_go=agent_cost_to_go,
            )

            available_tasks = self.allocator.get_available_tasks_for_agent(agent, sim_state)
            legal_actions = list(range(len(available_tasks)))

            q_agent = self.marl_coordinator.agents.get(a_id)
            if q_agent:
                action_idx = q_agent.select_action(state_key, legal_actions)
            else:
                action_idx = 0

            selected_task = available_tasks[action_idx]
            chosen_tasks[a_id] = (selected_task, state_key, action_idx)
            current_step_assignments[a_id] = action_idx

        self.last_assignments = current_step_assignments
        return chosen_tasks

    def _fallback_plan(
        self, agent: EnvAgent, sim_state: SimulationState, day_steps: int
    ) -> List[int]:
        """Fallback: Dijkstra to nearest reachable active spot, or stand still."""
        if agent.kind == AgentKind.REFUEL:
            return [-day_steps]

        active_spots = [
            s for s in sim_state.spots
            if s.current_stock > 0 and self.grid.is_passable(s.pos)
        ]
        if not active_spots or agent.fuel <= 0:
            return [-day_steps]

        # Find nearest spot via Hex distance
        agent_coord = HexCoord.from_index(agent.pos, self.grid.width)
        active_spots.sort(
            key=lambda s: agent_coord.distance_to(HexCoord.from_index(s.pos, self.grid.width))
        )
        target_indices = [s.pos for s in active_spots]

        path_res = self.dijkstra_planner.plan(
            start_index=agent.pos,
            target_indices=target_indices,
            agent_kind=agent.kind,
            fuel_limit=agent.fuel,
        )

        if not path_res.reachable or not path_res.actions:
            return [-day_steps]

        return self.grid.format_agent_actions(
            start_pos=agent.pos,
            actions=[a.value if hasattr(a, "value") else int(a) for a in path_res.actions],
            agent_kind=agent.kind,
            day_steps=day_steps,
            fuel=agent.fuel,
        )

    def plan_day(self, sim_state: SimulationState, day_steps: Any) -> ActionPlan:
        """Plan day steps for all agents combining Refueling coordination, MARL macro selection and DP path execution."""
        if isinstance(day_steps, list):
            day_steps = day_steps[sim_state.day] if 0 <= sim_state.day < len(day_steps) else 30
        elif not isinstance(day_steps, int) or day_steps <= 0:
            day_steps = 30

        assigned_plans: Dict[int, List[int]] = {}

        # 0. Check Refueling coordination for low-fuel patrol agents
        if self.enable_refueling:
            refuel_reqs = self.refuel_coordinator.check_refuel_requests(sim_state)
            available_refuelers = self.refuel_coordinator.get_available_refuel_agents(sim_state)

            refueler_idx = 0
            for req in refuel_reqs:
                if refueler_idx >= len(available_refuelers):
                    break
                patrol_agent = sim_state.get_agent(req.patrol_agent_id)
                refuel_agent = available_refuelers[refueler_idx]
                if patrol_agent and refuel_agent and patrol_agent.agent_id not in assigned_plans:
                    _, r_plan = self.refuel_coordinator.find_rendezvous_cell(
                        patrol=patrol_agent,
                        refuel=refuel_agent,
                        sim_state=sim_state,
                        day_steps=day_steps,
                    )
                    if r_plan:
                        assigned_plans[patrol_agent.agent_id] = r_plan.patrol_actions
                        assigned_plans[refuel_agent.agent_id] = r_plan.refuel_actions
                        refueler_idx += 1

        # 1. Compute DP cost-to-go maps for all active spots
        cost_maps, policy_maps = self.compute_dp_cost_to_go(sim_state)

        # 2. MARL selects coordinated macro-tasks
        chosen_tasks = self.select_macro_tasks(sim_state, cost_maps)

        plan: ActionPlan = []

        for agent in sim_state.agents:
            a_id = agent.agent_id

            # 1. Refuel agent without assigned rendezvous -> stay still
            if agent.kind == AgentKind.REFUEL and a_id not in assigned_plans:
                plan.append([-day_steps])
                continue

            # 2. If agent is already assigned to a refueling rendezvous, format and use that plan
            if a_id in assigned_plans:
                raw_plan = assigned_plans[a_id]
                plan.append(
                    self.grid.format_agent_actions(
                        start_pos=agent.pos,
                        actions=raw_plan,
                        agent_kind=agent.kind,
                        day_steps=day_steps,
                        fuel=agent.fuel,
                    )
                )
                continue

            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            # 3. Check standby or already at target
            if macro_task.task_type == "STANDBY" or target_pos == agent.pos:
                plan.append([-day_steps])
                continue

            # Detect impossible target (impassable cell)
            if not self.grid.is_passable(target_pos):
                plan.append(self._fallback_plan(agent, sim_state, day_steps))
                continue

            # 4. Use precomputed policy or run DP for specific target
            if target_pos in policy_maps:
                policy = policy_maps[target_pos]
            else:
                policy, _, _ = self.dp_planner.plan([target_pos])

            # Extract route via DP
            path, actions, reached = self.dp_planner.extract_route(
                start=agent.pos,
                target_indices=[target_pos],
                policy=policy,
                max_steps=day_steps,
            )

            # Check if DP succeeded
            if not reached or not actions:
                # Trigger Fallback 1: Dijkstra to nearest reachable target
                plan.append(self._fallback_plan(agent, sim_state, day_steps))
                continue

            # Format actions to respect movement step costs and fuel limits without overflowing
            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=[a.value if hasattr(a, "value") else int(a) for a in actions],
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=agent.fuel,
            )
            plan.append(agent_plan)

        # Validate action plan
        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan


class IQLDijkstraStrategy:
    """Baseline B3: MARL (IQL) task allocation + Dijkstra minimum-cost path planning."""

    def __init__(
        self,
        grid: HexGrid,
        num_agents: int = 3,
        weights_dir: Optional[Union[str, Path]] = "experiments/models/marl",
        evaluation_mode: bool = True,
    ):
        self.grid = grid
        self.num_agents = num_agents
        self.encoder = StateEncoder()
        self.allocator = TaskAllocator()
        self.dijkstra_planner = DijkstraPlanner(grid)
        self.last_assignments: Dict[int, int] = {}

        self.marl_coordinator = IndependentQLearning(
            num_agents=num_agents,
            conflict_penalty=-15.0,
            shared_weight=0.5,
        )

        if weights_dir is not None:
            w_path = Path(weights_dir)
            if w_path.exists():
                self.marl_coordinator.load(w_path)

        if evaluation_mode:
            for q_agent in self.marl_coordinator.agents.values():
                q_agent.epsilon = 0.0

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps using IQL task allocation and Dijkstra path planning."""
        chosen_tasks = self.marl_coordinator.select_macro_tasks(sim_state)
        plan: ActionPlan = []

        for agent in sim_state.agents:
            a_id = agent.agent_id
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            if macro_task.task_type == "STANDBY" or target_pos == agent.pos or not self.grid.is_passable(target_pos):
                plan.append([-day_steps])
                continue

            path_res = self.dijkstra_planner.plan(
                start_index=agent.pos,
                target_indices=target_pos,
                agent_kind=agent.kind,
                fuel_limit=agent.fuel,
            )

            if not path_res.reachable or not path_res.actions:
                plan.append([-day_steps])
                continue

            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=[a.value if hasattr(a, "value") else int(a) for a in path_res.actions],
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=agent.fuel,
            )
            plan.append(agent_plan)

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
