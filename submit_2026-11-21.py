#!/usr/bin/env python3
"""
THE DAILY ORBIT - "Sum up the day's world news in one image".

A single-file, standard-library-only program that deterministically renders a
newspaper-front-page style PNG (1024x1024, well under 1 MiB) summarising one
day of world news.  PNG encoding is done by hand with zlib + struct, and all
text is drawn with a small embedded 6x9 bitmap font (no external libraries).

Usage:
    python3 makefun_news.py [YYYY-MM-DD]     (default date below)
Output:
    world-news-<date>.png  written next to this script.
"""

import os
import struct
import sys
import zlib

# --------------------------------------------------------------------------
# Embedded 6x9 bitmap font.  Each glyph is 9 rows of 6 characters.
# Capitals/digits occupy rows 0-7, lower-case x-height is rows 3-7,
# descenders (g, j, p, q, y) use row 8.
# --------------------------------------------------------------------------

_FONT_RAW = {
    " ": ["......"] * 9,
    "A": [".####.", "#....#", "#....#", "#....#", "######", "#....#", "#....#", "#....#", "......"],
    "B": ["#####.", "#....#", "#....#", "#####.", "#....#", "#....#", "#....#", "#####.", "......"],
    "C": [".#####", "#.....", "#.....", "#.....", "#.....", "#.....", "#.....", ".#####", "......"],
    "D": ["####..", "#...#.", "#....#", "#....#", "#....#", "#....#", "#...#.", "####..", "......"],
    "E": ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "#.....", "######", "......"],
    "F": ["######", "#.....", "#.....", "#####.", "#.....", "#.....", "#.....", "#.....", "......"],
    "G": [".#####", "#.....", "#.....", "#.####", "#....#", "#....#", "#....#", ".###.#", "......"],
    "H": ["#....#", "#....#", "#....#", "######", "#....#", "#....#", "#....#", "#....#", "......"],
    "I": [".####.", "..#...", "..#...", "..#...", "..#...", "..#...", "..#...", ".####.", "......"],
    "J": [".#####", "....#.", "....#.", "....#.", "....#.", "#...#.", "#...#.", ".###..", "......"],
    "K": ["#....#", "#...#.", "#..#..", "###...", "#..#..", "#...#.", "#....#", "#....#", "......"],
    "L": ["#.....", "#.....", "#.....", "#.....", "#.....", "#.....", "#.....", "######", "......"],
    "M": ["#....#", "##..##", "#.#.#.", "#.#.#.", "#....#", "#....#", "#....#", "#....#", "......"],
    "N": ["#....#", "##...#", "#.#..#", "#..#.#", "#...##", "#....#", "#....#", "#....#", "......"],
    "O": [".####.", "#....#", "#....#", "#....#", "#....#", "#....#", "#....#", ".####.", "......"],
    "P": ["#####.", "#....#", "#....#", "#####.", "#.....", "#.....", "#.....", "#.....", "......"],
    "Q": [".####.", "#....#", "#....#", "#....#", "#....#", "#..#.#", "#...#.", ".###.#", "......"],
    "R": ["#####.", "#....#", "#....#", "#####.", "#..#..", "#...#.", "#....#", "#....#", "......"],
    "S": [".#####", "#.....", "#.....", ".####.", ".....#", ".....#", ".....#", "#####.", "......"],
    "T": ["######", "..#...", "..#...", "..#...", "..#...", "..#...", "..#...", "..#...", "......"],
    "U": ["#....#", "#....#", "#....#", "#....#", "#....#", "#....#", "#....#", ".####.", "......"],
    "V": ["#....#", "#....#", "#....#", "#....#", "#....#", ".#..#.", ".#..#.", "..##..", "......"],
    "W": ["#....#", "#....#", "#....#", "#....#", "#.#.#.", "#.#.#.", "##..##", "#....#", "......"],
    "X": ["#....#", ".#..#.", ".#..#.", "..##..", "..##..", ".#..#.", ".#..#.", "#....#", "......"],
    "Y": ["#....#", "#....#", ".#..#.", ".#..#.", "..#...", "..#...", "..#...", "..#...", "......"],
    "Z": ["######", ".....#", "....#.", "...#..", "..#...", ".#....", "#.....", "######", "......"],
    "a": ["......", "......", "......", ".####.", ".....#", ".#####", "#....#", ".####.", "......"],
    "b": ["#.....", "#.....", "#.....", "#####.", "#....#", "#....#", "#....#", "#####.", "......"],
    "c": ["......", "......", "......", ".#####", "#.....", "#.....", "#.....", ".#####", "......"],
    "d": [".....#", ".....#", ".....#", ".#####", "#....#", "#....#", "#....#", ".#####", "......"],
    "e": ["......", "......", "......", ".####.", "#....#", "######", "#.....", ".####.", "......"],
    "f": ["..###.", "..#...", "..#...", ".####.", "..#...", "..#...", "..#...", "..#...", "......"],
    "g": ["......", "......", "......", ".#####", "#....#", "#....#", ".#####", ".....#", ".####."],
    "h": ["#.....", "#.....", "#.....", "#####.", "#....#", "#....#", "#....#", "#....#", "......"],
    "i": ["......", "..#...", "......", ".##...", "..#...", "..#...", "..#...", ".###..", "......"],
    "j": ["......", "....#.", "......", "..###.", "...#..", "...#..", "...#..", "...#..", ".##..."],
    "k": ["#.....", "#.....", "#.....", "#....#", "#...#.", "#..#..", "#...#.", "#....#", "......"],
    "l": [".##...", "..#...", "..#...", "..#...", "..#...", "..#...", "..#...", ".###..", "......"],
    "m": ["......", "......", "......", "##.##.", "#.#.#.", "#.#.#.", "#.#.#.", "#.#.#.", "......"],
    "n": ["......", "......", "......", "#####.", "#....#", "#....#", "#....#", "#....#", "......"],
    "o": ["......", "......", "......", ".####.", "#....#", "#....#", "#....#", ".####.", "......"],
    "p": ["......", "......", "......", "#####.", "#....#", "#....#", "#####.", "#.....", "#....."],
    "q": ["......", "......", "......", ".#####", "#....#", "#....#", ".#####", ".....#", ".....#"],
    "r": ["......", "......", "......", "#.###.", "##....", "#.....", "#.....", "#.....", "......"],
    "s": ["......", "......", "......", ".#####", "#.....", ".####.", ".....#", "#####.", "......"],
    "t": ["......", "..#...", "..#...", ".####.", "..#...", "..#...", "..#...", "...##.", "......"],
    "u": ["......", "......", "......", "#....#", "#....#", "#....#", "#....#", ".####.", "......"],
    "v": ["......", "......", "......", "#....#", "#....#", "#....#", ".#..#.", "..##..", "......"],
    "w": ["......", "......", "......", "#....#", "#....#", "#.#.#.", "#.#.#.", "##..##", "......"],
    "x": ["......", "......", "......", "#....#", ".#..#.", "..##..", ".#..#.", "#....#", "......"],
    "y": ["......", "......", "......", "#....#", "#....#", ".#..#.", ".#..#.", "..##..", ".#...."],
    "z": ["......", "......", "......", "######", "....#.", "...#..", "..#...", "######", "......"],
    "0": [".####.", "#....#", "#...##", "#..#.#", "##...#", "#....#", "#....#", ".####.", "......"],
    "1": ["..#...", ".##...", "..#...", "..#...", "..#...", "..#...", "..#...", ".#####", "......"],
    "2": [".####.", "#....#", ".....#", "...##.", "..#...", ".#....", "#.....", "######", "......"],
    "3": [".####.", "#....#", ".....#", "..###.", ".....#", ".....#", "#....#", ".####.", "......"],
    "4": ["...#..", "..##..", ".#.#..", "#..#..", "######", "...#..", "...#..", "...#..", "......"],
    "5": ["######", "#.....", "#####.", ".....#", ".....#", ".....#", "#....#", ".####.", "......"],
    "6": [".####.", "#....#", "#.....", "#####.", "#....#", "#....#", "#....#", ".####.", "......"],
    "7": ["######", ".....#", "....#.", "....#.", "...#..", "...#..", "...#..", "...#..", "......"],
    "8": [".####.", "#....#", "#....#", ".####.", "#....#", "#....#", "#....#", ".####.", "......"],
    "9": [".####.", "#....#", "#....#", ".#####", ".....#", "#....#", "#....#", ".####.", "......"],
    ".": ["......", "......", "......", "......", "......", "......", ".##...", ".##...", "......"],
    ",": ["......", "......", "......", "......", "......", "......", ".##...", ".##...", ".#...."],
    ":": ["......", "......", ".##...", "......", "......", "......", ".##...", "......", "......"],
    ";": ["......", "......", ".##...", "......", "......", "......", ".##...", "......", ".#...."],
    "!": ["..#...", "..#...", "..#...", "..#...", "..#...", "..#...", "......", "..#...", "......"],
    "?": [".####.", "#....#", ".....#", "...##.", "..#...", "..#...", "......", "..#...", "......"],
    "'": ["..#...", "..#...", ".#....", "......", "......", "......", "......", "......", "......"],
    "-": ["......", "......", "......", "......", "#####.", "......", "......", "......", "......"],
    "(": ["....#.", "...#..", "..#...", "..#...", "..#...", "..#...", "...#..", "....#.", "......"],
    ")": [".#....", "..#...", "...#..", "...#..", "...#..", "...#..", "..#...", ".#....", "......"],
    "/": [".....#", ".....#", "....#.", "...#..", "..#...", "..#...", ".#....", "#.....", "......"],
    "%": ["##...#", "##..#.", "....#.", "...#..", "..#...", ".#....", ".#..##", "#...##", "......"],
    "$": ["..#...", ".#####", "#.#...", ".####.", "..#.#.", "#####.", "..#...", "......", "......"],
    "+": ["......", "......", "..#...", "..#...", ".#####", "..#...", "..#...", "......", "......"],
    "=": ["......", "......", "......", ".#####", "......", ".#####", "......", "......", "......"],
    '"': [".#..#.", ".#..#.", ".#..#.", "......", "......", "......", "......", "......", "......"],
    "&": ["..##..", ".#..#.", ".#.#..", "..#...", ".#.#.#", "#..#..", "#...#.", ".###..", "......"],
    "*": ["......", "......", ".#..#.", "..##..", ".#..#.", "......", "......", "......", "......"],
}

GLYPH_W = 6
GLYPH_H = 9
ADVANCE = 7  # glyph width + 1 unit of letter spacing, in font units


def _normalise_font():
    font = {}
    for ch, rows in _FONT_RAW.items():
        rows = [(r + "......")[:GLYPH_W] for r in rows]
        rows = (rows + ["......"] * GLYPH_H)[:GLYPH_H]
        font[ch] = rows
    return font


FONT = _normalise_font()
FALLBACK = FONT["?"]


# --------------------------------------------------------------------------
# Canvas + hand-rolled PNG encoder (zlib / struct only)
# --------------------------------------------------------------------------

W = 1024
H = 1024

PAPER = (247, 243, 234)
PAPER_DARK = (238, 231, 216)
INK = (26, 25, 23)
INK_SOFT = (58, 55, 50)
GRAY = (107, 103, 95)
RULE = (196, 188, 168)
WHITE = (255, 255, 255)

CAT_COLORS = {
    "CONFLICT": (179, 53, 43),
    "JUSTICE": (91, 75, 138),
    "ECONOMY": (14, 107, 107),
    "BUSINESS": (14, 107, 107),
    "POLITICS": (31, 58, 95),
    "DIPLOMACY": (31, 58, 95),
    "CLIMATE": (62, 124, 43),
    "HEALTH": (160, 48, 96),
    "SCIENCE": (52, 68, 158),
    "SPACE": (52, 68, 158),
    "TECHNOLOGY": (120, 72, 20),
    "AI DIPLOMACY": (120, 72, 20),
    "MIDDLE EAST": (176, 92, 30),
    "SOCIETY": (84, 96, 110),
    "DISASTER": (150, 40, 40),
    "EUROPE": (31, 58, 95),
    "SPORT": (62, 124, 43),
}


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.rect(x, y, thick, h, color)

    def circle(self, cx, cy, r, color, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill and d2 <= r * r:
                    self.px(xx, yy, color)
                elif not fill and r * r - 2 * r <= d2 <= r * r + 2 * r:
                    self.px(xx, yy, color)

    def triangle_up(self, cx, cy, s, color):
        for i in range(s):
            self.hline(cx - i, cy - s + 1 + i, 2 * i + 1, color)

    def triangle_down(self, cx, cy, s, color):
        for i in range(s):
            self.hline(cx - i, cy + i, 2 * i + 1, color)


def save_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter type 0 (None) for every scanline
        raw += canvas.buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# --------------------------------------------------------------------------
# Text engine on top of the bitmap font
# --------------------------------------------------------------------------

def text_width(text, scale=1, tracking=0):
    if not text:
        return 0
    return (len(text) * (ADVANCE + tracking) - tracking) * scale


def draw_text(cv, x, y, text, scale=1, color=INK, bold=False, tracking=0):
    """Draw text with its top-left at (x, y). Returns the drawn width in px."""
    extra = max(1, scale // 2) if bold else 0
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FALLBACK)
        for gy, row in enumerate(glyph):
            for gx, cell in enumerate(row):
                if cell == "#":
                    cv.rect(cx + gx * scale, y + gy * scale,
                            scale + extra, scale, color)
        cx += (ADVANCE + tracking) * scale
    return (cx - x) - tracking * scale if text else 0


def draw_text_centered(cv, cx, y, text, scale=1, color=INK, bold=False, tracking=0):
    w = text_width(text, scale, tracking)
    return draw_text(cv, cx - w // 2, y, text, scale, color, bold, tracking)


def draw_text_right(cv, rx, y, text, scale=1, color=INK, bold=False, tracking=0):
    w = text_width(text, scale, tracking)
    return draw_text(cv, rx - w, y, text, scale, color, bold, tracking)


def wrap_text(text, max_px, scale=1, bold=False, tracking=0):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, tracking) <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, text, max_px, scale=1, color=INK, bold=False,
                 tracking=0, line_gap=6, align="left", max_lines=None):
    """Draw word-wrapped text; returns y just below the last line."""
    lines = wrap_text(text, max_px, scale, tracking)
    if max_lines is not None:
        lines = lines[:max_lines]
    lh = GLYPH_H * scale + line_gap
    for i, line in enumerate(lines):
        ly = y + i * lh
        if align == "center":
            draw_text_centered(cv, x + max_px // 2, ly, line, scale, color, bold, tracking)
        elif align == "right":
            draw_text_right(cv, x + max_px, ly, line, scale, color, bold, tracking)
        else:
            draw_text(cv, x, ly, line, scale, color, bold, tracking)
    return y + len(lines) * lh - line_gap


def draw_globe(cv, cx, cy, r, color):
    """Small line-art globe: outline, two meridian ellipses, two parallels."""
    cv.circle(cx, cy, r, color, fill=False)
    import math
    for frac in (0.45, 0.85):
        rx = max(2, int(r * frac))
        for deg in range(0, 360, 2):
            a = deg * math.pi / 180.0
            xx = cx + int(rx * math.cos(a))
            yy = cy + int(r * math.sin(a))
            cv.px(xx, yy, color)
            cv.px(xx, yy + 1, color)
    for frac in (-0.45, 0.45):
        yy = cy + int(r * frac)
        half = int((r * r - (r * frac) ** 2) ** 0.5)
        cv.hline(cx - half, yy, 2 * half, color, 2)
    cv.vline(cx, cy - r, 2 * r, color, 1)


# --------------------------------------------------------------------------
# Front-page layout
# --------------------------------------------------------------------------

MARGIN = 36
PAGE_W = W - 2 * MARGIN


def kicker(cv, x, y, cat, place):
    color = CAT_COLORS.get(cat, INK)
    cv.rect(x, y + 1, 10, 10, color)
    draw_text(cv, x + 18, y, cat, 1, color, bold=True, tracking=2)
    if place:
        w = text_width(cat, 1, 2)
        draw_text(cv, x + 18 + w + 14, y, "- " + place, 1, GRAY, tracking=2)
    return y + 14


def story_block(cv, x, y, w, story, head_scale, body_scale, body_gap=5):
    y = kicker(cv, x, y, story["cat"], story.get("place", ""))
    y += 3
    y = draw_wrapped(cv, x, y, story["headline"], w, head_scale, INK,
                     bold=True, line_gap=5)
    y += 6
    y = draw_wrapped(cv, x, y, story["summary"], w, body_scale, INK_SOFT,
                     line_gap=body_gap)
    return y


def render(data):
    cv = Canvas(W, H, PAPER)
    x0 = MARGIN
    xr = W - MARGIN

    # ---- masthead ------------------------------------------------------
    y = 18
    cv.hline(x0, y, PAGE_W, INK, 2)
    y += 10
    draw_globe(cv, x0 + 30, y + 24, 26, INK)
    draw_globe(cv, xr - 30, y + 24, 26, INK)
    draw_text_centered(cv, W // 2, y, "THE DAILY ORBIT", 5, INK, bold=True, tracking=1)
    y += 9 * 5 + 8
    draw_text_centered(cv, W // 2, y, "THE WORLD'S FRONT PAGE - IN ONE IMAGE",
                       1, GRAY, tracking=3)
    y += 17
    draw_text(cv, x0, y + 3, "EDITION NO. " + data["edition"], 1, INK_SOFT, tracking=2)
    draw_text_centered(cv, W // 2, y, data["date_line"], 2, INK, bold=True, tracking=1)
    draw_text_right(cv, xr, y + 3, "ONE DAY - ONE IMAGE", 1, INK_SOFT, tracking=2)
    y += 23
    cv.hline(x0, y, PAGE_W, INK, 5)
    cv.hline(x0, y + 7, PAGE_W, INK, 1)
    y += 14

    # ---- digest band ---------------------------------------------------
    cv.rect(x0, y, PAGE_W, 30, INK)
    draw_text_centered(cv, W // 2, y + 6, data["digest"], 2, PAPER, bold=True)
    y += 30 + 8

    # ---- lead story ----------------------------------------------------
    lead = data["lead"]
    side_w = 232
    main_w = PAGE_W - side_w - 24
    lead_top = y
    y = kicker(cv, x0, y, lead["cat"], lead.get("place", ""))
    y += 3
    y = draw_wrapped(cv, x0, y, lead["headline"], main_w, 4, INK, bold=True, line_gap=7)
    y += 8
    y = draw_wrapped(cv, x0, y, lead["summary"], main_w, 2, INK_SOFT, line_gap=5)
    lead_bottom = y

    # side box: by the numbers / in short (height fitted to its content)
    bx = xr - side_w
    box_h = 16 + 22 + 12
    for _value, label in lead["side_items"]:
        n = len(wrap_text(label, side_w - 32, 1))
        box_h += 32 + n * 12 - 3 + 12
    cv.rect(bx, lead_top, side_w, 4, CAT_COLORS.get(lead["cat"], INK))
    cv.rect(bx, lead_top + 4, side_w, box_h - 4, PAPER_DARK)
    by = lead_top + 16
    draw_text(cv, bx + 16, by, lead["side_title"], 1,
              CAT_COLORS.get(lead["cat"], INK), bold=True, tracking=2)
    by += 22
    for value, label in lead["side_items"]:
        draw_text(cv, bx + 16, by, value, 3, INK, bold=True)
        by += 32
        by = draw_wrapped(cv, bx + 16, by, label, side_w - 32, 1, INK_SOFT,
                          line_gap=3)
        by += 12
    lead_h = max(lead_bottom, lead_top + box_h) - lead_top
    cv.vline(bx - 12, lead_top, lead_h, RULE, 1)
    y = lead_top + lead_h + 8
    cv.hline(x0, y, PAGE_W, RULE, 1)
    y += 8

    # ---- two secondary stories ------------------------------------------
    col_w = (PAGE_W - 28) // 2
    sec_y = y
    ends = []
    for i, story in enumerate(data["secondary"]):
        sx = x0 + i * (col_w + 28)
        ends.append(story_block(cv, sx, sec_y, col_w, story, 3, 1))
    cv.vline(x0 + col_w + 13, sec_y, max(ends) - sec_y, RULE, 1)
    y = max(ends) + 8
    cv.hline(x0, y, PAGE_W, RULE, 1)
    y += 8

    # ---- band: markets or quote of the day ------------------------------
    band = data.get("band")
    if band:
        if band["type"] == "markets":
            cv.rect(x0, y, PAGE_W, 54, INK)
            items = band["items"]
            iw = PAGE_W // len(items)
            for i, (name, val, chg, up) in enumerate(items):
                ix = x0 + i * iw + 14
                if i:
                    cv.vline(x0 + i * iw, y + 8, 38, (70, 66, 60), 1)
                draw_text(cv, ix, y + 7, name, 1, (168, 160, 146), tracking=1)
                col = (110, 200, 120) if up else (235, 110, 95)
                if up:
                    cv.triangle_up(ix + 4, y + 33, 6, col)
                else:
                    cv.triangle_down(ix + 4, y + 28, 6, col)
                if val:
                    vw = draw_text(cv, ix + 16, y + 24, val, 2, PAPER, bold=True)
                    draw_text(cv, ix + 16 + vw + 8, y + 26, chg, 1, col, bold=True)
                else:
                    draw_text(cv, ix + 16, y + 24, chg, 2, col, bold=True)
            y += 54 + 8
        elif band["type"] == "quote":
            cv.rect(x0, y, PAGE_W, 46, PAPER_DARK)
            cv.rect(x0, y, 4, 46, INK)
            draw_text(cv, x0 + 16, y + 6, band["label"], 1, GRAY,
                      bold=True, tracking=2)
            draw_text(cv, x0 + 16, y + 21, band["text"], 2, INK, bold=True)
            y += 46 + 8

    # ---- grid of six -----------------------------------------------------
    grid = data["grid"]
    rows = [grid[0:2], grid[2:4], grid[4:6]]
    for r, row in enumerate(rows):
        row_y = y
        ends = []
        for i, story in enumerate(row):
            sx = x0 + i * (col_w + 28)
            ends.append(story_block(cv, sx, row_y, col_w, story, 2, 1,
                                    body_gap=4))
        cv.vline(x0 + col_w + 13, row_y, max(ends) - row_y, RULE, 1)
        y = max(ends) + 10
        if r < len(rows) - 1:
            cv.hline(x0, y, PAGE_W, RULE, 1)
            y += 10

    # ---- in brief ---------------------------------------------------------
    cv.rect(x0, y, PAGE_W, 3, INK)
    y += 9
    draw_text(cv, x0, y, "IN BRIEF", 1, INK, bold=True, tracking=3)
    y += 17
    briefs = data["briefs"]
    bw = (PAGE_W - 3 * 20) // 4
    for i, (cat, text) in enumerate(briefs):
        bx = x0 + i * (bw + 20)
        color = CAT_COLORS.get(cat, INK)
        cv.circle(bx + 4, y + 6, 4, color)
        draw_wrapped(cv, bx + 15, y, text, bw - 15, 1, INK_SOFT,
                     line_gap=3, max_lines=3)
    y += 2 * 12 + 8

    # ---- footer ------------------------------------------------------------
    cv.hline(x0, y, PAGE_W, INK, 2)
    y += 8
    draw_text_centered(cv, W // 2, y, data["footer"], 1, GRAY, tracking=2)
    cv.end_y = y + 9
    return cv


# --------------------------------------------------------------------------
# The news itself (verified against multiple outlets; see news-notes.md)
# --------------------------------------------------------------------------

EDITIONS = {
    "2026-11-21": {
        "edition": "325",
        "date_line": "SATURDAY, NOVEMBER 21, 2026",
        "digest": "RUSSIA POUNDS UKRAINE - AI STOCKS TUMBLE",
        "lead": {
            "cat": "CONFLICT", "place": "KYIV, UKRAINE",
            "headline": "RUSSIA'S HUGE BARRAGE HITS UKRAINE; MISSILES LAND IN POLAND",
            "summary": "Russia fired 400+ drones and 110 missiles at Ukraine "
                       "overnight, killing at least eight in Kyiv and damaging "
                       "bridges and stations. Two missiles and a suspected drone "
                       "came down in Poland; Warsaw called it deliberate "
                       "provocation.",
            "side_title": "BY THE NUMBERS",
            "side_items": [
                ("400+", "drones fired at Ukraine overnight"),
                ("110", "missiles launched in the barrage"),
                ("2", "missiles down on Polish soil"),
            ],
        },
        "secondary": [
            {
                "cat": "JUSTICE", "place": "THE HAGUE",
                "headline": "UN COURT FINDS MYANMAR GUILTY OF GENOCIDE",
                "summary": "The International Court of Justice ruled Myanmar "
                           "committed genocide against the Rohingya, in a "
                           "landmark judgment.",
            },
            {
                "cat": "ECONOMY", "place": "NEW YORK",
                "headline": "AI SELL-OFF PUSHES S&P 500 INTO CORRECTION",
                "summary": "US stocks fell 3.7% Friday as investors dumped AI and "
                           "chip shares. The Nikkei slid 5.06% and gold dropped "
                           "3.98%.",
            },
        ],
        "band": {
            "type": "markets",
            "items": [
                ("S&P 500", "6,910", "3.70%", False),
                ("NIKKEI", "", "5.06%", False),
                ("GOLD", "", "3.98%", False),
                ("BRENT", "$89.87", "0.48%", True),
                ("EUR/USD", "1.10", "0.02%", True),
            ],
        },
        "grid": [
            {
                "cat": "POLITICS", "place": "BRUSSELS",
                "headline": "UK AND EU SIGN BIGGEST POST-BREXIT AGREEMENTS",
                "summary": "Prime Minister Andy Burnham and EU leaders signed "
                           "three deals on food exports, carbon markets and youth "
                           "mobility.",
            },
            {
                "cat": "CLIMATE", "place": "ANTALYA",
                "headline": "COP31 TALKS RUN PAST DEADLINE OVER FOSSIL FUELS",
                "summary": "The UN climate summit in Turkey ran into overtime as "
                           "nearly 200 nations failed to agree on fossil fuel "
                           "language.",
            },
            {
                "cat": "HEALTH", "place": "LONDON",
                "headline": "CANCER PILL CLEARS TUMOURS IN 1 IN 12 PATIENTS",
                "summary": "The pill daraxonrasib made pancreatic cancer "
                           "undetectable on scans in one in 12 patients in a "
                           "clinical trial.",
            },
            {
                "cat": "SCIENCE", "place": "SAN FRANCISCO",
                "headline": "ANTHROPIC SAYS CLAUDE SOLVED MATHS' GREATEST RIDDLE",
                "summary": "An Anthropic researcher says its AI model Claude "
                           "solved the Riemann Hypothesis, unsolved for over "
                           "160 years.",
            },
            {
                "cat": "MIDDLE EAST", "place": "STRAIT OF HORMUZ",
                "headline": "IRAN CLAIMS US DRONE DOWNED AS TRUMP WEIGHS STRIKES",
                "summary": "Iran says it shot down a US MQ-9 drone over the "
                           "strait, while Trump weighs new strikes and Tehran "
                           "urges diplomacy.",
            },
            {
                "cat": "SOCIETY", "place": "BERLIN",
                "headline": "GEN Z PROTESTS SPREAD ACROSS 25 EUROPEAN COUNTRIES",
                "summary": "Thousands of students marched across Europe over "
                           "living costs, military spending and climate policy.",
            },
        ],
        "briefs": [
            ("DISASTER", "Magnitude 6.7 earthquake shakes central Peru"),
            ("SPACE", "BepiColombo reaches Mercury orbit after eight years"),
            ("SPORT", "Alcaraz stays unbeaten in ATP Finals group play in Turin"),
            ("SPORT", "Mao Shimada leads Finlandia Trophy after short program"),
        ],
        "footer": "SOURCES: AP - SCMP - THE JAPAN TIMES - STANDARD TOPIC - ONE TURN",
    },
    "2026-11-20": {
        "edition": "324",
        "date_line": "FRIDAY, NOVEMBER 20, 2026",
        "digest": "THREE POWERS PLEDGE PEACE - RECORD $81B IPO",
        "lead": {
            "cat": "DIPLOMACY", "place": "SHENZHEN, CHINA",
            "headline": "TRUMP, XI AND PUTIN ISSUE JOINT PEACE DECLARATION",
            "summary": "Donald Trump, Xi Jinping and Vladimir Putin held their "
                       "first three-way meeting in Shenzhen and issued a "
                       "declaration committing to peace and stability. Analysts "
                       "saw little concrete progress.",
            "side_title": "THE SUMMIT IN SHORT",
            "side_items": [
                ("1ST", "Trump-Xi-Putin three-way meeting"),
                ("3", "superpowers at one table in Shenzhen"),
                ("1", "joint declaration on peace and stability"),
            ],
        },
        "secondary": [
            {
                "cat": "BUSINESS", "place": "NEW YORK",
                "headline": "ANTHROPIC'S $81B IPO IS THE LARGEST EVER",
                "summary": "The AI firm's debut raised $81 billion, surpassing "
                           "SpaceX, as shares opened 33% above the offer price.",
            },
            {
                "cat": "CONFLICT", "place": "KYIV, UKRAINE",
                "headline": "RUSSIAN BARRAGE HITS KYIV EMBASSIES",
                "summary": "A daytime attack blew out windows at the Austrian and "
                           "Dutch embassies and damaged a cathedral in Kyiv.",
            },
        ],
        "band": {
            "type": "quote",
            "label": "REACTION - BERLIN",
            "text": "MERZ WARNS EUROPE MUST NOT BE SIDELINED IN ANY SETTLEMENT",
        },
        "grid": [
            {
                "cat": "TECHNOLOGY", "place": "WASHINGTON",
                "headline": "WHITE HOUSE OUSTS CYBER CHIEF AMID OUTAGE CHAOS",
                "summary": "Cyber director Sean Cairncross stepped down amid US "
                           "tech outages, as a nine-hour Microsoft 365 failure "
                           "hit services.",
            },
            {
                "cat": "MIDDLE EAST", "place": "RIYADH",
                "headline": "HOUTHI MISSILE HITS RIYADH'S TALLEST SKYSCRAPER",
                "summary": "A missile blew out windows on eight floors of "
                           "Riyadh's tallest tower - a second attack on the "
                           "financial district this month.",
            },
            {
                "cat": "DISASTER", "place": "GEORGIA",
                "headline": "GAS BLAST COLLAPSES FLATS, KILLING SIX",
                "summary": "A blast tore through a residential block in Georgia, "
                           "collapsing part of the building and killing six "
                           "people.",
            },
            {
                "cat": "SPACE", "place": "DEEP SPACE",
                "headline": "VOYAGER 1 PHONES HOME FROM ONE LIGHT-DAY AWAY",
                "summary": "NASA's Voyager 1, launched in 1977, signalled from "
                           "about one light-day away - the farthest any human-made "
                           "object has reached.",
            },
            {
                "cat": "EUROPE", "place": "COPENHAGEN",
                "headline": "DENMARK APPROVES US-GREENLAND SECURITY DEAL",
                "summary": "Danish lawmakers approved a trilateral security "
                           "agreement with the United States and Greenland, "
                           "deepening defence ties in the Arctic.",
            },
            {
                "cat": "AI DIPLOMACY", "place": "SHENZHEN",
                "headline": "US AND CHINA AGREE: HUMANS MUST OVERSEE MILITARY AI",
                "summary": "Treasury Secretary Bessent said Trump and Xi agreed "
                           "humans must oversee decisions on using AI in major "
                           "military operations.",
            },
        ],
        "briefs": [
            ("CLIMATE", "COP31 draft stalls over fossil fuels in Antalya"),
            ("CONFLICT", "Haiti police say 34 suspected gang members killed"),
            ("CONFLICT", "Ukrainian strikes down a span of the Crimean Bridge"),
            ("CONFLICT", "Russian bombers enter Taiwan's air defence zone"),
        ],
        "footer": "SOURCES: SCMP - AP - OPEN CHRONICLE - STANDARD TOPIC - INFORMED CLEARLY",
    },
}

DEFAULT_DATE = "2026-11-21"


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATE
    if date not in EDITIONS:
        print("no edition for %s (have: %s)" % (date, ", ".join(sorted(EDITIONS))))
        return 1
    cv = render(EDITIONS[date])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "world-news-%s.png" % date)
    size = save_png(cv, out)
    print("wrote %s (%d bytes, content ends at y=%d of %d)"
          % (out, size, cv.end_y, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
