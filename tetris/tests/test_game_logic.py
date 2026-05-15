import unittest
import curses
from random import Random

from terminal_tetris.game import Board, Game, LINE_SCORES, Piece, STATE_GAME_OVER, STATE_PAUSED, STATE_PLAYING
from terminal_tetris.renderer import handle_input


class FakeScreen:
    def __init__(self, keys: list[int]) -> None:
        self.keys = keys

    def getch(self) -> int:
        if self.keys:
            return self.keys.pop(0)
        return -1


class PieceTests(unittest.TestCase):
    def test_piece_rotation_cycles(self) -> None:
        piece = Piece("T")
        self.assertEqual(piece.rotated(1).rotation, 1)
        self.assertEqual(piece.rotated(-1).rotation, 3)
        self.assertEqual(piece.rotated(4).rotation, 0)


class BoardTests(unittest.TestCase):
    def test_collision_detection_against_walls_floor_and_blocks(self) -> None:
        board = Board()
        self.assertFalse(board.can_place(Piece("I", x=-1, y=0)))
        self.assertFalse(board.can_place(Piece("I", x=8, y=0)))
        self.assertFalse(board.can_place(Piece("I", x=3, y=19)))

        board.grid[1][4] = "O"
        self.assertFalse(board.can_place(Piece("T", x=3, y=0)))

    def test_line_clearing_compacts_board(self) -> None:
        board = Board()
        board.grid[19] = ["I"] * board.width
        board.grid[18][0] = "T"
        cleared = board.clear_rows(board.full_rows())
        self.assertEqual(cleared, 1)
        self.assertTrue(all(cell is None for cell in board.grid[0]))
        self.assertEqual(board.grid[19][0], "T")


class GameTests(unittest.TestCase):
    def test_hold_is_once_per_piece_and_swaps(self) -> None:
        game = Game(Random(2))
        game.start()
        first = game.current.kind
        self.assertTrue(game.hold())
        self.assertEqual(game.hold_kind, first)
        second = game.current.kind
        self.assertFalse(game.hold())
        self.assertEqual(game.current.kind, second)

        game.hard_drop()
        third = game.current.kind
        self.assertTrue(game.hold())
        self.assertEqual(game.current.kind, first)
        self.assertEqual(game.hold_kind, third)

    def test_hard_drop_distance_and_score(self) -> None:
        game = Game(Random(3))
        game.start()
        game.current = Piece("O", x=4, y=0)
        distance = game.hard_drop_distance()
        self.assertEqual(distance, 18)
        dropped = game.hard_drop()
        self.assertEqual(dropped, 18)
        self.assertEqual(game.score, 36)
        self.assertEqual(game.pieces_placed, 1)

    def test_scoring_for_line_clears(self) -> None:
        game = Game(Random(4))
        game.start()
        for y in (18, 19):
            game.board.grid[y] = ["Z"] * game.board.width
        game.clear_rows_pending = [18, 19]
        game.finish_line_clear()
        self.assertEqual(game.lines, 2)
        self.assertEqual(game.score, LINE_SCORES[2])

    def test_line_clear_score_uses_level_at_clear_start(self) -> None:
        game = Game(Random(5))
        game.start()
        game.lines = 9
        game.board.grid[19] = ["L"] * game.board.width
        game.clear_rows_pending = [19]
        game.finish_line_clear()
        self.assertEqual(game.lines, 10)
        self.assertEqual(game.level, 2)
        self.assertEqual(game.score, LINE_SCORES[1])


class InputTests(unittest.TestCase):
    def test_required_controls_are_mapped(self) -> None:
        game = Game(Random(6))
        game.start()
        game.current = Piece("T", x=4, y=0)

        self.assertTrue(handle_input(FakeScreen([curses.KEY_LEFT]), game, 1.0))
        self.assertEqual(game.current.x, 3)
        self.assertTrue(handle_input(FakeScreen([curses.KEY_RIGHT]), game, 1.0))
        self.assertEqual(game.current.x, 4)
        self.assertTrue(handle_input(FakeScreen([curses.KEY_DOWN]), game, 1.0))
        self.assertEqual(game.current.y, 1)
        self.assertEqual(game.score, 1)
        self.assertTrue(handle_input(FakeScreen([ord("z")]), game, 1.0))
        self.assertEqual(game.current.rotation, 3)
        self.assertTrue(handle_input(FakeScreen([curses.KEY_UP]), game, 1.0))
        self.assertEqual(game.current.rotation, 0)

        held = game.current.kind
        self.assertTrue(handle_input(FakeScreen([ord("c")]), game, 1.0))
        self.assertEqual(game.hold_kind, held)
        self.assertTrue(game.hold_used)

        self.assertTrue(handle_input(FakeScreen([ord("p")]), game, 1.0))
        self.assertEqual(game.state, STATE_PAUSED)
        self.assertTrue(handle_input(FakeScreen([ord("p")]), game, 2.0))
        self.assertEqual(game.state, STATE_PLAYING)
        self.assertFalse(handle_input(FakeScreen([ord("q")]), game, 2.0))

    def test_hard_drop_start_and_restart_controls(self) -> None:
        game = Game(Random(7))
        self.assertTrue(handle_input(FakeScreen([ord(" ")]), game, 1.0))
        self.assertEqual(game.state, STATE_PLAYING)

        game.current = Piece("O", x=4, y=0)
        self.assertTrue(handle_input(FakeScreen([ord(" ")]), game, 1.0))
        self.assertEqual(game.pieces_placed, 1)
        self.assertEqual(game.score, 36)

        game.state = STATE_GAME_OVER
        self.assertTrue(handle_input(FakeScreen([ord("r")]), game, 2.0))
        self.assertEqual(game.state, STATE_PLAYING)


if __name__ == "__main__":
    unittest.main()
