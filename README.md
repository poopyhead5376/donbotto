# 50 AI Marios (GBA-style prototype)

This project is a browser-based crowd-platformer prototype inspired by GBA-era platformers.

## What changed

- Keeps the original 50-agent AI simulation on a shared side-scrolling course.
- Adds a **BYO ROM** upload control so the project can be extended toward real-game integration.
- Does **not** include Nintendo ROM/BIOS/emulator binaries.

## Run

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Controls

- `R`: reset all 50 agents with new AI personality values.

## Notes on "actual game" mode

To wire this up to the real game, you must provide your own legally dumped ROM/BIOS and integrate a separately-licensed web GBA core.
