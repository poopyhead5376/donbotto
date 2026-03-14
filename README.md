# SIMA2 Bazzite (Minecraft Mod-Learning Bot)

This project is a practical **SIMA-2 style clone** for Bazzite/Linux that can:

1. Inspect your modpack and infer each mod's feature domains (machines, magic, farming, etc.).
2. Persist learning outcomes in SQLite so it gets better at picking actions over time.
3. Execute actions through Minecraft RCON.
4. Build structures from JSON blueprints (supports mod blocks too).
5. Search YouTube tutorials for detected mod features (build and non-build learning).
6. Use local Ollama models to generate adaptive mod-learning actions.

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

## Run learning cycle (default planner)

```bash
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --knowledge-db ./data/knowledge.sqlite3 \
  --rcon-host 127.0.0.1 \
  --rcon-port 25575 \
  --rcon-password change_me \
  learn
```

## Run learning cycle with Ollama

```bash
ollama pull llama3.1
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --rcon-password change_me \
  --use-ollama \
  --ollama-url http://127.0.0.1:11434 \
  --ollama-model llama3.1 \
  learn
```

## Research tutorials on YouTube

This searches tutorials for feature use-cases such as mod progression, automation, and building.

```bash
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --rcon-password change_me \
  research --feature-limit 4 --per-query-limit 3
```

## Build a blueprint

```bash
sima2-bazzite \
  --mods-dir /path/to/server/mods \
  --rcon-password change_me \
  build --blueprint blueprints/starter_hut.json --origin 100 64 100
```

## Notes

- YouTube results are parsed from public search pages (no API key required).
- For advanced automation, replace `say` actions in `agent.py` with command functions/macros/KubeJS hooks.
