#!/usr/bin/env python3
"""Mario Party DS - Mario's Puzzle Party bot.

This bot uses:
- OpenCV (`cv2`) for visual analysis.
- pydirectinput for emulator/game input.

How it works (high level):
1. Reads video frames from a capture device (typically an OBS Virtual Camera
   that shows your emulator window).
2. Converts a board ROI into a color grid.
3. Detects the currently falling candy near the top of the board.
4. Picks a target column using a quick heuristic aimed at building 2x2 blocks.
5. Sends left/right/down key presses with pydirectinput.

This is a practical starter bot: you will need to calibrate ROI and HSV ranges
for your emulator, scale, and color profile.
"""

from __future__ import annotations

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

    def detect_falling_piece(self, board):
        """Approximate the active candy by scanning the top rows for occupancy.

        Returns (column_index, color_id) or (None, None).
        """
        for r in range(0, 2):
            for c in range(self.cfg.cols):
                color = board[r][c]
                if color != 0:
                    return c, color
        return None, None

    def _drop_row(self, board, col):
        for r in range(self.cfg.rows - 1, -1, -1):
            if board[r][col] == 0:
                return r
        return None

    def _score_column(self, board, col, color):
        row = self._drop_row(board, col)
        if row is None:
            return -10_000

        score = 0

        # Prefer deeper placements (survivability).
        score += row * 2

        # Reward adjacency of same color.
        neighbors = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
        for rr, cc in neighbors:
            if 0 <= rr < self.cfg.rows and 0 <= cc < self.cfg.cols and board[rr][cc] == color:
                score += 6

        # Strong reward for creating/finishing a 2x2 same-color block.
        score += self._square_completion_bonus(board, row, col, color)

        # Light penalty for very tall columns.
        filled = sum(1 for r in range(self.cfg.rows) if board[r][col] != 0)
        score -= filled

        return score

    def _square_completion_bonus(self, board, row, col, color):
        bonus = 0

        # Candidate 2x2 windows containing (row, col).
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
                bonus += 70
            elif same == 3 and empty == 1:
                bonus += 22
            elif same == 2 and empty == 2:
                bonus += 8

        return bonus

    def choose_target_column(self, board, piece_color):
        best_col = 0
        best_score = -10_000_000

        for col in range(self.cfg.cols):
            s = self._score_column(board, col, piece_color)
            if s > best_score:
                best_col = col
                best_score = s

        return best_col

    def move_piece(self, current_col, target_col):
        if current_col is None or target_col is None:
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

        # Fast drop once lined up.
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
                current_col, color = self.detect_falling_piece(board)

                if color is not None:
                    target_col = self.choose_target_column(board, color)
                    self.move_piece(current_col, target_col)

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
    )

    bot = MarioPuzzlePartyBot(cfg)
    bot.run()


if __name__ == "__main__":
    main()
