#!/usr/bin/env python3
"""
generate_nyan.py — Sparkle cat eats your GitHub contributions!
 
Usage:
    pip install Pillow requests
    export GITHUB_TOKEN=ghp_your_token_here
    python generate_nyan.py <github_username>
    python generate_nyan.py <github_username> --output dist/nyan.gif
"""
 
import os, sys, argparse, random, requests
from PIL import Image, ImageDraw
 
# ── Layout ─────────────────────────────────────────────────────────────────────
CELL  = 11
GAP   = 2
S     = CELL + GAP
WEEKS = 53
DAYS  = 7
 
L = 20
T = 40
R = 40
B = 40
 
IMG_W = L + WEEKS * S + R
IMG_H = T + DAYS  * S + B
 
BG = (13, 17, 23)
 
LEVEL_COLORS = [
    (22,  27,  34),
    (14,  68,  41),
    (0,  109,  50),
    (38, 166,  65),
    (57, 211,  83),
]
 
# ── Sparkle trail ──────────────────────────────────────────────────────────────
SPARKLE_COLORS = [
    (255, 255, 180),  # warm yellow
    (255, 220, 255),  # soft pink
    (180, 230, 255),  # pale blue
    (255, 255, 255),  # white
    (220, 255, 220),  # mint
]
 
TRAIL_LEN = 35
 
def draw_sparkle(draw, x, y, size, color):
    draw.line([x, y-size, x, y+size], fill=color, width=1)
    draw.line([x-size, y, x+size, y], fill=color, width=1)
    d = max(1, size // 2)
    draw.line([x-d, y-d, x+d, y+d], fill=color, width=1)
    draw.line([x+d, y-d, x-d, y+d], fill=color, width=1)
 
def draw_sparkle_trail(draw, path, head_idx):
    start = max(0, head_idx - TRAIL_LEN)
    rng   = random.Random(42)
    for i in range(start, head_idx):
        col, day = path[i]
        cx, cy   = cell_center(col, day)
        t     = (i - start) / max(1, TRAIL_LEN)
        count = 1 if t < 0.4 else 2
        for _ in range(count):
            ox    = rng.randint(-4, 4)
            oy    = rng.randint(-4, 4)
            size  = max(1, int(t * 4))
            color = rng.choice(SPARKLE_COLORS)
            fade  = int(80 + t * 175)
            faded = tuple(min(255, int(c * fade / 255)) for c in color)
            draw_sparkle(draw, cx + ox, cy + oy, size, faded)
 
# ── Cat head ───────────────────────────────────────────────────────────────────
def draw_cute_cat(draw, col, day):
    cx = L + col * S + CELL // 2
    cy = T + day * S + CELL // 2
    R  = 11
 
    # Chubby cheeks tucked into face
    draw.ellipse([cx-R-2, cy+2, cx-R+8, cy+11], fill=(222, 212, 212))
    draw.ellipse([cx+R-8, cy+2, cx+R+2, cy+11], fill=(222, 212, 212))
 
    # Head
    draw.ellipse([cx-R, cy-R, cx+R, cy+R], fill=(215,215,215), outline=(0,0,0), width=1)
 
    # Ears
    draw.polygon([(cx-R+1, cy-R+3), (cx-R-1, cy-R-7), (cx-R+8, cy-R+1)],
                 fill=(215,215,215), outline=(0,0,0))
    draw.polygon([(cx+R-1, cy-R+3), (cx+R+1, cy-R-7), (cx+R-8, cy-R+1)],
                 fill=(215,215,215), outline=(0,0,0))
    draw.polygon([(cx-R+2, cy-R+2), (cx-R,   cy-R-4), (cx-R+6, cy-R+1)], fill=(255,160,185))
    draw.polygon([(cx+R-2, cy-R+2), (cx+R,   cy-R-4), (cx+R-6, cy-R+1)], fill=(255,160,185))
 
    # Eyes with shine
    draw.ellipse([cx-7, cy-5, cx-1, cy+2], fill=(30,30,30))
    draw.ellipse([cx+1, cy-5, cx+7, cy+2], fill=(30,30,30))
    draw.ellipse([cx-6, cy-4, cx-4, cy-2], fill=(255,255,255))
    draw.ellipse([cx+2, cy-4, cx+4, cy-2], fill=(255,255,255))
 
    # Blush
    draw.ellipse([cx-R+1, cy+3, cx-R+8, cy+8], fill=(255,175,192))
    draw.ellipse([cx+R-8, cy+3, cx+R-1, cy+8], fill=(255,175,192))
 
    # Nose
    draw.ellipse([cx-2, cy+2, cx+2, cy+5], fill=(255,110,145))
 
    # Mouth
    draw.line([cx-4, cy+7, cx-1, cy+5], fill=(80,80,80), width=1)
    draw.line([cx-1, cy+5, cx+1, cy+7], fill=(80,80,80), width=1)
    draw.line([cx+1, cy+7, cx+4, cy+5], fill=(80,80,80), width=1)
 
    # Whiskers
    draw.line([cx-R-5, cy+1, cx-R+3, cy+3], fill=(160,160,160), width=1)
    draw.line([cx-R-5, cy+5, cx-R+3, cy+5], fill=(160,160,160), width=1)
    draw.line([cx+R-3, cy+3, cx+R+5, cy+1], fill=(160,160,160), width=1)
    draw.line([cx+R-3, cy+5, cx+R+5, cy+5], fill=(160,160,160), width=1)
 
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
            wd = day["weekday"]
            row[wd] = 0 if c==0 else 1 if c<=3 else 2 if c<=6 else 3 if c<=9 else 4
        grid.append(row)
    while len(grid) < WEEKS:
        grid.append([0] * DAYS)
    return grid
 
# ── Snake path ─────────────────────────────────────────────────────────────────
def make_path() -> list:
    path = []
    for col in range(WEEKS):
        days = range(DAYS) if col % 2 == 0 else range(DAYS - 1, -1, -1)
        for day in days:
            path.append((col, day))
    return path
 
# ── Rendering helpers ──────────────────────────────────────────────────────────
def cell_topleft(col, day):
    return L + col * S, T + day * S
 
def cell_center(col, day):
    x, y = cell_topleft(col, day)
    return x + CELL // 2, y + CELL // 2
 
def draw_grid(draw, grid, eaten):
    for col in range(WEEKS):
        for day in range(DAYS):
            x, y  = cell_topleft(col, day)
            color = LEVEL_COLORS[0] if (col, day) in eaten else LEVEL_COLORS[grid[col][day]]
            draw.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=color)
 
def draw_stars(draw, seed):
    rng = random.Random(seed)
    for _ in range(20):
        sx = rng.randint(0, IMG_W - 1)
        sy = rng.randint(0, IMG_H - 1)
        br = rng.choice([100, 150, 200, 240])
        sz = rng.choice([1, 1, 2])
        draw.rectangle([sx, sy, sx+sz-1, sy+sz-1], fill=(br, br, br))
 
# ── GIF generation ─────────────────────────────────────────────────────────────
CELLS_PER_FRAME = 2
 
def generate_gif(grid: list, output_path: str):
    path   = make_path()
    frames = []
    eaten  = set()
 
    for i in range(0, len(path), CELLS_PER_FRAME):
        for j in range(CELLS_PER_FRAME):
            if i + j < len(path):
                eaten.add(path[i + j])
 
        head_idx           = min(i + CELLS_PER_FRAME - 1, len(path) - 1)
        head_col, head_day = path[head_idx]
 
        img  = Image.new("RGB", (IMG_W, IMG_H), BG)
        draw = ImageDraw.Draw(img)
 
        draw_stars(draw, (i // CELLS_PER_FRAME) % 10)
        draw_grid(draw, grid, eaten)
        draw_sparkle_trail(draw, path, head_idx)
        draw_cute_cat(draw, head_col, head_day)
 
        frames.append(img)
 
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    print(f"  Saving {len(frames)} frames → {output_path}")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=60,
        optimize=False,
    )
    print(f"  Done! ({os.path.getsize(output_path) // 1024} KB)")
 
# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Sparkle cat eats your GitHub contributions!")
    parser.add_argument("username")
    parser.add_argument("--token", "-t", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--output", "-o", default="nyan.gif")
    args = parser.parse_args()
 
    if not args.token:
        print("Error: set GITHUB_TOKEN or pass --token")
        sys.exit(1)
 
    print(f"Fetching contributions for @{args.username}...")
    grid = fetch_grid(args.username, args.token)
    filled = sum(grid[c][d] > 0 for c in range(WEEKS) for d in range(DAYS))
    print(f"  {filled} active cells found")
 
    print("Generating animation...")
    generate_gif(grid, args.output)
 
if __name__ == "__main__":
    main()
 
