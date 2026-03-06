#!/usr/bin/env python3
"""
SMW Overlay Assistant (prototype)

Captures an emulator window, estimates obstacles, predicts a short horizon
"best move" sequence, and draws a path/trajectory overlay so a player can
follow it.

This is a heuristic assistant, not a perfect agent. Tune the HSV masks,
physics constants, and scoring for your ROM/video settings.
"""

from __future__ import annotations

import argparse
import dataclasses
import math
import time
from typing import List, Optional, Sequence, Tuple

import cv2
import mss
import numpy as np

try:
    import pygetwindow as gw
except Exception:  # pragma: no cover - optional dependency edge case
    gw = None


Point = Tuple[int, int]


@dataclasses.dataclass
class WindowRegion:
    left: int
    top: int
    width: int
    height: int


@dataclasses.dataclass
class PlannerConfig:
    step_dt: float = 1 / 30.0
    horizon_steps: int = 36
    gravity: float = 1800.0
    run_speed: float = 150.0
    jump_speed_short: float = 460.0
    jump_speed_long: float = 560.0
    beam_width: int = 16


@dataclasses.dataclass
class SimState:
    x: float
    y: float
    vx: float
    vy: float
    on_ground: bool
    score: float
    path: List[Point]
    actions: List[str]


ACTIONS: Sequence[str] = (
    "run",
    "run_jump_short",
    "run_jump_long",
    "hold",
)


class EmulatorCapture:
    def __init__(self, window_title: str, fallback_region: Optional[WindowRegion] = None):
        self.window_title = window_title
        self.fallback_region = fallback_region
        self._sct = mss.mss()

    def get_region(self) -> WindowRegion:
        if gw is not None:
            wins = gw.getWindowsWithTitle(self.window_title)
            wins = [w for w in wins if w.width > 0 and w.height > 0]
            if wins:
                w = wins[0]
                return WindowRegion(w.left, w.top, w.width, w.height)

        if self.fallback_region is not None:
            return self.fallback_region

        mon = self._sct.monitors[1]
        return WindowRegion(mon["left"], mon["top"], mon["width"], mon["height"])

    def grab(self) -> np.ndarray:
        region = self.get_region()
        shot = self._sct.grab(
            {
                "left": region.left,
                "top": region.top,
                "width": region.width,
                "height": region.height,
            }
        )
        frame = np.array(shot, dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


class SceneEstimator:
    def __init__(self, debug: bool = False):
        self.debug = debug

    def estimate_ground_obstacles(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return (obstacle_mask, ground_mask) binary uint8 masks."""
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Heuristic: sky tends to be bright blue in many SMW scenes.
        sky_lo = np.array([85, 30, 60], dtype=np.uint8)
        sky_hi = np.array([130, 255, 255], dtype=np.uint8)
        sky = cv2.inRange(hsv, sky_lo, sky_hi)

        # Solid platforms are generally non-sky in the lower area.
        not_sky = cv2.bitwise_not(sky)
        lower_focus = np.zeros((h, w), dtype=np.uint8)
        lower_focus[h // 3 :, :] = 255
        ground = cv2.bitwise_and(not_sky, lower_focus)

        kernel = np.ones((3, 3), np.uint8)
        ground = cv2.morphologyEx(ground, cv2.MORPH_OPEN, kernel)
        ground = cv2.morphologyEx(ground, cv2.MORPH_CLOSE, kernel)

        # Treat tall non-sky structures and ground tiles as collision obstacles.
        obstacles = ground.copy()

        # Add rough enemy-like colors (reds/greens) as dangerous obstacles.
        red1 = cv2.inRange(hsv, (0, 60, 60), (10, 255, 255))
        red2 = cv2.inRange(hsv, (165, 60, 60), (179, 255, 255))
        green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        enemies = cv2.bitwise_or(cv2.bitwise_or(red1, red2), green)
        enemies = cv2.morphologyEx(enemies, cv2.MORPH_OPEN, kernel)
        obstacles = cv2.bitwise_or(obstacles, enemies)

        # Inflate for safer planning.
        obstacles = cv2.dilate(obstacles, np.ones((5, 5), np.uint8), iterations=1)

        return obstacles, ground

    def estimate_mario_position(self, frame: np.ndarray, ground_mask: np.ndarray) -> Point:
        """
        Heuristic position estimate.
        We assume Mario is in left half and near first strong ground contact.
        """
        h, w = frame.shape[:2]
        search_w = max(32, w // 2)

        # Candidate from classic red cap + blue overalls cluster.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 70, 50), (10, 255, 255)),
            cv2.inRange(hsv, (165, 70, 50), (179, 255, 255)),
        )
        blue = cv2.inRange(hsv, (90, 40, 30), (140, 255, 255))
        mario_like = cv2.bitwise_and(red, blue)

        roi = mario_like[:, :search_w]
        ys, xs = np.where(roi > 0)
        if len(xs) > 8:
            x = int(np.mean(xs))
            y = int(np.mean(ys))
            return (x, y)

        # Fallback: left-middle near top of ground in current column band.
        col = max(8, w // 5)
        ground_col = ground_mask[:, col]
        gy = np.where(ground_col > 0)[0]
        if len(gy) > 0:
            y = int(max(10, gy.min() - 14))
            return (col, y)

        return (w // 4, int(h * 0.6))


class TrajectoryPlanner:
    def __init__(self, cfg: PlannerConfig):
        self.cfg = cfg

    def _collides(self, x: float, y: float, obstacles: np.ndarray) -> bool:
        h, w = obstacles.shape[:2]
        xi = int(np.clip(round(x), 0, w - 1))
        yi = int(np.clip(round(y), 0, h - 1))

        # Approximate Mario hitbox (8x14 px)
        x0, x1 = max(0, xi - 4), min(w, xi + 4)
        y0, y1 = max(0, yi - 12), min(h, yi + 2)
        hitbox = obstacles[y0:y1, x0:x1]
        return np.any(hitbox > 0)

    def _is_on_ground(self, x: float, y: float, ground: np.ndarray) -> bool:
        h, w = ground.shape[:2]
        xi = int(np.clip(round(x), 0, w - 1))
        yi = int(np.clip(round(y), 0, h - 1))
        y_foot = min(h - 1, yi + 3)
        return ground[y_foot, xi] > 0

    def _simulate_step(
        self,
        state: SimState,
        action: str,
        obstacles: np.ndarray,
        ground: np.ndarray,
    ) -> Optional[SimState]:
        dt = self.cfg.step_dt

        vx = self.cfg.run_speed if action != "hold" else state.vx * 0.85
        vy = state.vy
        on_ground = self._is_on_ground(state.x, state.y, ground)

        if on_ground and action == "run_jump_short":
            vy = -self.cfg.jump_speed_short
        elif on_ground and action == "run_jump_long":
            vy = -self.cfg.jump_speed_long

        vy += self.cfg.gravity * dt

        nx = state.x + vx * dt
        ny = state.y + vy * dt

        h, w = ground.shape[:2]
        nx = float(np.clip(nx, 0, w - 1))
        ny = float(np.clip(ny, 0, h - 1))

        if self._collides(nx, ny, obstacles):
            return None

        n_on_ground = self._is_on_ground(nx, ny, ground)
        if n_on_ground and vy > 0:
            # snap slightly upward to stay on top of tile edges
            ny = max(0.0, ny - 2.0)
            vy = 0.0

        progress = nx - state.x
        safety_penalty = 0.0

        # Penalize being too close to bottom (fall risk)
        if ny > h * 0.9:
            safety_penalty += 100.0

        nscore = state.score + progress - safety_penalty
        npath = state.path + [(int(nx), int(ny))]
        nactions = state.actions + [action]

        return SimState(nx, ny, vx, vy, n_on_ground, nscore, npath, nactions)

    def plan(
        self,
        start: Point,
        obstacles: np.ndarray,
        ground: np.ndarray,
    ) -> Tuple[List[Point], List[str]]:
        sx, sy = start
        init = SimState(float(sx), float(sy), self.cfg.run_speed, 0.0, True, 0.0, [start], [])

        beam = [init]
        best = init

        for _ in range(self.cfg.horizon_steps):
            expanded: List[SimState] = []
            for st in beam:
                for action in ACTIONS:
                    nxt = self._simulate_step(st, action, obstacles, ground)
                    if nxt is not None:
                        expanded.append(nxt)
                        if nxt.score > best.score:
                            best = nxt

            if not expanded:
                break

            expanded.sort(key=lambda s: s.score, reverse=True)
            beam = expanded[: self.cfg.beam_width]

        return best.path, best.actions


def draw_overlay(
    frame: np.ndarray,
    mario: Point,
    obstacles: np.ndarray,
    path: Sequence[Point],
    actions: Sequence[str],
) -> np.ndarray:
    vis = frame.copy()

    # obstacle tint
    red_tint = np.zeros_like(vis)
    red_tint[:, :, 2] = 190
    obstacle_col = cv2.bitwise_and(red_tint, red_tint, mask=obstacles)
    vis = cv2.addWeighted(vis, 1.0, obstacle_col, 0.25, 0)

    # mario marker
    cv2.circle(vis, mario, 6, (0, 255, 255), 2)
    cv2.putText(vis, "Mario", (mario[0] + 8, mario[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

    # path
    if len(path) > 1:
        for i in range(1, len(path)):
            color = (40, 220, 40)
            cv2.line(vis, path[i - 1], path[i], color, 2, cv2.LINE_AA)
        cv2.circle(vis, path[-1], 5, (255, 255, 255), -1)

    # next move hint
    next_move = actions[0] if actions else "none"
    hint = f"Next: {next_move}"
    cv2.rectangle(vis, (8, 8), (240, 44), (0, 0, 0), -1)
    cv2.putText(vis, hint, (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return vis


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SMW trajectory overlay assistant")
    p.add_argument("--window-title", default="Snes9x", help="Substring of emulator window title")
    p.add_argument("--fallback-left", type=int, default=None)
    p.add_argument("--fallback-top", type=int, default=None)
    p.add_argument("--fallback-width", type=int, default=None)
    p.add_argument("--fallback-height", type=int, default=None)
    p.add_argument("--show-obstacles", action="store_true", help="Show obstacle debug window")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    fallback = None
    if None not in (args.fallback_left, args.fallback_top, args.fallback_width, args.fallback_height):
        fallback = WindowRegion(
            args.fallback_left,
            args.fallback_top,
            args.fallback_width,
            args.fallback_height,
        )

    capture = EmulatorCapture(args.window_title, fallback)
    estimator = SceneEstimator()
    planner = TrajectoryPlanner(PlannerConfig())

    win = "SMW Move Overlay (q to quit)"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_TOPMOST, 1)

    last_t = time.time()

    while True:
        frame = capture.grab()
        obstacles, ground = estimator.estimate_ground_obstacles(frame)
        mario = estimator.estimate_mario_position(frame, ground)
        path, actions = planner.plan(mario, obstacles, ground)

        overlay = draw_overlay(frame, mario, obstacles, path, actions)

        now = time.time()
        fps = 1.0 / max(1e-6, now - last_t)
        last_t = now
        cv2.putText(overlay, f"FPS: {fps:4.1f}", (overlay.shape[1] - 120, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow(win, overlay)
        if args.show_obstacles:
            cv2.imshow("obstacles", obstacles)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
