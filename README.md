# 50 AI Marios (GBA-style prototype)

This project is a browser-based crowd-platformer prototype inspired by GBA-era platformers.

## What changed

- Keeps the original 50-agent AI simulation on a shared side-scrolling course.
- ROM loading now actually reads and validates your selected local file in-browser.
- When a ROM is loaded, the simulation is re-seeded from ROM bytes (AI personalities + platform offsets), so loading is visibly applied.
- Does **not** include Nintendo ROM/BIOS/emulator binaries.

## Run

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Controls

- `R`: reset all 50 agents with current seed/personality settings.

## Notes

This demo can load a user-provided GBA file and react to it, but it is still not a full emulator runtime.
