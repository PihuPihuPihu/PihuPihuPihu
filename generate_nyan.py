#!/usr/bin/env python3
"""
generate_nyan.py — Nyan Cat eats your GitHub contributions!

Usage:
    pip install Pillow requests
    export GITHUB_TOKEN=ghp_your_token_here
    python generate_nyan.py <github_username>
    python generate_nyan.py <github_username> --output dist/nyan.gif
"""

import os
import sys
import argparse
import requests
from PIL import Image, ImageDraw

# ── Layout ─────────────────────────────────────────────────────────────────────
CELL  = 11       # contribution square size (px)
GAP   = 2        # gap between squares
S     = CELL + GAP
WEEKS = 53
DAYS  = 7

L = 20     # left padding
T = 30     # top padding (space for day labels)
R = 75     # right padding (cat head overhangs here)
B = 25     # bottom padding

IMG_W = L + WEEKS * S + R
IMG_H = T + DAYS  * S + B

BG = (13, 17, 23)   # GitHub dark background

LEVEL_COLORS = [
    (22,  27,  34),   # 0 — no contributions
    (14,  68,  41),   # 1 — low
    (0,  109,  50),   # 2
    (38, 166,  65),   # 3
    (57, 211,  83),   # 4 — high
]

RAINBOW = [
    (255,   0,   0),
    (255, 140,   0),
    (255, 255,   0),
    (  0, 200,   0),
    (  0, 100, 255),
    (180,   0, 255),
]

# Nyan Cat colors
CAT_GRAY   = (148, 148, 148)
CAT_BLACK  = (  0,   0,   0)
TART_BASE  = (210, 155,  84)
TART_FROST = (255, 175, 200)
NOSE_PINK  = (255,  90, 130)
BLUSH      = (255, 160, 180)


# ── GitHub GraphQL API ─────────────────────────────────────────────────────────
GQL = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            weekday
          }
        }
      }
    }
  }
}
"""

def fetch_grid(username: str, token: str) -> list:
    """Fetch contributions and return grid[week][day] with level 0–4."""
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": GQL, "variables": {"login": username}},
        headers={"Authorization": f"bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()

    weeks_raw = (
        resp.json()["data"]["user"]
                   ["contributionsCollection"]
                   ["contributionCalendar"]["weeks"]
    )

    grid = []
    for week in weeks_raw[:WEEKS]:
        row = [0] * DAYS
        for day in week["contributionDays"]:
            c  = day["contributionCount"]
            wd = day["weekday"]   # 0=Sunday … 6=Saturday
            row[wd] = 0 if c == 0 else 1 if c <= 3 else 2 if c <= 6 else 3 if c <= 9 else 4
        grid.append(row)

    # Pad to full WEEKS if the year hasn't finished yet
    while len(grid) < WEEKS:
        grid.append([0] * DAYS)

    return grid


# ── Snake path (column-by-column boustrophedon) ───────────────────────────────
def make_path() -> list:
    """Returns list of (col, day) tuples in traversal order."""
    path = []
    for col in range(WEEKS):
        days = range(DAYS) if col % 2 == 0 else range(DAYS - 1, -1, -1)
        for day in days:
            path.append((col, day))
    return path


# ── Coordinate helpers ─────────────────────────────────────────────────────────
def cell_topleft(col, day):
    return L + col * S, T + day * S

def cell_center(col, day):
    x, y = cell_topleft(col, day)
    return x + CELL // 2, y + CELL // 2


# ── Draw contribution grid ─────────────────────────────────────────────────────
def draw_grid(draw: ImageDraw.ImageDraw, grid: list, eaten: set):
    for col in range(WEEKS):
        for day in range(DAYS):
            x, y  = cell_topleft(col, day)
            color = LEVEL_COLORS[0] if (col, day) in eaten else LEVEL_COLORS[grid[col][day]]
            draw.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=color)


# ── Draw rainbow trail ─────────────────────────────────────────────────────────
TRAIL_LEN = 28   # how many past cells show rainbow

def draw_rainbow_trail(draw: ImageDraw.ImageDraw, path: list, head_idx: int):
    start = max(0, head_idx - TRAIL_LEN)
    for i in range(start, head_idx):
        col, day  = path[i]
        cx, cy    = cell_center(col, day)
        stripe_h  = 2
        total_h   = len(RAINBOW) * stripe_h
        for r_idx, rc in enumerate(RAINBOW):
            ry = cy - total_h // 2 + r_idx * stripe_h
            draw.rectangle(
                [cx - CELL // 2 - 1, ry, cx + CELL // 2 + 1, ry + stripe_h - 1],
                fill=rc,
            )


# ── Draw Nyan Cat sprite ───────────────────────────────────────────────────────
def draw_nyan_cat(draw: ImageDraw.ImageDraw, col: int, day: int, frame: int):
    cx, cy = cell_center(col, day)

    # — Pop tart body (centered on the cell) —
    bx = cx - 13    # left edge of pop tart
    by = cy - 8     # top edge of pop tart
    bw = 26         # width
    bh = 16         # height

    # Tan base + black outline
    draw.rectangle([bx, by, bx + bw, by + bh], fill=TART_BASE, outline=CAT_BLACK)
    # Pink frosting
    draw.rectangle([bx + 1, by + 1, bx + bw - 1, by + bh - 1], fill=TART_FROST)
    # Sprinkles
    for sx, sy, sc in [
        (bx + 4,  by + 3,  (255,  50,  50)),
        (bx + 11, by + 4,  ( 50, 200,  50)),
        (bx + 18, by + 3,  ( 50, 100, 255)),
        (bx + 7,  by + 9,  (255, 220,  50)),
        (bx + 15, by + 9,  (255,  50, 200)),
        (bx + 21, by + 5,  (255, 150,  50)),
    ]:
        draw.rectangle([sx, sy, sx + 2, sy + 1], fill=sc)

    # — Cat head (to the right of pop tart) —
    hx = bx + bw + 2
    hy = cy - 9

    # Head circle
    draw.ellipse([hx, hy, hx + 16, hy + 16], fill=CAT_GRAY, outline=CAT_BLACK)

    # Ears
    draw.polygon(
        [(hx + 1, hy + 2), (hx + 3, hy - 5), (hx + 7, hy + 2)],
        fill=CAT_GRAY, outline=CAT_BLACK,
    )
    draw.polygon(
        [(hx + 9, hy + 2), (hx + 13, hy - 5), (hx + 15, hy + 2)],
        fill=CAT_GRAY, outline=CAT_BLACK,
    )

    # Eyes (Nyan Cat has closed squint lines)
    draw.line([hx + 3,  hy + 6, hx + 6,  hy + 6], fill=CAT_BLACK, width=2)
    draw.line([hx + 10, hy + 6, hx + 13, hy + 6], fill=CAT_BLACK, width=2)

    # Nose
    draw.ellipse([hx + 6, hy + 9, hx + 9, hy + 12], fill=NOSE_PINK)

    # Mouth (little w shape)
    draw.line([hx + 4,  hy + 14, hx + 6,  hy + 12], fill=CAT_BLACK)
    draw.line([hx + 6,  hy + 12, hx + 8,  hy + 14], fill=CAT_BLACK)
    draw.line([hx + 8,  hy + 14, hx + 10, hy + 12], fill=CAT_BLACK)
    draw.line([hx + 10, hy + 12, hx + 12, hy + 14], fill=CAT_BLACK)

    # Cheek blush
    draw.ellipse([hx + 1,  hy + 9,  hx + 4,  hy + 11], fill=BLUSH)
    draw.ellipse([hx + 12, hy + 9,  hx + 15, hy + 11], fill=BLUSH)

    # — Legs (4 legs, 2-frame walk cycle) —
    leg_positions = [bx + 3, bx + 9, bx + 15, bx + 21]
    for i, lx in enumerate(leg_positions):
        bob = 3 if (i + frame) % 2 == 0 else 0
        draw.rectangle(
            [lx, by + bh + bob, lx + 3, by + bh + 5 + bob],
            fill=CAT_GRAY, outline=CAT_BLACK,
        )

    # — Tail (wiggles every other frame) —
    wave = 3 if frame % 2 == 0 else -3
    draw.line(
        [(bx - 2, cy), (bx - 5, cy + wave), (bx - 9, cy), (bx - 12, cy - wave)],
        fill=CAT_GRAY, width=3,
    )


# ── Generate all frames and save as GIF ───────────────────────────────────────
CELLS_PER_FRAME = 2   # cells eaten per frame — lower = slower/smoother, higher = faster

def generate_gif(grid: list, output_path: str):
    path   = make_path()
    frames = []
    eaten  = set()

    for i in range(0, len(path), CELLS_PER_FRAME):
        # Advance the snake
        for j in range(CELLS_PER_FRAME):
            if i + j < len(path):
                eaten.add(path[i + j])

        head_idx       = min(i + CELLS_PER_FRAME - 1, len(path) - 1)
        head_col, head_day = path[head_idx]

        img  = Image.new("RGB", (IMG_W, IMG_H), BG)
        draw = ImageDraw.Draw(img)

        draw_grid(draw, grid, eaten)
        draw_rainbow_trail(draw, path, head_idx)
        draw_nyan_cat(draw, head_col, head_day, i // CELLS_PER_FRAME)

        frames.append(img)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    print(f"  Saving {len(frames)} frames → {output_path}")

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=60,    # ms per frame
        optimize=False,
    )

    size_kb = os.path.getsize(output_path) // 1024
    print(f"  Done! {output_path} ({size_kb} KB)")


# ── CLI entry point ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Nyan Cat eats your GitHub contributions!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_nyan.py PihuPihuPihu
  python generate_nyan.py PihuPihuPihu --output dist/nyan.gif

Token setup:
  export GITHUB_TOKEN=ghp_your_token_here
  # OR pass --token ghp_your_token_here
        """,
    )
    parser.add_argument("username", help="GitHub username")
    parser.add_argument(
        "--token", "-t",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--output", "-o",
        default="nyan.gif",
        help="Output GIF path (default: nyan.gif)",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub token is required.")
        print("  export GITHUB_TOKEN=ghp_your_token_here")
        print("  or: python generate_nyan.py <user> --token ghp_...")
        sys.exit(1)

    print(f"Fetching contributions for @{args.username}...")
    grid = fetch_grid(args.username, args.token)

    filled = sum(grid[col][day] > 0 for col in range(WEEKS) for day in range(DAYS))
    print(f"  {filled} active contribution cells found")

    print("Generating animation...")
    generate_gif(grid, args.output)


if __name__ == "__main__":
    main()
