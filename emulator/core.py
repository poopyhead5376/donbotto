"""Minimal emulator integration scaffolding.

This file intentionally avoids shipping copyrighted or reverse-engineered game code.
It provides a clean API surface for plugging in a lawful open-source GBA core.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class EmulatorError(RuntimeError):
    """Raised when emulator operations fail."""


@dataclass(slots=True)
class FrameBuffer:
    width: int
    height: int
    pixels_rgba: bytes


class EmulatorCore:
    """Abstract adapter for a legal emulator implementation."""

    def __init__(self) -> None:
        self._rom_path: Path | None = None
        self._loaded = False

    def load_rom(self, rom_path: str | Path) -> None:
        path = Path(rom_path)
        if not path.exists():
            raise EmulatorError(f"ROM not found: {path}")
        if path.suffix.lower() not in {".gba", ".bin"}:
            raise EmulatorError("Expected a .gba/.bin ROM image")
        self._rom_path = path
        self._loaded = True

    def step_frame(self, buttons_mask: int = 0) -> FrameBuffer:
        if not self._loaded:
            raise EmulatorError("No ROM loaded")
        # Placeholder frame; replace with real emulator integration.
        width, height = 240, 160
        return FrameBuffer(width=width, height=height, pixels_rgba=b"\x00" * (width * height * 4))

    @property
    def loaded_rom(self) -> Path | None:
        return self._rom_path
