"""Unit tests for Hex Grid calculations and coordinates."""
import unittest
from client.protocol import Direction
from env.hex_grid import HexCoord, HexGrid


class TestHexGrid(unittest.TestCase):
    def setUp(self):
        self.width = 10
        self.height = 10
        self.grid = HexGrid(self.width, self.height)

    def test_coord_index_conversion(self):
        c = HexCoord(row=3, col=4)
        idx = c.to_index(self.width)
        self.assertEqual(idx, 34)

        c_restored = HexCoord.from_index(idx, self.width)
        self.assertEqual(c, c_restored)

    def test_stay_direction(self):
        nxt = self.grid.get_neighbor(2, 2, Direction.STAY)
        self.assertEqual(nxt, HexCoord(2, 2))

    def test_neighbor_bounds(self):
        # Top-left corner (0, 0)
        # Up-left is out of bounds
        nxt_ul = self.grid.get_neighbor(0, 0, Direction.UP_LEFT)
        self.assertIsNone(nxt_ul)

        # Right (0, 1) is valid
        nxt_r = self.grid.get_neighbor(0, 0, Direction.RIGHT)
        self.assertEqual(nxt_r, HexCoord(0, 1))

    def test_distance_symmetry(self):
        c1 = HexCoord(1, 2)
        c2 = HexCoord(4, 5)
        d1 = c1.distance_to(c2)
        d2 = c2.distance_to(c1)
        self.assertEqual(d1, d2)
        self.assertGreater(d1, 0)


if __name__ == "__main__":
    unittest.main()
