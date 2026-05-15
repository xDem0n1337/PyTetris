# Terminal Tetris

A polished, self-contained Tetris game for the terminal. It uses Python 3 and the standard-library `curses` module.

## Requirements

- Python 3.10 or newer
- macOS or Linux terminal with `curses`
- Windows users may need `pip install windows-curses`

No third-party packages are required on macOS or Linux.

## Run

From this directory:

```bash
python3 tetris.py
```

You can also run the package directly:

```bash
python3 -m terminal_tetris
```

## Controls

| Key | Action |
| --- | --- |
| Left / Right arrows | Move piece |
| Down arrow | Soft drop |
| Space | Hard drop |
| Z | Rotate counterclockwise |
| X or Up arrow | Rotate clockwise |
| C | Hold piece |
| P | Pause or resume |
| R | Restart after game over |
| Q or Esc | Quit |

## Features

- Standard 10x20 Tetris board
- Seven tetrominoes with randomized 7-bag generation
- Hold piece, limited to once per falling piece
- Ghost piece showing the hard-drop landing position
- Five-piece next queue
- Conventional line-clear and drop scoring
- Level increases every 10 cleared lines with faster gravity
- Line-clear animation, hard-drop landing flash, start screen, pause overlay, and game-over overlay
- Terminal-safe colors with monochrome fallback
- Responsive input, low flicker, resize message, and cursor restoration through `curses.wrapper`

## Tests

Run the logic tests with:

```bash
python3 -m unittest discover
```

The tests cover piece rotation, collision detection, line clearing, hold behavior, hard-drop distance, and line-clear scoring.

## Known Limitations

- Rotation uses a small practical wall-kick set, not the full Super Rotation System.
- The UI is designed for terminals at least 70 columns by 26 rows.
