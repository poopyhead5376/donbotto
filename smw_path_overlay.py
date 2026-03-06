#!/usr/bin/env python3
"""
SMW Overlay Assistant (improved prototype)

- Captures an emulator window and keeps an overlay view docked to that exact region.
- Estimates obstacles and Mario location with lightweight vision heuristics.
- Predicts multiple candidate trajectories with a beam search planner.
- Draws clearer visuals: primary + alternate paths, waypoint markers, action timeline,
  and confidence score.

Note: Truly injecting graphics inside emulator rendering is emulator-specific. This script
keeps the overlay window tightly aligned over the emulator bounds to behave like an
in-place overlay.
"""

from __future__ import annotations

import argparse
import dataclasses
import time
from typing import List, Optional, Sequence, Tuple

import cv2
import mss
import numpy as np

try:
    import pygetwindow as gw
except Exception:  # optional dependency edge case
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
    horizon_steps: int = 48
    gravity: float = 1800.0
    run_speed: float = 160.0
    jump_speed_short: float = 460.0
    jump_speed_long: float = 600.0
    beam_width: int = 22
    keep_top_paths: int = 3


@dataclasses.dataclass
class SimState:
    x: float
    y: float
    vx: float
    vy: float
    score: float
    path: List[Point]
    actions: List[str]


ACTIONS: Sequence[str] = ("run", "run_jump_short", "run_jump_long", "hold")


class EmulatorCapture:
    def __init__(self, window_title: str, fallback_region: Optional[WindowRegion] = None):
        self.window_title = window_title
        self.fallback_region = fallback_region
        self._sct = mss.mss()

    def get_region(self) -> WindowRegion:
        if gw is not None:
            wins = [w for w in gw.getWindowsWithTitle(self.window_title) if w.width > 0 and w.height > 0]
            if wins:
                w = wins[0]
                return WindowRegion(w.left, w.top, w.width, w.height)

        if self.fallback_region is not None:
            return self.fallback_region

        mon = self._sct.monitors[1]
        return WindowRegion(mon["left"], mon["top"], mon["width"], mon["height"])

    def grab(self) -> Tuple[np.ndarray, WindowRegion]:
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
        bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return bgr, region


class SceneEstimator:
    def __init__(self) -> None:
        self.prev_mario: Optional[Point] = None

    def estimate_ground_obstacles(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        sky = cv2.inRange(hsv, np.array([85, 25, 50], dtype=np.uint8), np.array([130, 255, 255], dtype=np.uint8))
        not_sky = cv2.bitwise_not(sky)

        lower_focus = np.zeros((h, w), dtype=np.uint8)
        lower_focus[h // 4 :, :] = 255
        ground = cv2.bitwise_and(not_sky, lower_focus)

        kernel = np.ones((3, 3), np.uint8)
        ground = cv2.morphologyEx(ground, cv2.MORPH_OPEN, kernel)
        ground = cv2.morphologyEx(ground, cv2.MORPH_CLOSE, kernel)

        red = cv2.bitwise_or(cv2.inRange(hsv, (0, 60, 60), (10, 255, 255)), cv2.inRange(hsv, (165, 60, 60), (179, 255, 255)))
        green = cv2.inRange(hsv, (35, 40, 40), (90, 255, 255))
        enemies = cv2.bitwise_or(red, green)
        enemies = cv2.morphologyEx(enemies, cv2.MORPH_OPEN, kernel)

        obstacles = cv2.bitwise_or(ground, enemies)
        obstacles = cv2.dilate(obstacles, np.ones((5, 5), np.uint8), iterations=1)

        free_space = cv2.bitwise_not(obstacles)
        obstacle_dist = cv2.distanceTransform(free_space, cv2.DIST_L2, 3)
        return obstacles, ground, obstacle_dist

    def estimate_mario_position(self, frame: np.ndarray, ground_mask: np.ndarray) -> Point:
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        search_w = max(64, int(w * 0.7))

        red = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 70, 45), (12, 255, 255)),
            cv2.inRange(hsv, (165, 70, 45), (179, 255, 255)),
        )
        blue = cv2.inRange(hsv, (88, 35, 25), (145, 255, 255))

        # Mario-like pixels are where red and blue are close (hat + overalls neighborhood).
        rb_near = cv2.bitwise_or(
            cv2.bitwise_and(red, cv2.dilate(blue, np.ones((5, 5), np.uint8), 1)),
            cv2.bitwise_and(blue, cv2.dilate(red, np.ones((5, 5), np.uint8), 1)),
        )
        rb_near = cv2.morphologyEx(rb_near, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        roi = rb_near[:, :search_w]
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best: Optional[Tuple[float, Point]] = None
        for c in contours:
            area = cv2.contourArea(c)
            if area < 10:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            # Use lower-center of blob so marker sits on Mario body/feet area.
            cx = int(x + bw / 2)
            cy = int(y + bh * 0.85)

            score = area
            if self.prev_mario is not None:
                dx = cx - self.prev_mario[0]
                dy = cy - self.prev_mario[1]
                score -= 0.15 * (dx * dx + dy * dy) ** 0.5

            if best is None or score > best[0]:
                best = (score, (cx, cy))

        if best is not None:
            raw = best[1]
            if self.prev_mario is None:
                self.prev_mario = raw
            else:
                # Smooth position to keep marker stable on sprite.
                ax = int(0.65 * self.prev_mario[0] + 0.35 * raw[0])
                ay = int(0.65 * self.prev_mario[1] + 0.35 * raw[1])
                self.prev_mario = (ax, ay)
            return self.prev_mario

        col = max(8, w // 5)
        gy = np.where(ground_mask[:, col] > 0)[0]
        if len(gy):
            fallback = (col, int(max(10, gy.min() - 14)))
        else:
            fallback = (w // 4, int(h * 0.6))

        if self.prev_mario is None:
            self.prev_mario = fallback
        return self.prev_mario


class TrajectoryPlanner:
    def __init__(self, cfg: PlannerConfig):
        self.cfg = cfg

    @staticmethod
    def _clamp_pt(x: float, y: float, shape: Tuple[int, int]) -> Tuple[int, int]:
        h, w = shape
        return int(np.clip(round(x), 0, w - 1)), int(np.clip(round(y), 0, h - 1))

    def _collides(self, x: float, y: float, obstacles: np.ndarray) -> bool:
        h, w = obstacles.shape[:2]
        xi, yi = self._clamp_pt(x, y, (h, w))
        x0, x1 = max(0, xi - 4), min(w, xi + 4)
        y0, y1 = max(0, yi - 12), min(h, yi + 2)
        return np.any(obstacles[y0:y1, x0:x1] > 0)

    def _is_on_ground(self, x: float, y: float, ground: np.ndarray) -> bool:
        h, w = ground.shape[:2]
        xi, yi = self._clamp_pt(x, y, (h, w))
        return ground[min(h - 1, yi + 3), xi] > 0

    def _step(self, state: SimState, action: str, obstacles: np.ndarray, ground: np.ndarray, obstacle_dist: np.ndarray) -> Optional[SimState]:
        dt = self.cfg.step_dt

        vx = self.cfg.run_speed if action != "hold" else state.vx * 0.86
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
            ny = max(0.0, ny - 2.0)
            vy = 0.0

        xi, yi = self._clamp_pt(nx, ny, (h, w))
        clearance = float(obstacle_dist[yi, xi])

        progress = nx - state.x
        safety_bonus = min(12.0, clearance * 0.35)
        bottom_penalty = 50.0 if ny > h * 0.9 else 0.0

        score = state.score + progress + safety_bonus - bottom_penalty
        return SimState(nx, ny, vx, vy, score, state.path + [(xi, yi)], state.actions + [action])

    def plan(self, start: Point, obstacles: np.ndarray, ground: np.ndarray, obstacle_dist: np.ndarray) -> List[SimState]:
        sx, sy = start
        beam = [SimState(float(sx), float(sy), self.cfg.run_speed, 0.0, 0.0, [start], [])]

        for _ in range(self.cfg.horizon_steps):
            expanded: List[SimState] = []
            for st in beam:
                for action in ACTIONS:
                    nxt = self._step(st, action, obstacles, ground, obstacle_dist)
                    if nxt is not None:
                        expanded.append(nxt)
            if not expanded:
                break
            expanded.sort(key=lambda s: s.score, reverse=True)
            beam = expanded[: self.cfg.beam_width]

        beam.sort(key=lambda s: s.score, reverse=True)
        return beam[: self.cfg.keep_top_paths]


def draw_action_timeline(vis: np.ndarray, actions: Sequence[str], x: int, y: int, w: int = 420, h: int = 24) -> None:
    if not actions:
        return
    cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 0), -1)
    color_map = {
        "run": (60, 220, 60),
        "run_jump_short": (60, 180, 255),
        "run_jump_long": (40, 120, 255),
        "hold": (180, 180, 180),
    }
    n = len(actions)
    seg = max(2, w // n)
    for i, act in enumerate(actions):
        cx0 = x + i * seg
        cx1 = min(x + w, cx0 + seg - 1)
        cv2.rectangle(vis, (cx0, y), (cx1, y + h), color_map.get(act, (100, 100, 100)), -1)
    cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 255, 255), 1)


def draw_overlay(frame: np.ndarray, mario: Point, obstacles: np.ndarray, candidates: Sequence[SimState]) -> np.ndarray:
    vis = frame.copy()
    h, w = vis.shape[:2]

    red_tint = np.zeros_like(vis)
    red_tint[:, :, 2] = 180
    obstacle_col = cv2.bitwise_and(red_tint, red_tint, mask=obstacles)
    vis = cv2.addWeighted(vis, 1.0, obstacle_col, 0.22, 0)

    # Draw alternate trajectories first.
    for rank, cand in enumerate(candidates[1:], start=2):
        if len(cand.path) < 2:
            continue
        for i in range(1, len(cand.path)):
            cv2.line(vis, cand.path[i - 1], cand.path[i], (220, 180, 70), 1, cv2.LINE_AA)
        cv2.putText(vis, f"#{rank}", cand.path[-1], cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 180, 70), 1)

    # Draw main path with stronger readability.
    if candidates:
        best = candidates[0]
        if len(best.path) > 1:
            for i in range(1, len(best.path)):
                t = i / max(1, len(best.path) - 1)
                color = (int(40 + 100 * t), int(220 - 80 * t), int(40 + 170 * t))
                cv2.line(vis, best.path[i - 1], best.path[i], color, 3, cv2.LINE_AA)
            # waypoint dots every ~6 steps
            for i in range(0, len(best.path), 6):
                cv2.circle(vis, best.path[i], 3, (255, 255, 255), -1)
            cv2.circle(vis, best.path[-1], 6, (255, 255, 255), -1)

        next_move = best.actions[0] if best.actions else "none"
        conf = 0.0
        if len(candidates) >= 2:
            delta = best.score - candidates[1].score
            conf = max(0.0, min(1.0, 0.5 + delta / 120.0))
        elif candidates:
            conf = 0.85

        cv2.rectangle(vis, (10, 8), (410, 76), (0, 0, 0), -1)
        cv2.putText(vis, f"Next: {next_move}", (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
        cv2.putText(vis, f"Confidence: {int(conf * 100)}%", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (220, 220, 220), 2)

        draw_action_timeline(vis, best.actions[:20], 10, h - 36, w=min(500, w - 20), h=20)

    cv2.circle(vis, mario, 7, (0, 255, 255), 2)
    cv2.putText(vis, "Mario", (mario[0] + 8, mario[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    return vis


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SMW trajectory overlay assistant")
    p.add_argument("--window-title", default="Snes9x", help="Substring of emulator window title")
    p.add_argument("--fallback-left", type=int, default=None)
    p.add_argument("--fallback-top", type=int, default=None)
    p.add_argument("--fallback-width", type=int, default=None)
    p.add_argument("--fallback-height", type=int, default=None)
    p.add_argument("--show-obstacles", action="store_true", help="Show obstacle debug window")
    p.add_argument(
        "--dock-overlay",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep overlay window docked over emulator bounds",
    )
    p.add_argument(
        "--prevent-feedback-loop",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Temporarily moves overlay off-screen before capture to avoid recursive self-capture",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    fallback = None
    if None not in (args.fallback_left, args.fallback_top, args.fallback_width, args.fallback_height):
        fallback = WindowRegion(args.fallback_left, args.fallback_top, args.fallback_width, args.fallback_height)

    capture = EmulatorCapture(args.window_title, fallback)
    estimator = SceneEstimator()
    planner = TrajectoryPlanner(PlannerConfig())

    win = "SMW Overlay (docked) - q to quit"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_TOPMOST, 1)

    last_t = time.time()
    while True:
        # Prevent infinite hall-of-mirrors loop when overlay sits above emulator.
        # `moveWindow` may apply on the next GUI tick, so we force a tiny UI pump
        # before grabbing the frame.
        if args.prevent_feedback_loop and args.dock_overlay:
            cv2.moveWindow(win, -20000, -20000)
            cv2.waitKey(1)
            time.sleep(0.005)

        frame, region = capture.grab()


        obstacles, ground, obstacle_dist = estimator.estimate_ground_obstacles(frame)
        mario = estimator.estimate_mario_position(frame, ground)
        candidates = planner.plan(mario, obstacles, ground, obstacle_dist)
        overlay = draw_overlay(frame, mario, obstacles, candidates)

        now = time.time()
        fps = 1.0 / max(1e-6, now - last_t)
        last_t = now
        cv2.putText(overlay, f"FPS: {fps:4.1f}", (overlay.shape[1] - 120, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

        if args.dock_overlay:
            cv2.resizeWindow(win, region.width, region.height)
            cv2.moveWindow(win, region.left, region.top)

        cv2.imshow(win, overlay)
        if args.show_obstacles:
            cv2.imshow("obstacles", obstacles)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
