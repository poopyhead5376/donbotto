from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sima2_bazzite.rcon_client import RconClient


@dataclass(slots=True)
class BlockPlacement:
    x: int
    y: int
    z: int
    block: str


def load_blueprint(path: Path) -> list[BlockPlacement]:
    data = json.loads(path.read_text())
    placements: list[BlockPlacement] = []
    for item in data["blocks"]:
        placements.append(
            BlockPlacement(
                x=int(item["x"]),
                y=int(item["y"]),
                z=int(item["z"]),
                block=str(item["block"]),
            )
        )
    return placements


def build_structure(rcon: RconClient, blueprint: list[BlockPlacement], origin: tuple[int, int, int]) -> list[str]:
    ox, oy, oz = origin
    outputs: list[str] = []
    for step in blueprint:
        cmd = f"setblock {ox + step.x} {oy + step.y} {oz + step.z} {step.block}"
        outputs.append(rcon.run(cmd))
    return outputs
