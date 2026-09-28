"""Task Allocator defining macro actions and targets for cooperative agents."""
from dataclasses import dataclass
from typing import Dict, List, Optional
from client.protocol import AgentKind
from env.state import EnvAgent, SimulationState, UdonSpot


@dataclass
class MacroTask:
    """A high-level task assigned to an agent."""
    task_id: int
    name: str
    target_pos: int
    task_type: str  # "COLLECT_UDON", "REFUEL_AGENT", "STANDBY"


class TaskAllocator:
    """Manages macro-task generation and mapping to cell targets."""

    def __init__(self, num_spots: int = 5):
        self.num_spots = num_spots

    def get_available_tasks_for_agent(
        self, agent: EnvAgent, sim_state: SimulationState
    ) -> List[MacroTask]:
        """Generate list of feasible macro-tasks for the given agent."""
        tasks: List[MacroTask] = []

        if agent.kind == AgentKind.PATROL:
            # Patrol agents can target any Udon spot that has stock
            for i, spot in enumerate(sim_state.spots):
                tasks.append(
                    MacroTask(
                        task_id=i,
                        name=f"Collect Udon from Spot {spot.spot_id}",
                        target_pos=spot.pos,
                        task_type="COLLECT_UDON",
                    )
                )
            # Standby task
            tasks.append(
                MacroTask(
                    task_id=len(sim_state.spots),
                    name="Standby",
                    target_pos=agent.pos,
                    task_type="STANDBY",
                )
            )
        else:
            # Refuel agents can support patrol agents
            for i, pa in enumerate(sim_state.agents):
                if pa.kind == AgentKind.PATROL:
                    tasks.append(
                        MacroTask(
                            task_id=i,
                            name=f"Support Patrol Agent {pa.agent_id}",
                            target_pos=pa.pos,
                            task_type="REFUEL_AGENT",
                        )
                    )
            # Standby task
            tasks.append(
                MacroTask(
                    task_id=len(tasks),
                    name="Standby",
                    target_pos=agent.pos,
                    task_type="STANDBY",
                )
            )

        return tasks
