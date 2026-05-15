from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable


BOARD_WIDTH = 10
BOARD_HEIGHT = 20
VISIBLE_NEXT = 5
LINES_PER_LEVEL = 10
LINE_CLEAR_SECONDS = 0.18
IMPACT_FLASH_SECONDS = 0.08
BASE_FALL_SECONDS = 0.80
MIN_FALL_SECONDS = 0.06
FALL_SPEED_FACTOR = 0.86

LINE_SCORES = {
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}

SOFT_DROP_POINTS = 1
HARD_DROP_POINTS = 2

STATE_START = "start"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_CLEARING = "clearing"
STATE_GAME_OVER = "game_over"

PIECE_KINDS = ("I", "O", "T", "S", "Z", "J", "L")

SHAPES: dict[str, tuple[tuple[tuple[int, int], ...], ...]] = {
    "I": (
        ((0, 1), (1, 1), (2, 1), (3, 1)),
        ((2, 0), (2, 1), (2, 2), (2, 3)),
        ((0, 2), (1, 2), (2, 2), (3, 2)),
        ((1, 0), (1, 1), (1, 2), (1, 3)),
    ),
    "O": (
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (2, 1)),
    ),
    "T": (
        ((1, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (1, 2)),
        ((1, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "S": (
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
        ((1, 1), (2, 1), (0, 2), (1, 2)),
        ((0, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "Z": (
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (1, 2), (2, 2)),
        ((1, 0), (0, 1), (1, 1), (0, 2)),
    ),
    "J": (
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (1, 1), (0, 2), (1, 2)),
    ),
    "L": (
        ((2, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (1, 2), (2, 2)),
        ((0, 1), (1, 1), (2, 1), (0, 2)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
    ),
}


@dataclass(frozen=True)
class Piece:
    kind: str
    x: int = 3
    y: int = 0
    rotation: int = 0

    def cells(self) -> tuple[tuple[int, int], ...]:
        return tuple((self.x + cx, self.y + cy) for cx, cy in SHAPES[self.kind][self.rotation])

    def moved(self, dx: int = 0, dy: int = 0) -> "Piece":
        return Piece(self.kind, self.x + dx, self.y + dy, self.rotation)

    def rotated(self, delta: int) -> "Piece":
        return Piece(self.kind, self.x, self.y, (self.rotation + delta) % 4)


class Board:
    def __init__(self, width: int = BOARD_WIDTH, height: int = BOARD_HEIGHT) -> None:
        self.width = width
        self.height = height
        self.grid: list[list[str | None]] = [
            [None for _ in range(width)] for _ in range(height)
        ]

    def clone_grid(self) -> list[list[str | None]]:
        return [row[:] for row in self.grid]

    def is_blocked(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y >= self.height:
            return True
        if y < 0:
            return False
        return self.grid[y][x] is not None

    def can_place(self, piece: Piece) -> bool:
        return all(not self.is_blocked(x, y) for x, y in piece.cells())

    def lock_piece(self, piece: Piece) -> tuple[tuple[int, int], ...]:
        locked: list[tuple[int, int]] = []
        for x, y in piece.cells():
            if y >= 0:
                self.grid[y][x] = piece.kind
                locked.append((x, y))
        return tuple(locked)

    def full_rows(self) -> list[int]:
        return [index for index, row in enumerate(self.grid) if all(row)]

    def clear_rows(self, rows: Iterable[int]) -> int:
        row_set = set(rows)
        kept = [row for index, row in enumerate(self.grid) if index not in row_set]
        cleared = self.height - len(kept)
        self.grid = [[None for _ in range(self.width)] for _ in range(cleared)] + kept
        return cleared


class SevenBag:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()
        self.queue: list[str] = []
        self.ensure(VISIBLE_NEXT + 1)

    def ensure(self, count: int) -> None:
        while len(self.queue) < count:
            bag = list(PIECE_KINDS)
            self.rng.shuffle(bag)
            self.queue.extend(bag)

    def pop(self) -> str:
        self.ensure(VISIBLE_NEXT + 1)
        kind = self.queue.pop(0)
        self.ensure(VISIBLE_NEXT + 1)
        return kind

    def peek(self, count: int = VISIBLE_NEXT) -> list[str]:
        self.ensure(count)
        return self.queue[:count]


class Game:
    def __init__(self, rng: Random | None = None) -> None:
        self.rng = rng or Random()
        self.state = STATE_START
        self.board = Board()
        self.bag = SevenBag(self.rng)
        self.current: Piece | None = None
        self.hold_kind: str | None = None
        self.hold_used = False
        self.score = 0
        self.lines = 0
        self.pieces_placed = 0
        self.clear_rows_pending: list[int] = []
        self.clear_started_at = 0.0
        self.impact_cells: tuple[tuple[int, int], ...] = ()
        self.impact_until = 0.0
        self.last_fall_at = 0.0

    @property
    def level(self) -> int:
        return self.lines // LINES_PER_LEVEL + 1

    @property
    def fall_seconds(self) -> float:
        return max(MIN_FALL_SECONDS, BASE_FALL_SECONDS * (FALL_SPEED_FACTOR ** (self.level - 1)))

    def start(self, now: float = 0.0) -> None:
        self.board = Board()
        self.bag = SevenBag(self.rng)
        self.current = None
        self.hold_kind = None
        self.hold_used = False
        self.score = 0
        self.lines = 0
        self.pieces_placed = 0
        self.clear_rows_pending = []
        self.impact_cells = ()
        self.impact_until = 0.0
        self.last_fall_at = now
        self.state = STATE_PLAYING
        self.spawn_next()

    def spawn_piece(self, kind: str) -> None:
        piece = Piece(kind)
        if self.board.can_place(piece):
            self.current = piece
            self.hold_used = False
            return
        self.current = piece
        self.state = STATE_GAME_OVER

    def spawn_next(self) -> None:
        self.spawn_piece(self.bag.pop())

    def move(self, dx: int, dy: int = 0) -> bool:
        if self.state != STATE_PLAYING or self.current is None:
            return False
        moved = self.current.moved(dx, dy)
        if self.board.can_place(moved):
            self.current = moved
            return True
        return False

    def soft_drop(self, now: float = 0.0) -> bool:
        if self.move(0, 1):
            self.score += SOFT_DROP_POINTS
            self.last_fall_at = now
            return True
        self.lock_current(now)
        return False

    def rotate(self, delta: int) -> bool:
        if self.state != STATE_PLAYING or self.current is None:
            return False
        rotated = self.current.rotated(delta)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)):
            candidate = rotated.moved(dx, dy)
            if self.board.can_place(candidate):
                self.current = candidate
                return True
        return False

    def hard_drop_distance(self, piece: Piece | None = None) -> int:
        if piece is None:
            piece = self.current
        if piece is None:
            return 0
        distance = 0
        while self.board.can_place(piece.moved(0, distance + 1)):
            distance += 1
        return distance

    def ghost_piece(self) -> Piece | None:
        if self.current is None:
            return None
        return self.current.moved(0, self.hard_drop_distance())

    def hard_drop(self, now: float = 0.0) -> int:
        if self.state != STATE_PLAYING or self.current is None:
            return 0
        distance = self.hard_drop_distance()
        self.current = self.current.moved(0, distance)
        self.score += distance * HARD_DROP_POINTS
        self.lock_current(now)
        return distance

    def hold(self) -> bool:
        if self.state != STATE_PLAYING or self.current is None or self.hold_used:
            return False
        current_kind = self.current.kind
        if self.hold_kind is None:
            self.hold_kind = current_kind
            self.spawn_next()
        else:
            swap_kind = self.hold_kind
            self.hold_kind = current_kind
            self.spawn_piece(swap_kind)
        self.hold_used = True
        return self.state == STATE_PLAYING

    def lock_current(self, now: float = 0.0) -> None:
        if self.current is None:
            return
        self.impact_cells = self.board.lock_piece(self.current)
        self.impact_until = now + IMPACT_FLASH_SECONDS
        self.current = None
        self.pieces_placed += 1
        full_rows = self.board.full_rows()
        if full_rows:
            self.clear_rows_pending = full_rows
            self.clear_started_at = now
            self.state = STATE_CLEARING
        else:
            self.spawn_next()
        self.last_fall_at = now

    def finish_line_clear(self) -> int:
        cleared = self.board.clear_rows(self.clear_rows_pending)
        if cleared:
            clear_level = self.level
            self.lines += cleared
            self.score += LINE_SCORES.get(cleared, 0) * clear_level
        self.clear_rows_pending = []
        self.state = STATE_PLAYING
        self.spawn_next()
        return cleared

    def tick(self, now: float) -> None:
        if self.state == STATE_CLEARING:
            if now - self.clear_started_at >= LINE_CLEAR_SECONDS:
                self.finish_line_clear()
            return
        if self.state != STATE_PLAYING:
            return
        if now - self.last_fall_at >= self.fall_seconds:
            if self.move(0, 1):
                self.last_fall_at = now
            else:
                self.lock_current(now)

    def toggle_pause(self, now: float | None = None) -> None:
        if self.state == STATE_PLAYING:
            self.state = STATE_PAUSED
        elif self.state == STATE_PAUSED:
            self.state = STATE_PLAYING
            if now is not None:
                self.last_fall_at = now
