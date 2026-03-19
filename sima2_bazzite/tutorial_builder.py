from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sima2_bazzite.builder import BlockPlacement
from sima2_bazzite.research import VideoResult, youtube_search


@dataclass(slots=True)
class TutorialBuildPlan:
    query: str
    source_video: VideoResult | None
    palette: list[str]
    placements: list[BlockPlacement]
    rationale: str


def _rectangular_house(width: int, depth: int, height: int, palette: list[str]) -> list[BlockPlacement]:
    floor, wall, roof = palette[0], palette[1], palette[2]
    placements: list[BlockPlacement] = []

    for x in range(width):
        for z in range(depth):
            placements.append(BlockPlacement(x=x, y=0, z=z, block=floor))

    for y in range(1, height + 1):
        for x in range(width):
            for z in range(depth):
                is_edge = x in (0, width - 1) or z in (0, depth - 1)
                if is_edge:
                    placements.append(BlockPlacement(x=x, y=y, z=z, block=wall))

    door_x = width // 2
    placements = [p for p in placements if not (p.x == door_x and p.z == 0 and p.y in (1, 2))]

    for x in range(-1, width + 1):
        for z in range(-1, depth + 1):
            placements.append(BlockPlacement(x=x, y=height + 1, z=z, block=roof))

    return placements


def _tower(radius: int, height: int, palette: list[str]) -> list[BlockPlacement]:
    base, wall, roof = palette[0], palette[1], palette[2]
    placements: list[BlockPlacement] = []
    size = radius * 2 + 1
    center = radius
    for x in range(size):
        for z in range(size):
            dist = abs(x - center) + abs(z - center)
            if dist <= radius:
                placements.append(BlockPlacement(x=x, y=0, z=z, block=base))
                for y in range(1, height + 1):
                    if dist == radius:
                        placements.append(BlockPlacement(x=x, y=y, z=z, block=wall))
    for x in range(size):
        for z in range(size):
            dist = abs(x - center) + abs(z - center)
            if dist <= radius + 1:
                placements.append(BlockPlacement(x=x, y=height + 1, z=z, block=roof))
    return placements


def _garden(width: int, depth: int, palette: list[str]) -> list[BlockPlacement]:
    border, crop, water = palette[0], palette[1], palette[2]
    placements: list[BlockPlacement] = []
    water_x = width // 2
    for x in range(width):
        for z in range(depth):
            if x in (0, width - 1) or z in (0, depth - 1):
                placements.append(BlockPlacement(x=x, y=0, z=z, block=border))
            elif x == water_x and z % 3 == 0:
                placements.append(BlockPlacement(x=x, y=0, z=z, block=water))
            else:
                placements.append(BlockPlacement(x=x, y=0, z=z, block=crop))
    return placements


STRUCTURE_KEYWORDS: dict[str, tuple[Callable[..., list[BlockPlacement]], tuple[int, ...], list[str], str]] = {
    "tower": (_tower, (2, 7), ["stone_bricks", "stone_bricks", "cobblestone_slab"], "Detected tower-style tutorial, generating compact watchtower plan."),
    "farm": (_garden, (9, 7), ["oak_log", "wheat", "water"], "Detected farm tutorial, generating irrigated starter farm."),
    "garden": (_garden, (9, 7), ["oak_log", "carrots", "water"], "Detected garden tutorial, generating decorative crop plot."),
    "house": (_rectangular_house, (7, 6, 4), ["oak_planks", "spruce_log", "spruce_stairs"], "Detected house tutorial, generating compact starter house."),
    "cabin": (_rectangular_house, (6, 5, 4), ["spruce_planks", "spruce_log", "spruce_stairs"], "Detected cabin tutorial, generating rustic cabin."),
    "base": (_rectangular_house, (9, 7, 4), ["stone_bricks", "oak_log", "stone_brick_stairs"], "Detected base tutorial, generating practical survival base."),
}


def infer_build_plan(query: str, videos: list[VideoResult]) -> TutorialBuildPlan:
    source = videos[0] if videos else None
    text = f"{query} {source.title if source else ''}".lower()
    for keyword, (factory, dimensions, palette, rationale) in STRUCTURE_KEYWORDS.items():
        if keyword in text:
            placements = factory(*dimensions, palette)
            return TutorialBuildPlan(
                query=query,
                source_video=source,
                palette=palette,
                placements=placements,
                rationale=rationale,
            )

    palette = ["oak_planks", "oak_log", "oak_stairs"]
    placements = _rectangular_house(7, 6, 4, palette)
    return TutorialBuildPlan(
        query=query,
        source_video=source,
        palette=palette,
        placements=placements,
        rationale="No exact structure keyword matched, using a reliable starter house fallback.",
    )


def plan_build_from_tutorial(query: str, limit: int = 5) -> TutorialBuildPlan:
    videos = youtube_search(f"minecraft {query} tutorial", limit=limit)
    return infer_build_plan(query, videos)
