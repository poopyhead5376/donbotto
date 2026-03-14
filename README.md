# SIMA2 Bazzite (Minecraft Mod-Learning Bot)

This project is a practical **SIMA-2 style clone** for Bazzite/Linux that can:

1. Inspect your modpack and infer each mod's feature domains (machines, magic, farming, etc.).
2. Persist learning outcomes in SQLite so it gets better at picking actions over time.
3. Execute actions through Minecraft RCON.
4. Build structures from JSON blueprints (supports mod blocks too).

## Why this design

A true visual embodied general agent requires client instrumentation and reinforcement pipelines.
This implementation is intentionally robust and runnable today on Bazzite with modded servers:
- Works headless.
- Integrates with any Forge/Fabric/NeoForge server that enables RCON.
- Learns mod intent from jar metadata and descriptions.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure server RCON

In `server.properties`:

```ini
enable-rcon=true
rcon.password=change_me
rcon.port=25575
```

## Run learning cycle

```bash
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --knowledge-db ./data/knowledge.sqlite3 \
  --rcon-host 127.0.0.1 \
  --rcon-port 25575 \
  --rcon-password change_me \
  learn
```

## Build a blueprint

```bash
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --rcon-password change_me \
  build --blueprint blueprints/starter_hut.json --origin 100 64 100
```

## Extending to advanced control

- Replace `say` commands in `agent.py` with macro actions (`/execute`, `/function`, KubeJS hooks, or server-side scripting).
- Feed JEI recipe dumps and in-game logs into `knowledge.py` for richer learning.
- Connect to a movement bot (mineflayer, Carpet bots, or custom client) while keeping this planner/knowledge system.
