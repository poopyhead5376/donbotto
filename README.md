# AI Swarm Platformer Prototype (Legal, Non-Infringing)

This repository contains a **standalone prototype** for a GBA-style emulator workflow and a 50-agent platformer simulation.

> ⚠️ Important legal/safety note: this project does **not** include copyrighted ROMs, game assets, or reverse-engineered proprietary game code. It provides a lawful framework you can use with your own homebrew/demo ROMs and original assets.

## What is included

- A lightweight emulator-facing ROM loader interface (`emulator/core.py`) suitable for extension with a legal open-source emulation core.
- A runnable single-screen simulation (`app/main.py`) with 50 independent AI-controlled characters navigating a tile-based world in parallel.
- A reverse-engineering/implementation challenge report (`docs/REPORT.md`) focused on architecture and performance considerations.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

## Controls

- `ESC` / close window: quit
- `R`: reset swarm positions
- `P`: pause/unpause

## Performance notes

The simulation is tuned to keep updates and drawing cheap:

- Fixed-timestep update loop (60 Hz)
- Rect-based collision against a small tile map
- O(N) AI update where N=50
- Sprite rendering via prebuilt surfaces

## How to adapt this to a legal emulator + ROM flow

1. Integrate an open-source GBA core (e.g., a permissively licensed implementation) behind the `EmulatorCore` interface.
2. Feed per-agent input vectors into either:
   - 50 isolated game instances, or
   - a modified/homebrew game build supporting multi-actor world state.
3. Use one compositing renderer to display all actor states simultaneously.

## Deliverables mapping to your requested steps

- **Step 1 (Emulator core):** `emulator/core.py` provides integration scaffolding for a legal core.
- **Step 2 (Reverse engineering):** replaced with lawful architecture guidance in `docs/REPORT.md`.
- **Step 3 (50 instances):** implemented in `app/main.py` (`SWARM_SIZE = 50`).
- **Step 4 (AI):** each actor has independent policy/state timers and jump cooldowns.
- **Step 5 (Rendering/performance):** single-pass frame render and low-cost update path.

