# SMW Path & Trajectory Overlay (Improved Prototype)

This script captures a Super Mario World emulator window, predicts likely next moves,
and draws an easier-to-read trajectory overlay that stays docked to emulator bounds.

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

## What's improved

- **Docked overlay behavior:** the assistant window now follows emulator position and size so it stays aligned.
- **Smarter planner scoring:** trajectory ranking now uses progress plus local obstacle-clearance distance.
- **Clearer visuals:**
  - primary trajectory with gradient and waypoint dots
  - alternate candidate trajectories
  - confidence estimate
  - next-action label
  - action timeline bar at bottom for near-future move sequence

## Notes

- This is still a heuristic assistant (not a trained RL model).
- You may still need to tune color masks and physics constants for specific ROMs/shaders.
- Rendering directly inside emulator pixels is emulator-specific; this script simulates in-place overlay by docking a topmost window to emulator bounds.
