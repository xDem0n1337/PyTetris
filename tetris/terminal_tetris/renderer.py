from __future__ import annotations

import curses
import time
from typing import Callable

from .game import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    SHAPES,
    Game,
    Piece,
    STATE_CLEARING,
    STATE_GAME_OVER,
    STATE_PAUSED,
    STATE_PLAYING,
    STATE_START,
)


CELL_W = 2
BOARD_X = 18
BOARD_Y = 2
SIDE_GAP = 4
MIN_HEIGHT = 26
MIN_WIDTH = 70

KEY_ESCAPE = 27

COLOR_DEFAULT = 0
COLOR_I = 1
COLOR_O = 2
COLOR_T = 3
COLOR_S = 4
COLOR_Z = 5
COLOR_J = 6
COLOR_L = 7
COLOR_GHOST = 8
COLOR_BORDER = 9
COLOR_FLASH = 10
COLOR_TEXT = 11

PIECE_COLORS = {
    "I": COLOR_I,
    "O": COLOR_O,
    "T": COLOR_T,
    "S": COLOR_S,
    "Z": COLOR_Z,
    "J": COLOR_J,
    "L": COLOR_L,
}


class Renderer:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.has_color = False
        self.cursor_hidden = False
        self.setup_curses()

    def setup_curses(self) -> None:
        self.cursor_hidden = self.set_cursor(0)
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(0)
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            self.has_color = True
            color_defs = {
                COLOR_I: curses.COLOR_CYAN,
                COLOR_O: curses.COLOR_YELLOW,
                COLOR_T: curses.COLOR_MAGENTA,
                COLOR_S: curses.COLOR_GREEN,
                COLOR_Z: curses.COLOR_RED,
                COLOR_J: curses.COLOR_BLUE,
                COLOR_L: curses.COLOR_WHITE,
                COLOR_GHOST: curses.COLOR_WHITE,
                COLOR_BORDER: curses.COLOR_WHITE,
                COLOR_FLASH: curses.COLOR_WHITE,
                COLOR_TEXT: curses.COLOR_WHITE,
            }
            for pair, fg in color_defs.items():
                curses.init_pair(pair, fg, background)

    @staticmethod
    def set_cursor(visibility: int) -> bool:
        try:
            curses.curs_set(visibility)
        except curses.error:
            return False
        return True

    def attr(self, pair: int = COLOR_DEFAULT, extra: int = 0) -> int:
        if not self.has_color or pair == COLOR_DEFAULT:
            return extra
        return curses.color_pair(pair) | extra

    def draw(self, game: Game, now: float) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        if height < MIN_HEIGHT or width < MIN_WIDTH:
            self.center_text(0, "Terminal Tetris")
            self.center_text(2, f"Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}.")
            self.center_text(4, "Q quits.")
            self.stdscr.refresh()
            return
        if game.state == STATE_START:
            self.draw_start()
        else:
            self.draw_game(game, now)
            if game.state == STATE_PAUSED:
                self.draw_overlay("PAUSED", "Press P to resume    Q to quit")
            elif game.state == STATE_GAME_OVER:
                self.draw_game_over(game, now)
        self.stdscr.refresh()

    def draw_start(self) -> None:
        self.center_text(3, "TERMINAL TETRIS", self.attr(COLOR_TEXT, curses.A_BOLD))
        lines = [
            "Arrow keys move    Down soft drops    Space hard drops",
            "Z rotates counterclockwise    X or Up rotates clockwise",
            "C holds    P pauses    R restarts after game over    Q/Esc quits",
            "",
            "Press Enter or Space to start",
        ]
        for offset, text in enumerate(lines):
            self.center_text(7 + offset * 2, text)
        self.draw_piece_preview(BOARD_X + 7, 17, Piece("T"), "[]")

    def draw_game(self, game: Game, now: float) -> None:
        self.draw_board_frame()
        self.draw_locked_blocks(game, now)
        ghost = game.ghost_piece()
        if game.state == STATE_PLAYING and ghost is not None:
            self.draw_piece_cells(ghost, "..", self.attr(COLOR_GHOST))
        if game.current is not None and game.state in (STATE_PLAYING, STATE_CLEARING):
            self.draw_piece_cells(game.current, "[]", self.piece_attr(game.current.kind, curses.A_BOLD))
        self.draw_side_panel(game)

    def draw_board_frame(self) -> None:
        attr = self.attr(COLOR_BORDER)
        top = "+" + "-" * (BOARD_WIDTH * CELL_W) + "+"
        self.addstr(BOARD_Y - 1, BOARD_X - 1, top, attr)
        for y in range(BOARD_HEIGHT):
            self.addstr(BOARD_Y + y, BOARD_X - 1, "|", attr)
            self.addstr(BOARD_Y + y, BOARD_X + BOARD_WIDTH * CELL_W, "|", attr)
        bottom = "+" + "-" * (BOARD_WIDTH * CELL_W) + "+"
        self.addstr(BOARD_Y + BOARD_HEIGHT, BOARD_X - 1, bottom, attr)

    def draw_locked_blocks(self, game: Game, now: float) -> None:
        clear_flash = game.state == STATE_CLEARING and int((now - game.clear_started_at) * 24) % 2 == 0
        impact_flash = now < game.impact_until
        impact_cells = set(game.impact_cells)
        for y, row in enumerate(game.board.grid):
            for x, kind in enumerate(row):
                if kind is None:
                    continue
                text = "##"
                attr = self.piece_attr(kind)
                if y in game.clear_rows_pending and clear_flash:
                    text = "  "
                    attr = self.attr(COLOR_FLASH, curses.A_REVERSE)
                elif impact_flash and (x, y) in impact_cells:
                    attr = self.attr(COLOR_FLASH, curses.A_REVERSE | curses.A_BOLD)
                self.draw_cell(x, y, text, attr)

    def draw_side_panel(self, game: Game) -> None:
        screen_height, _ = self.stdscr.getmaxyx()
        side_x = BOARD_X + BOARD_WIDTH * CELL_W + SIDE_GAP
        self.addstr(BOARD_Y - 1, side_x, "STATS", self.attr(COLOR_TEXT, curses.A_BOLD))
        stats = [
            f"Score  {game.score}",
            f"Lines  {game.lines}",
            f"Level  {game.level}",
            f"Pieces {game.pieces_placed}",
        ]
        for index, stat in enumerate(stats):
            self.addstr(BOARD_Y + index + 1, side_x, stat)

        self.draw_box(side_x, BOARD_Y + 7, 10, 6, "HOLD")
        if game.hold_kind:
            self.draw_piece_preview(side_x + 2, BOARD_Y + 9, Piece(game.hold_kind), "[]")

        next_y = BOARD_Y + 15
        self.addstr(next_y - 1, side_x, "NEXT", self.attr(COLOR_TEXT, curses.A_BOLD))
        visible_next = max(3, min(5, (screen_height - next_y - 1) // 4))
        for index, kind in enumerate(game.bag.peek(visible_next)):
            y = next_y + index * 4
            self.draw_piece_preview(side_x, y, Piece(kind), "[]")

    def draw_box(self, x: int, y: int, width: int, height: int, title: str) -> None:
        attr = self.attr(COLOR_BORDER)
        self.addstr(y, x, "+" + "-" * (width - 2) + "+", attr)
        for row in range(1, height - 1):
            self.addstr(y + row, x, "|", attr)
            self.addstr(y + row, x + width - 1, "|", attr)
        self.addstr(y + height - 1, x, "+" + "-" * (width - 2) + "+", attr)
        self.addstr(y, x + 2, f" {title} ", self.attr(COLOR_TEXT, curses.A_BOLD))

    def draw_piece_preview(self, x: int, y: int, piece: Piece, text: str) -> None:
        cells = SHAPES[piece.kind][0]
        min_x = min(cx for cx, _ in cells)
        min_y = min(cy for _, cy in cells)
        for cx, cy in cells:
            self.addstr(y + cy - min_y, x + (cx - min_x) * CELL_W, text, self.piece_attr(piece.kind, curses.A_BOLD))

    def draw_piece_cells(self, piece: Piece, text: str, attr: int) -> None:
        for x, y in piece.cells():
            if y >= 0:
                self.draw_cell(x, y, text, attr)

    def draw_cell(self, x: int, y: int, text: str, attr: int) -> None:
        self.addstr(BOARD_Y + y, BOARD_X + x * CELL_W, text, attr)

    def piece_attr(self, kind: str, extra: int = 0) -> int:
        return self.attr(PIECE_COLORS[kind], extra)

    def draw_overlay(self, title: str, subtitle: str) -> None:
        width = max(len(title), len(subtitle)) + 6
        x = BOARD_X + (BOARD_WIDTH * CELL_W - width) // 2
        y = BOARD_Y + BOARD_HEIGHT // 2 - 2
        self.addstr(y, x, "+" + "-" * (width - 2) + "+", self.attr(COLOR_BORDER))
        self.addstr(y + 1, x, "|" + " " * (width - 2) + "|", self.attr(COLOR_BORDER))
        self.addstr(y + 2, x, "|" + " " * (width - 2) + "|", self.attr(COLOR_BORDER))
        self.addstr(y + 3, x, "+" + "-" * (width - 2) + "+", self.attr(COLOR_BORDER))
        self.addstr(y + 1, x + (width - len(title)) // 2, title, self.attr(COLOR_TEXT, curses.A_BOLD))
        self.addstr(y + 2, x + (width - len(subtitle)) // 2, subtitle)

    def draw_game_over(self, game: Game, now: float) -> None:
        pulse = curses.A_BOLD if int(now * 3) % 2 == 0 else 0
        title = "GAME OVER"
        subtitle = f"Score {game.score}  Lines {game.lines}  Level {game.level}"
        self.draw_overlay(title, subtitle)
        self.center_text(BOARD_Y + BOARD_HEIGHT // 2 + 3, "Press R to restart    Q to quit", self.attr(COLOR_TEXT, pulse))

    def center_text(self, y: int, text: str, attr: int = 0) -> None:
        _, width = self.stdscr.getmaxyx()
        x = max(0, (width - len(text)) // 2)
        self.addstr(y, x, text, attr)

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = self.stdscr.getmaxyx()
        if 0 <= y < height and x < width:
            self.stdscr.addnstr(y, max(0, x), text, max(0, width - max(0, x) - 1), attr)


def run_curses(stdscr: curses.window) -> None:
    game = Game()
    renderer = Renderer(stdscr)
    running = True

    try:
        while running:
            now = time.monotonic()
            running = handle_input(stdscr, game, now)
            game.tick(now)
            renderer.draw(game, now)
            time.sleep(1 / 60)
    finally:
        if renderer.cursor_hidden:
            Renderer.set_cursor(1)


def handle_input(stdscr: curses.window, game: Game, now: float) -> bool:
    while True:
        key = stdscr.getch()
        if key == -1:
            break
        if key in (ord("q"), ord("Q"), KEY_ESCAPE):
            return False
        if game.state == STATE_START:
            if key in (curses.KEY_ENTER, 10, 13, ord(" ")):
                game.start(now)
            continue
        if key in (ord("p"), ord("P")):
            game.toggle_pause(now)
            continue
        if game.state == STATE_GAME_OVER:
            if key in (ord("r"), ord("R")):
                game.start(now)
            continue
        if game.state != STATE_PLAYING:
            continue
        if key == curses.KEY_LEFT:
            game.move(-1)
        elif key == curses.KEY_RIGHT:
            game.move(1)
        elif key == curses.KEY_DOWN:
            game.soft_drop(now)
        elif key == ord(" "):
            game.hard_drop(now)
        elif key in (ord("z"), ord("Z")):
            game.rotate(-1)
        elif key in (ord("x"), ord("X"), curses.KEY_UP):
            game.rotate(1)
        elif key in (ord("c"), ord("C")):
            game.hold()
    return True


def main(wrapper: Callable[[Callable[[curses.window], None]], None] = curses.wrapper) -> None:
    wrapper(run_curses)
