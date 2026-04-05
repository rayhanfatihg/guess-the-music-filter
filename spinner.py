"""
spinner.py
----------
Song-spinner overlay for the Guess-the-Song filter.

State machine
  IDLE     →  shows "SPACE to spin" prompt
  SPINNING →  cycles through album covers fast → slow (eased)
  RESULT   →  locks on selected song, shows "Sing it!" for a few seconds
             → auto-returns to IDLE

Public API
  spinner = SongSpinner(csv_path, cover_dir)
  spinner.trigger_spin()          # call on SPACE key
  frame   = spinner.render_overlay(frame, anchor_x, anchor_y)
"""

import csv
import os
import random
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ─── Font loading ─────────────────────────────────────────────────────────────

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_TITLE  = _load_font(19)
FONT_ARTIST = _load_font(14)
FONT_LABEL  = _load_font(13)


# ─── Spinner class ────────────────────────────────────────────────────────────

class SongSpinner:
    # States
    IDLE     = "idle"
    SPINNING = "spinning"
    RESULT   = "result"

    # Card dimensions
    CARD_W   = 230
    CARD_H   = 290
    ART_SIZE = 160
    RADIUS   = 18

    # Timings
    SPIN_DURATION   = 3.5   # seconds to spin
    RESULT_DURATION = 7.0   # seconds to display result before auto-reset

    def __init__(self, csv_path: str, cover_dir: str) -> None:
        self.songs:  list[dict]       = []
        self.covers: dict[str, Image.Image | None] = {}
        self._load_data(csv_path, cover_dir)

        self.state        = self.IDLE
        self.selected_idx = 0
        self.display_idx  = 0

        self._spin_pos:    float = 0.0
        self._spin_start:  float = 0.0
        self._result_start: float = 0.0
        self._last_t:      float = time.perf_counter()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data(self, csv_path: str, cover_dir: str) -> None:
        with open(csv_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                self.songs.append(row)

        for song in self.songs:
            sid  = song["id"]
            path = os.path.join(cover_dir, f"{sid}.jpg")
            try:
                img = Image.open(path).convert("RGBA")
                img = img.resize((self.ART_SIZE, self.ART_SIZE), Image.LANCZOS)
                # Circular crop mask
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).ellipse((0, 0, self.ART_SIZE - 1, self.ART_SIZE - 1), fill=255)
                img.putalpha(mask)
                self.covers[sid] = img
            except Exception:
                self.covers[sid] = None

        print(f"[Spinner] Loaded {len(self.songs)} songs.")

    # ── Public API ────────────────────────────────────────────────────────────

    def trigger_spin(self) -> None:
        """Trigger spinning. Safe to call from any state."""
        if self.state in (self.IDLE, self.RESULT):
            self.selected_idx = random.randint(0, len(self.songs) - 1)
            self._spin_start  = time.perf_counter()
            self._spin_pos    = float(self.display_idx)
            self.state        = self.SPINNING

    def update(self) -> None:
        """Advance animation. Called automatically by render_overlay."""
        now = time.perf_counter()
        dt  = min(now - self._last_t, 0.1)   # cap at 100 ms
        self._last_t = now

        if self.state == self.SPINNING:
            elapsed = now - self._spin_start
            t       = min(elapsed / self.SPIN_DURATION, 1.0)
            # Songs/second: 28 → 0, eased with (1-t)²
            speed   = 28.0 * (1.0 - t) ** 2
            self._spin_pos   = (self._spin_pos + speed * dt) % len(self.songs)
            self.display_idx = int(self._spin_pos)
            if t >= 1.0:
                self.display_idx   = self.selected_idx
                self._result_start = now
                self.state         = self.RESULT

        elif self.state == self.RESULT:
            if now - self._result_start >= self.RESULT_DURATION:
                self.state = self.IDLE

    def render_overlay(
        self,
        frame: np.ndarray,
        anchor_x: int,
        anchor_y: int,
    ) -> np.ndarray:
        """
        Render the spinning card above (anchor_x, anchor_y) onto frame.
        Returns the modified frame.
        """
        self.update()
        card = self._build_card()
        # Centre card horizontally at anchor; bottom of card sits 20 px above forehead
        ox = anchor_x - self.CARD_W // 2
        oy = anchor_y - self.CARD_H - 20
        return self._paste_rgba(frame, card, ox, oy)

    # ── Card builder ──────────────────────────────────────────────────────────

    def _build_card(self) -> Image.Image:
        w, h = self.CARD_W, self.CARD_H
        card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        # Background colour varies by state
        if self.state == self.RESULT:
            bg   = (15, 50, 20, 220)
            ring = (60, 230, 100, 200)
        elif self.state == self.SPINNING:
            bg   = (20, 20, 40, 210)
            ring = (255, 200, 50, 200)
        else:
            bg   = (20, 20, 35, 190)
            ring = (100, 100, 150, 160)

        draw.rounded_rectangle(
            (0, 0, w - 1, h - 1),
            radius=self.RADIUS,
            fill=bg,
            outline=ring,
            width=2,
        )

        # Album art (circular)
        art_x = (w - self.ART_SIZE) // 2
        art_y = 18
        song  = self.songs[self.display_idx]
        cover = self.covers.get(song["id"])
        if cover:
            card.paste(cover, (art_x, art_y), cover)
        else:
            draw.ellipse(
                (art_x, art_y, art_x + self.ART_SIZE - 1, art_y + self.ART_SIZE - 1),
                fill=(60, 60, 70, 200),
            )
            self._draw_centered(draw, "♪", FONT_TITLE, w, art_y + self.ART_SIZE // 2 - 12,
                                fill=(200, 200, 200, 255))

        # Ring highlight around art during result
        if self.state == self.RESULT:
            draw.ellipse(
                (art_x - 3, art_y - 3, art_x + self.ART_SIZE + 2, art_y + self.ART_SIZE + 2),
                outline=(60, 230, 100, 200),
                width=3,
            )

        # Song name
        ty = art_y + self.ART_SIZE + 14
        self._draw_centered(draw, song["song_name"], FONT_TITLE, w, ty,
                            fill=(255, 255, 255, 255), max_w=w - 16)

        # Artist name
        ty += 26
        self._draw_centered(draw, song["artist"], FONT_ARTIST, w, ty,
                            fill=(180, 180, 200, 220), max_w=w - 16)

        # State label
        ty += 22
        if self.state == self.SPINNING:
            label, col = "🎵  Spinning…",    (255, 220, 50, 255)
        elif self.state == self.RESULT:
            label, col = "🎤  Sing it!",     (80, 255, 120, 255)
        else:
            label, col = "SPACE  to  spin",  (140, 140, 170, 200)
        self._draw_centered(draw, label, FONT_LABEL, w, ty, fill=col)

        return card

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _draw_centered(
        draw: ImageDraw.Draw,
        text: str,
        font,
        card_w: int,
        y: int,
        fill,
        max_w: int = 9999,
    ) -> None:
        while True:
            bb = draw.textbbox((0, 0), text, font=font)
            tw = bb[2] - bb[0]
            if tw <= max_w or len(text) <= 4:
                break
            text = text[:-2] + "…"
        draw.text(((card_w - tw) / 2, y), text, font=font, fill=fill)

    @staticmethod
    def _paste_rgba(
        frame: np.ndarray,
        overlay: Image.Image,
        ox: int,
        oy: int,
    ) -> np.ndarray:
        """Alpha-blend a PIL RGBA image onto a BGR OpenCV frame."""
        fh, fw = frame.shape[:2]
        iw, ih = overlay.size

        # Clamp to frame
        x0 = max(ox, 0);      y0 = max(oy, 0)
        x1 = min(ox + iw, fw); y1 = min(oy + ih, fh)
        if x0 >= x1 or y0 >= y1:
            return frame

        crop   = overlay.crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy))
        arr    = np.array(crop, dtype=np.float32)       # H×W×4
        alpha  = arr[:, :, 3:] / 255.0                  # H×W×1

        bgr    = arr[:, :, [2, 1, 0]]                   # RGB → BGR
        roi    = frame[y0:y1, x0:x1].astype(np.float32)
        frame[y0:y1, x0:x1] = (bgr * alpha + roi * (1.0 - alpha)).astype(np.uint8)
        return frame
