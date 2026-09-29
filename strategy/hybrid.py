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

        # Sync grid traffic levels from current simulation state
        if hasattr(sim_state, "traffics") and sim_state.traffics is not None:
            self.grid.update_traffics(sim_state.traffics)

        assigned_plans: Dict[int, Any] = {}
        refuel_reqs: List[Any] = []
        available_refuelers: List[Any] = []

        # 0. Check Refueling coordination for low-fuel patrol agents
        if self.enable_refueling:
            refuel_reqs = self.refuel_coordinator.check_refuel_requests(sim_state, day_steps=day_steps)
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
                        meet_step = max(r_plan.patrol_arrival_step, r_plan.refuel_arrival_step)
                        assigned_plans[patrol_agent.agent_id] = (
                            r_plan.patrol_actions,
                            r_plan.rendezvous_cell,
                            meet_step,
                        )
                        assigned_plans[refuel_agent.agent_id] = (
                            r_plan.refuel_actions,
                            r_plan.rendezvous_cell,
                            meet_step,
                        )
                        refueler_idx += 1

        # 1. Compute DP cost-to-go maps for all active spots
        cost_maps, policy_maps = self.compute_dp_cost_to_go(sim_state)

        # 2. MARL selects coordinated macro-tasks
        chosen_tasks = self.select_macro_tasks(sim_state, cost_maps)

        plan: ActionPlan = []

        for agent in sim_state.agents:
            a_id = agent.agent_id

            # 1. Refuel agent without assigned rendezvous -> deploy centrally towards active spots
            if agent.kind == AgentKind.REFUEL and a_id not in assigned_plans:
                active_spots = [
                    s.pos for s in sim_state.spots
                    if s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if active_spots:
                    avg_r = sum(p // self.grid.width for p in active_spots) // len(active_spots)
                    avg_c = sum(p % self.grid.width for p in active_spots) // len(active_spots)
                    c_coord = HexCoord(avg_r, avg_c)
                    center_target = min(
                        active_spots,
                        key=lambda p: c_coord.distance_to(HexCoord.from_index(p, self.grid.width))
                    )
                    dist = HexCoord.from_index(agent.pos, self.grid.width).distance_to(
                        HexCoord.from_index(center_target, self.grid.width)
                    )
                    if dist > 2:
                        res = self.dijkstra_planner.plan(
                            start_index=agent.pos,
                            target_indices=center_target,
                            agent_kind=AgentKind.REFUEL,
                            fuel_limit=1000,
                        )
                        if res.reachable and res.actions:
                            r_actions = [a.value if hasattr(a, "value") else int(a) for a in res.actions]
                            plan.append(
                                self.grid.format_agent_actions(
                                    start_pos=agent.pos,
                                    actions=r_actions,
                                    agent_kind=AgentKind.REFUEL,
                                    day_steps=day_steps,
                                    fuel=1000,
                                )
                            )
                            continue
                plan.append([-day_steps])
                continue

            # 2. If agent is already assigned to a refueling rendezvous
            if a_id in assigned_plans:
                raw_actions, r_cell, meet_step = assigned_plans[a_id]
                if agent.kind == AgentKind.REFUEL:
                    plan.append(
                        self.grid.format_agent_actions(
                            start_pos=agent.pos,
                            actions=raw_actions,
                            agent_kind=agent.kind,
                            day_steps=day_steps,
                            fuel=agent.fuel,
                        )
                    )
                    continue

                # Patrol agent: after rendezvous at r_cell, continue chaining to nearest active Udon spots
                patrol_route = list(raw_actions[:meet_step])
                curr_pos = r_cell
                chain_visited = {agent.pos, curr_pos}
                while len(patrol_route) < day_steps:
                    next_candidates = [
                        s.pos for s in sim_state.spots
                        if s.pos not in chain_visited and s.current_stock > 0 and self.grid.is_passable(s.pos)
                    ]
                    if not next_candidates:
                        break
                    next_res = self.dijkstra_planner.plan(
                        start_index=curr_pos,
                        target_indices=next_candidates,
                        agent_kind=AgentKind.PATROL,
                        fuel_limit=agent.max_fuel,
                    )
                    if not next_res.reachable or not next_res.actions:
                        break
                    patrol_route.extend([a.value if hasattr(a, "value") else int(a) for a in next_res.actions])
                    curr_pos = next_res.path[-1]
                    chain_visited.add(curr_pos)

                agent_plan = self.grid.format_agent_actions(
                    start_pos=agent.pos,
                    actions=patrol_route,
                    agent_kind=agent.kind,
                    day_steps=day_steps,
                    fuel=agent.max_fuel,
                )
                plan.append(agent_plan)
                continue

            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            # 3. Determine primary target spot (avoid sitting still on already-visited cell)
            primary_target = target_pos
            if macro_task.task_type == "STANDBY" or primary_target == agent.pos or not self.grid.is_passable(primary_target):
                other_spots = [
                    s.pos for s in sim_state.spots
                    if s.pos != agent.pos and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if other_spots:
                    agent_coord = HexCoord.from_index(agent.pos, self.grid.width)
                    other_spots.sort(key=lambda p: agent_coord.distance_to(HexCoord.from_index(p, self.grid.width)))
                    primary_target = other_spots[0]
                else:
                    plan.append([-day_steps])
                    continue

            # 4. Extract route to primary target via DP or Dijkstra
            route_actions: List[int] = []
            if primary_target in policy_maps:
                policy = policy_maps[primary_target]
            else:
                policy, _, _ = self.dp_planner.plan([primary_target])

            path, actions, reached = self.dp_planner.extract_route(
                start=agent.pos,
                target_indices=[primary_target],
                policy=policy,
                max_steps=day_steps,
            )

            curr_chain_pos = agent.pos
            if reached and actions:
                route_actions = [a.value if hasattr(a, "value") else int(a) for a in actions]
                curr_chain_pos = primary_target
            else:
                d_res = self.dijkstra_planner.plan(
                    start_index=agent.pos,
                    target_indices=primary_target,
                    agent_kind=agent.kind,
                    fuel_limit=agent.fuel,
                )
                if d_res.reachable and d_res.actions:
                    route_actions = [a.value if hasattr(a, "value") else int(a) for a in d_res.actions]
                    curr_chain_pos = d_res.path[-1]

            # 5. Multi-spot chaining: continue visiting other spots with remaining steps
            chain_visited = {agent.pos, curr_chain_pos}
            while len(route_actions) < day_steps:
                next_candidates = [
                    s.pos for s in sim_state.spots
                    if s.pos not in chain_visited and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if not next_candidates:
                    break
                next_res = self.dijkstra_planner.plan(
                    start_index=curr_chain_pos,
                    target_indices=next_candidates,
                    agent_kind=agent.kind,
                    fuel_limit=agent.fuel,
                )
                if not next_res.reachable or not next_res.actions:
                    break
                route_actions.extend([a.value if hasattr(a, "value") else int(a) for a in next_res.actions])
                curr_chain_pos = next_res.path[-1]
                chain_visited.add(curr_chain_pos)

            # If patrol agent has low fuel and cannot get refueled today, preserve fuel buffer so it won't hit 0 tomorrow
            patrol_fuel = agent.fuel
            if agent.kind == AgentKind.PATROL and agent.fuel <= 25 and len(refuel_reqs) > len(available_refuelers):
                patrol_fuel = max(0, agent.fuel - 10)

            # Format actions to respect movement step costs and fuel limits without overflowing
            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=route_actions,
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=patrol_fuel,
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
        if hasattr(sim_state, "traffics") and sim_state.traffics is not None:
            self.grid.update_traffics(sim_state.traffics)

        chosen_tasks = self.marl_coordinator.select_macro_tasks(sim_state)
        plan: ActionPlan = []

        for agent in sim_state.agents:
            a_id = agent.agent_id
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            primary_target = target_pos
            if macro_task.task_type == "STANDBY" or primary_target == agent.pos or not self.grid.is_passable(primary_target):
                other_spots = [
                    s.pos for s in sim_state.spots
                    if s.pos != agent.pos and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if other_spots:
                    agent_coord = HexCoord.from_index(agent.pos, self.grid.width)
                    other_spots.sort(key=lambda p: agent_coord.distance_to(HexCoord.from_index(p, self.grid.width)))
                    primary_target = other_spots[0]
                else:
                    plan.append([-day_steps])
                    continue

            path_res = self.dijkstra_planner.plan(
                start_index=agent.pos,
                target_indices=primary_target,
                agent_kind=agent.kind,
                fuel_limit=agent.fuel,
            )

            route_actions: List[int] = []
            curr_chain_pos = agent.pos
            if path_res.reachable and path_res.actions:
                route_actions = [a.value if hasattr(a, "value") else int(a) for a in path_res.actions]
                curr_chain_pos = path_res.path[-1]

            # Multi-spot chaining
            chain_visited = {agent.pos, curr_chain_pos}
            while len(route_actions) < day_steps:
                next_candidates = [
                    s.pos for s in sim_state.spots
                    if s.pos not in chain_visited and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if not next_candidates:
                    break
                next_res = self.dijkstra_planner.plan(
                    start_index=curr_chain_pos,
                    target_indices=next_candidates,
                    agent_kind=agent.kind,
                    fuel_limit=agent.fuel,
                )
                if not next_res.reachable or not next_res.actions:
                    break
                route_actions.extend([a.value if hasattr(a, "value") else int(a) for a in next_res.actions])
                curr_chain_pos = next_res.path[-1]
                chain_visited.add(curr_chain_pos)

            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=route_actions,
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=agent.fuel,
            )
            plan.append(agent_plan)

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
