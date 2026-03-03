#!/usr/bin/env python3
"""Mario Party DS - Mario's Puzzle Party bot.

This bot uses:
- OpenCV (`cv2`) for visual analysis.
- pydirectinput for emulator/game input.

How it works (high level):
1. Reads video frames from a capture device (typically an OBS Virtual Camera
   that shows your emulator window).
2. Converts a board ROI into a color grid.
3. Detects the currently falling pair near the top of the board.
4. Evaluates target columns with both orientations (normal/flipped).
5. Sends left/right/down and optional flip (`x`) key presses with pydirectinput.

This is a practical starter bot: you will need to calibrate ROI and HSV ranges
for your emulator, scale, and color profile.
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass

import cv2
import pydirectinput


@dataclass
class BotConfig:
    # Board geometry in *frame pixels*.
    board_left: int = 480
    board_top: int = 120
    board_width: int = 288
    board_height: int = 576

    # Mario's Puzzle Party uses a tall, narrow board.
    cols: int = 6
    rows: int = 12

    # Input mapping; adjust for your emulator keybinds.
    key_left: str = "left"
    key_right: str = "right"
    key_drop: str = "down"
    key_flip: str = "x"

    # Capture index (0 is often webcam, OBS virtual camera may be 1+).
    capture_index: int = 0

    # How often to think/act.
    tick_sleep_s: float = 0.035
    movement_press_s: float = 0.025


class MarioPuzzlePartyBot:
    # HSV thresholds for candy colors. Tune these for your feed.
    # Format: name -> ((h_low, s_low, v_low), (h_high, s_high, v_high)).
    HSV_RANGES = {
        "red": ((0, 120, 90), (10, 255, 255)),
        "yellow": ((20, 110, 110), (35, 255, 255)),
        "green": ((40, 70, 70), (90, 255, 255)),
        "blue": ((95, 90, 80), (130, 255, 255)),
    }

    COLOR_IDS = {
        "empty": 0,
        "red": 1,
        "yellow": 2,
        "green": 3,
        "blue": 4,
    }

    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self.cap = cv2.VideoCapture(cfg.capture_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                "Could not open capture device. Set capture_index to OBS virtual camera or a valid video source."
            )

        pydirectinput.PAUSE = 0
        pydirectinput.FAILSAFE = False

        self.cell_w = self.cfg.board_width // self.cfg.cols
        self.cell_h = self.cfg.board_height // self.cfg.rows

    def close(self) -> None:
        self.cap.release()

    def _board_roi(self, frame):
        y1 = self.cfg.board_top
        y2 = y1 + self.cfg.board_height
        x1 = self.cfg.board_left
        x2 = x1 + self.cfg.board_width
        return frame[y1:y2, x1:x2]

    def _classify_cell(self, cell_hsv) -> int:
        best_name = "empty"
        best_score = 0

        for name, (low, high) in self.HSV_RANGES.items():
            mask = cv2.inRange(cell_hsv, low, high)
            score = cv2.countNonZero(mask)
            if score > best_score:
                best_score = score
                best_name = name

        # Require enough colored pixels or treat as empty.
        if best_score < int(cell_hsv.shape[0] * cell_hsv.shape[1] * 0.16):
            return self.COLOR_IDS["empty"]

        return self.COLOR_IDS[best_name]

    def board_from_frame(self, frame):
        roi = self._board_roi(frame)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        board = [[0 for _ in range(self.cfg.cols)] for _ in range(self.cfg.rows)]

        for r in range(self.cfg.rows):
            for c in range(self.cfg.cols):
                y1 = r * self.cell_h
                y2 = y1 + self.cell_h
                x1 = c * self.cell_w
                x2 = x1 + self.cell_w

                # Use center area to avoid cell borders.
                pad_y = max(2, self.cell_h // 6)
                pad_x = max(2, self.cell_w // 6)
                cell = hsv[y1 + pad_y : y2 - pad_y, x1 + pad_x : x2 - pad_x]
                board[r][c] = self._classify_cell(cell)

        return board

    def detect_falling_pair(self, board):
        """Approximate active pair by scanning top rows.

        Returns (column, top_color, bottom_color) or None when uncertain.
        If only one piece is visible, treat pair as same color to keep moving.
        """
        found = []
        for r in range(0, 3):
            for c in range(self.cfg.cols):
                color = board[r][c]
                if color != 0:
                    found.append((r, c, color))

        if not found:
            return None

        found.sort(key=lambda x: x[0])
        if len(found) == 1:
            _, c, color = found[0]
            return c, color, color

        # Prefer two candies in same column (vertical pair).
        for i in range(len(found)):
            for j in range(i + 1, len(found)):
                r1, c1, col1 = found[i]
                r2, c2, col2 = found[j]
                if c1 == c2 and abs(r1 - r2) <= 2:
                    if r1 <= r2:
                        return c1, col1, col2
                    return c1, col2, col1

        # Fallback to earliest two seen.
        (_, c0, col0), (_, _, col1) = found[0], found[1]
        return c0, col0, col1

    def _drop_row(self, board, col):
        for r in range(self.cfg.rows - 1, -1, -1):
            if board[r][col] == 0:
                return r
        return None

    def _square_completion_bonus(self, board, row, col, color):
        bonus = 0

        windows = [
            ((row - 1, col - 1), (row - 1, col), (row, col - 1), (row, col)),
            ((row - 1, col), (row - 1, col + 1), (row, col), (row, col + 1)),
            ((row, col - 1), (row, col), (row + 1, col - 1), (row + 1, col)),
            ((row, col), (row, col + 1), (row + 1, col), (row + 1, col + 1)),
        ]

        for cells in windows:
            valid = True
            values = []
            for rr, cc in cells:
                if not (0 <= rr < self.cfg.rows and 0 <= cc < self.cfg.cols):
                    valid = False
                    break
                if rr == row and cc == col:
                    values.append(color)
                else:
                    values.append(board[rr][cc])
            if not valid:
                continue

            same = sum(1 for v in values if v == color)
            empty = sum(1 for v in values if v == 0)

            if same == 4:
                bonus += 80
            elif same == 3 and empty == 1:
                bonus += 28
            elif same == 2 and empty == 2:
                bonus += 10

        return bonus

    def _column_height(self, board, col):
        return sum(1 for r in range(self.cfg.rows) if board[r][col] != 0)

    def _local_adjacency_bonus(self, board, row, col, color):
        score = 0
        neighbors = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        for rr, cc in neighbors:
            if 0 <= rr < self.cfg.rows and 0 <= cc < self.cfg.cols:
                if board[rr][cc] == color:
                    score += 7
                elif board[rr][cc] == 0:
                    score += 1
        return score

    def _count_completed_squares(self, board):
        total = 0
        for r in range(self.cfg.rows - 1):
            for c in range(self.cfg.cols - 1):
                vals = [board[r][c], board[r][c + 1], board[r + 1][c], board[r + 1][c + 1]]
                if vals[0] != 0 and vals.count(vals[0]) == 4:
                    total += 1
        return total

    def _simulate_drop_pair(self, board, col, top_color, bottom_color, flipped):
        sim = copy.deepcopy(board)
        row_bottom = self._drop_row(sim, col)
        if row_bottom is None:
            return None

        row_top = row_bottom - 1
        if row_top < 0 or sim[row_top][col] != 0:
            return None

        first, second = (top_color, bottom_color)
        if flipped:
            first, second = second, first

        # In a vertical pair, top piece lands at row_top and bottom at row_bottom.
        sim[row_top][col] = first
        sim[row_bottom][col] = second

        return sim, row_top, row_bottom

    def _score_simulated_state(self, board_before, board_after, col, row_top, row_bottom, top_color, bottom_color):
        score = 0

        # Strongly reward immediate completed 2x2 groups.
        before_squares = self._count_completed_squares(board_before)
        after_squares = self._count_completed_squares(board_after)
        score += (after_squares - before_squares) * 140

        # Reward local 2x2 setup around each placed candy.
        score += self._square_completion_bonus(board_after, row_top, col, top_color)
        score += self._square_completion_bonus(board_after, row_bottom, col, bottom_color)

        # Reward local adjacency of same color around both pieces.
        score += self._local_adjacency_bonus(board_after, row_top, col, top_color)
        score += self._local_adjacency_bonus(board_after, row_bottom, col, bottom_color)

        # Keep center-ish and avoid very tall columns.
        center = (self.cfg.cols - 1) / 2.0
        score -= int(abs(col - center) * 1.5)

        heights = [self._column_height(board_after, c) for c in range(self.cfg.cols)]
        max_h = max(heights)
        score -= max_h * 2

        # Punish top-danger states.
        if max_h >= self.cfg.rows - 1:
            score -= 250
        elif max_h >= self.cfg.rows - 2:
            score -= 120

        # Penalize uneven skyline.
        roughness = sum(abs(heights[i] - heights[i + 1]) for i in range(self.cfg.cols - 1))
        score -= roughness

        return score

    def choose_best_move(self, board, top_color, bottom_color):
        best = None
        best_score = -10**9

        for col in range(self.cfg.cols):
            for flipped in (False, True):
                simulation = self._simulate_drop_pair(board, col, top_color, bottom_color, flipped)
                if simulation is None:
                    continue

                sim_board, row_top, row_bottom = simulation
                placed_top = top_color if not flipped else bottom_color
                placed_bottom = bottom_color if not flipped else top_color
                score = self._score_simulated_state(
                    board,
                    sim_board,
                    col,
                    row_top,
                    row_bottom,
                    placed_top,
                    placed_bottom,
                )

                if score > best_score:
                    best_score = score
                    best = (col, flipped)

        return best

    def execute_move(self, current_col, target_col, flip_before_drop):
        if current_col is None:
            return

        while current_col < target_col:
            pydirectinput.keyDown(self.cfg.key_right)
            time.sleep(self.cfg.movement_press_s)
            pydirectinput.keyUp(self.cfg.key_right)
            current_col += 1

        while current_col > target_col:
            pydirectinput.keyDown(self.cfg.key_left)
            time.sleep(self.cfg.movement_press_s)
            pydirectinput.keyUp(self.cfg.key_left)
            current_col -= 1

        if flip_before_drop:
            pydirectinput.press(self.cfg.key_flip)
            time.sleep(self.cfg.movement_press_s)

        pydirectinput.press(self.cfg.key_drop)

    def run(self):
        print("Bot started. Press Ctrl+C to stop.")
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.1)
                    continue

                board = self.board_from_frame(frame)
                falling = self.detect_falling_pair(board)

                if falling is not None:
                    current_col, top_color, bottom_color = falling
                    best_move = self.choose_best_move(board, top_color, bottom_color)
                    if best_move is not None:
                        target_col, flip = best_move
                        self.execute_move(current_col, target_col, flip)

                time.sleep(self.cfg.tick_sleep_s)
        finally:
            self.close()


def main() -> None:
    cfg = BotConfig(
        # Update these numbers after calibration.
        board_left=480,
        board_top=120,
        board_width=288,
        board_height=576,
        cols=6,
        rows=12,
        capture_index=0,
        key_flip="x",
    )

    bot = MarioPuzzlePartyBot(cfg)
    bot.run()


if __name__ == "__main__":
    main()
