"""Hexagonal Grid representation, coordinate utilities, and terrain costs for PTIT PROCON 2026."""
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from client.protocol import AgentKind, Direction, MatchSetup


class TerrainType(IntEnum):
    """Terrain types defined in PTIT PROCON 2026 challenge (matching BTC)."""
    PLAIN = 0     # 0: Đất — 2 bước, 1 fuel
    ROAD = 1      # 1: Đường — 1-4 bước tùy lưu lượng, 2 fuel
    MOUNTAIN = 2  # 2: Núi — 3 bước, 2 fuel
    POND = 3      # 3: Ao — Không đi được (Blocked)


class TrafficLevel(IntEnum):
    """Traffic congestion levels on road cells."""
    CLEAR = 0      # Thông thoáng: 1 bước, 2 fuel
    CROWDED = 1    # Đông đúc: 2 bước, 2 fuel
    CONGESTED = 2  # Ùn tắc: 4 bước, 2 fuel


@dataclass(frozen=True)
class HexCoord:
    """Row and column coordinates on a hexagonal grid."""
    row: int
    col: int

    def to_index(self, width: int) -> int:
        """Convert 2D (row, col) to flat index."""
        return self.row * width + self.col

    @classmethod
    def from_index(cls, index: int, width: int) -> "HexCoord":
        """Convert flat index to 2D (row, col)."""
        return cls(row=index // width, col=index % width)

    def to_cube(self, layout: str = "even-r") -> Tuple[int, int, int]:
        """Convert offset coordinates to cube coordinates (q, r, s) where q + r + s == 0."""
        r = self.row
        c = self.col
        if layout == "even-r":
            q = c - (r + (r & 1)) // 2
        else:  # odd-r
            q = c - (r - (r & 1)) // 2
        r_coord = r
        s = -q - r_coord
        return (q, r_coord, s)

    def distance_to(self, other: "HexCoord", layout: str = "even-r") -> int:
        """Hexagonal Manhattan distance between two cells."""
        q1, r1, s1 = self.to_cube(layout)
        q2, r2, s2 = other.to_cube(layout)
        return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))


class HexGrid:
    """Hexagonal Grid management, neighbor calculation, and terrain/traffic properties.
    
    Layout: 'even-r' horizontal pointy-topped hexes (Khớp BTC Q1):
    - Direction 0: Up-Left (Trên-Trái)
    - Direction 1: Up-Right (Trên-Phải)
    - Direction 2: Right (Phải)
    - Direction 3: Down-Right (Dưới-Phải)
    - Direction 4: Down-Left (Dưới-Trái)
    - Direction 5: Left (Trái)
    - Direction -1: Stay still (Đứng yên)
    """

    EVEN_R_OFFSETS = {
        # Even rows (r % 2 == 0): DIRS_EVEN = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,0)] (dcol, drow)
        0: {
            Direction.UP_LEFT: (-1, 0),
            Direction.UP_RIGHT: (-1, 1),
            Direction.RIGHT: (0, 1),
            Direction.DOWN_RIGHT: (1, 1),
            Direction.DOWN_LEFT: (1, 0),
            Direction.LEFT: (0, -1),
        },
        # Odd rows (r % 2 == 1): DIRS_ODD = [(-1,-1),(0,-1),(1,0),(0,1),(-1,1),(-1,0)] (dcol, drow)
        1: {
            Direction.UP_LEFT: (-1, -1),
            Direction.UP_RIGHT: (-1, 0),
            Direction.RIGHT: (0, 1),
            Direction.DOWN_RIGHT: (1, 0),
            Direction.DOWN_LEFT: (1, -1),
            Direction.LEFT: (0, -1),
        },
    }

    def __init__(
        self,
        width: int,
        height: int,
        layout: str = "even-r",
        cell_types: Optional[List[int]] = None,
        traffic_levels: Optional[List[int]] = None,
    ):
        self.width = width
        self.height = height
        self.layout = layout
        self.num_cells = width * height
        self.cell_types = list(cell_types) if cell_types is not None else [TerrainType.PLAIN.value] * self.num_cells
        self.traffic_levels = list(traffic_levels) if traffic_levels is not None else [TrafficLevel.CLEAR.value] * self.num_cells

    @classmethod
    def from_setup(cls, setup: MatchSetup) -> "HexGrid":
        """Instantiate HexGrid from server MatchSetup."""
        num_cells = setup.width * setup.height
        cell_types = [TerrainType.PLAIN.value] * num_cells
        traffic_levels = [TrafficLevel.CLEAR.value] * num_cells

        # Check if cells is a 2D matrix (cells[row][col]) as defined by BTC
        if isinstance(setup.cells, list) and setup.cells and isinstance(setup.cells[0], list):
            for r in range(min(setup.height, len(setup.cells))):
                row_cells = setup.cells[r]
                for c in range(min(setup.width, len(row_cells))):
                    idx = r * setup.width + c
                    cell = row_cells[c]
                    if isinstance(cell, dict):
                        cell_types[idx] = cell.get("type", TerrainType.PLAIN.value)
                        traffic_levels[idx] = cell.get("traffic", TrafficLevel.CLEAR.value)
                    elif isinstance(cell, int):
                        cell_types[idx] = cell
        else:
            for idx, cell in enumerate(setup.cells):
                if idx < num_cells:
                    if isinstance(cell, dict):
                        cell_types[idx] = cell.get("type", TerrainType.PLAIN.value)
                        traffic_levels[idx] = cell.get("traffic", TrafficLevel.CLEAR.value)
                    elif isinstance(cell, int):
                        cell_types[idx] = cell

        return cls(
            width=setup.width,
            height=setup.height,
            cell_types=cell_types,
            traffic_levels=traffic_levels,
        )

    def is_valid_coord(self, row: int, col: int) -> bool:
        """Check if (row, col) is within grid boundaries."""
        return 0 <= row < self.height and 0 <= col < self.width

    def is_valid_index(self, index: int) -> bool:
        """Check if flat cell index is within grid boundaries."""
        return 0 <= index < self.num_cells

    def is_passable(self, index: int) -> bool:
        """Check if cell is passable (not a Pond/impassable obstacle)."""
        if not self.is_valid_index(index):
            return False
        return self.cell_types[index] != TerrainType.POND.value

    def get_neighbor(self, row: int, col: int, direction: Direction) -> Optional[HexCoord]:
        """Compute coordinate of neighbor in a given direction."""
        if direction == Direction.STAY:
            return HexCoord(row, col)

        parity = row % 2
        offsets = self.EVEN_R_OFFSETS[parity].get(direction)
        if not offsets:
            return None

        dr, dc = offsets
        nr, nc = row + dr, col + dc

        if self.is_valid_coord(nr, nc):
            return HexCoord(nr, nc)
        return None

    def get_neighbor_index(self, index: int, direction: Direction) -> Optional[int]:
        """Compute neighbor flat index in a given direction."""
        coord = HexCoord.from_index(index, self.width)
        nxt = self.get_neighbor(coord.row, coord.col, direction)
        return nxt.to_index(self.width) if nxt else None

    def get_all_neighbors(self, index: int, check_passable: bool = False) -> Dict[Direction, int]:
        """Get all valid neighbor indices for a given cell index."""
        neighbors = {}
        for d in Direction.all_movements():
            nxt_idx = self.get_neighbor_index(index, d)
            if nxt_idx is not None:
                if not check_passable or self.is_passable(nxt_idx):
                    neighbors[d] = nxt_idx
        return neighbors

    def get_movement_cost(
        self, from_index: int, to_index: int, agent_kind: AgentKind = AgentKind.PATROL
    ) -> Tuple[float, int]:
        """Calculate (step_cost, fuel_cost) according to PTIT PROCON 2026 specs.
        
        Rule: Movement cost is determined by the source cell (ô nguồn) when initiating movement.
        - Plain: 2 steps, 1 fuel (patrol)
        - Mountain: 3 steps, 2 fuel (patrol)
        - Pond: impassable (inf steps, inf fuel)
        - Road: 
            - Clear: 1 step, 2 fuel
            - Crowded: 2 steps, 2 fuel
            - Congested: 4 steps, 2 fuel
        Refuel agents consume 0 patrol fuel.
        """
        if from_index == to_index:
            # Stay action
            return (1.0, 0)

        # Validate that destination cell is passable
        if not self.is_passable(to_index):
            return (float("inf"), 999)

        if not self.is_valid_index(from_index):
            return (float("inf"), 999)

        terrain = self.cell_types[from_index]
        traffic = self.traffic_levels[from_index]

        if terrain == TerrainType.POND.value:
            return (float("inf"), 999)

        elif terrain == TerrainType.MOUNTAIN.value:
            step_cost = 3.0
            fuel_cost = 2 if agent_kind == AgentKind.PATROL else 0

        elif terrain == TerrainType.ROAD.value:
            if traffic == TrafficLevel.CONGESTED.value:
                step_cost = 4.0
            elif traffic == TrafficLevel.CROWDED.value:
                step_cost = 2.0
            else:
                step_cost = 1.0
            fuel_cost = 2 if agent_kind == AgentKind.PATROL else 0

        else:  # TerrainType.PLAIN
            step_cost = 2.0
            fuel_cost = 1 if agent_kind == AgentKind.PATROL else 0

        return (step_cost, fuel_cost)

    def get_move_cost(self, from_index: int, to_index: int) -> float:
        """Backward compatible helper returning step cost."""
        steps, _ = self.get_movement_cost(from_index, to_index, AgentKind.PATROL)
        return steps

    def format_agent_actions(
        self,
        start_pos: int,
        actions: List[int],
        agent_kind: AgentKind = AgentKind.PATROL,
        day_steps: int = 30,
        fuel: int = 1000,
    ) -> List[int]:
        """Format an action sequence into a valid server action list conforming to BTC protocol.

        Ensures:
        - Movement step costs (plain=2, mountain=3, road=1/2/4) are tracked accurately.
        - Steps do not exceed day_steps (prevents E_STEP_OVERFLOW).
        - Fuel consumption is respected.
        - Remaining step budget is padded with -(day_steps - used_steps).
        - Agents with no moves return [-day_steps].
        """
        curr = start_pos
        curr_fuel = fuel
        used_steps = 0
        safe_plan: List[int] = []

        for act in actions:
            if act < 0:
                # Negative value means stay for |act| steps
                stay_len = abs(act)
                if used_steps + stay_len <= day_steps:
                    safe_plan.append(-stay_len)
                    used_steps += stay_len
                else:
                    rem = day_steps - used_steps
                    if rem > 0:
                        safe_plan.append(-rem)
                        used_steps += rem
                    break
            else:
                dir_val = Direction(act) if not isinstance(act, Direction) else act
                nxt = self.get_neighbor_index(curr, dir_val)
                if nxt is None or not self.is_passable(nxt):
                    break
                s_cost, f_cost = self.get_movement_cost(curr, nxt, agent_kind)
                s_cost = int(s_cost)
                if used_steps + s_cost <= day_steps and curr_fuel >= f_cost:
                    safe_plan.append(act)
                    used_steps += s_cost
                    curr_fuel -= f_cost
                    curr = nxt
                else:
                    break

        if used_steps < day_steps:
            safe_plan.append(-(day_steps - used_steps))

        return safe_plan if safe_plan else [-day_steps]
