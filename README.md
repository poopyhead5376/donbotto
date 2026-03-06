# SMW Path & Trajectory Overlay (Prototype)

This repo now contains a Python script that captures a Super Mario World emulator window,
estimates nearby obstacles, predicts a short-horizon "best" move sequence, and draws a
trajectory/path overlay for the player to follow.

## File

- `smw_path_overlay.py` — main script.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install opencv-python mss numpy pygetwindow
```

## Run

```bash
python smw_path_overlay.py --window-title "Snes9x"
```

If auto window detection fails, use a manual capture rectangle:

```bash
python smw_path_overlay.py \
  --window-title "Snes9x" \
  --fallback-left 100 --fallback-top 100 \
  --fallback-width 768 --fallback-height 672
```

Press `q` (or `Esc`) to quit.

## Notes

- This is a heuristic assistant (not perfect RL/vision AI).
- You will likely need to tune color masks and physics constants for your emulator/filter settings.
- The overlay window is set to "topmost" so it can stay above the emulator.
