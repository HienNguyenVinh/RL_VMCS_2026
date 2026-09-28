"""Multi-Agent Reinforcement Learning package for cooperative task allocation."""
from marl.iql import IndependentQLearning
from marl.q_agent import TabularQAgent
from marl.refuel_coordinator import RefuelCoordinator, RefuelRequest, RendezvousPlan
from marl.state_encoder import StateEncoder
from marl.task_allocator import MacroTask, TaskAllocator

__all__ = [
    "TabularQAgent",
    "IndependentQLearning",
    "TaskAllocator",
    "MacroTask",
    "StateEncoder",
    "RefuelCoordinator",
    "RefuelRequest",
    "RendezvousPlan",
]

