# Mario's Puzzle Party (Mario Party DS) Bot

This repository contains a **Python bot** for Mario Party DS's version of **Mario's Puzzle Party**, implemented with:

- `opencv-python` (`cv2`) for board/candy detection.
- `pydirectinput` for sending keyboard input to an emulator.

## Research notes used for this bot

The bot logic is based on the core objective of Mario's Puzzle Party:

- Candies fall into a vertical grid.
- Matching colors in a **2x2 square** clears them.
- Chains can occur when gravity causes new 2x2 squares after a clear.

## What is improved

- Supports `x` as the **flip key** for swapping the vertical pair order before dropping.
- Detects a falling **pair** (top/bottom colors), not just a single candy.
- Evaluates both orientations (normal + flipped) for each candidate column.
- Uses a stronger board heuristic that rewards immediate 2x2 clears, local setup,
  adjacency, and survivability (lower height / smoother skyline).

## Requirements

```bash
pip install opencv-python pydirectinput
```

## Usage

1. Open your emulator and put the game on screen.
2. Route emulator output to a camera source OpenCV can read (OBS Virtual Camera is a common setup).
3. Set `capture_index` and board ROI values in `main()`.
4. Ensure emulator keybinds match `left`, `right`, `down`, and `x`.
5. Run:

```bash
python mario_puzzle_party_bot.py
```

## Calibration tips

- Start by confirming the board crop (`board_left`, `board_top`, `board_width`, `board_height`).
- Tune `HSV_RANGES` for your emulator colors.
- Verify that `rows` and `cols` match your in-game board.
- Adjust key bindings in `BotConfig` to match emulator controls.

## Disclaimer

This is still a practical baseline and may need per-setup tuning for stable play.
