"""Per-room shapes from the game's own map TIMs (Item_m2/MAP01..MAP0B).

Native layout (Biohazard.exe 0x43bfb0): page p loads PAGE_FILES[p], belongs to map stage
PAGE_STAGE[p]; room slot k owns CLUT entries 13+6k .. 18+6k (+0 door marker, +1/+2 detail,
+3/+4 fill, +5 black). Output data/map_rooms.json.
"""
import json, os, struct, sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).parent.parent
ITEM_M2 = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn/Item_m2'
PAGE_STAGE = [0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4]          # exe 0x4b1bf8
STAGE_ROOMS = [32, 31, 19, 18, 24]                      # exe 0x4b1bd0
STAGE_FLAG_BASE = [0, 32, 63, 82, 100]                  # exe 0x4b1bc8 (Flg_7 visited bits)
AREA_PAGES = [[2, 0, 1], [4, 3], [6, 5], [10, 9, 8, 7]]  # exe 0x4b1bd8, area*4+floor (top floor first)
PAGE_FILES = ['MAP01', 'MAP02', 'MAP03', 'MAP04', 'MAP05', 'MAP0A', 'MAP0B', 'MAP06', 'MAP07', 'MAP08', 'MAP09']  # exe string table 0x4b1a38 + page*0x24


def load_page(p):
    d = (ITEM_M2 / f'{PAGE_FILES[p]}.TIM').read_bytes()
    clen = struct.unpack_from('<I', d, 8)[0]
    q = 8 + clen
    blen, x, y, w, h = struct.unpack_from('<IHHHH', d, q)
    return w * 2, h, d[q + 12:q + blen]


def inscribed_point(pts):
    """Pixel farthest (4-neighbour BFS) from the outside of the region; ties -> nearest centroid."""
    s = set(pts)
    dist, dq = {}, deque()
    for (x, y) in pts:
        if any((x + dx, y + dy) not in s for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            dist[(x, y)] = 1
            dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in s and n not in dist:
                dist[n] = dist[(x, y)] + 1
                dq.append(n)
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    best = max(pts, key=lambda q: (dist[q], -((q[0] - cx) ** 2 + (q[1] - cy) ** 2)))
    return best, dist[best]


def main():
    pages = []
    for p in range(11):
        w, h, px = load_page(p)
        stage = PAGE_STAGE[p]
        rooms = []
        for k in range(STAGE_ROOMS[stage]):
            lo = 13 + 6 * k
            pts = [(i % w, i // w) for i, c in enumerate(px) if lo <= c <= lo + 5]
            if not pts:
                continue
            doors = [(i % w, i // w) for i, c in enumerate(px) if c == lo]
            (ax, ay), depth = inscribed_point(pts)
            xs, ys = [x for x, _ in pts], [y for _, y in pts]
            rooms.append(dict(slot=k, pixels=len(pts), bbox=[min(xs), min(ys), max(xs), max(ys)],
                              anchor=[ax, ay], depth=depth, doors=doors,
                              rows=sorted(set(ys)), mask=[[x, y] for x, y in pts]))
        pages.append(dict(page=p, file=PAGE_FILES[p] + '.TIM', stage=stage, size=[w, h], rooms=rooms))
    (ROOT / 'data/map_rooms.json').write_text(json.dumps(dict(
        page_stage=PAGE_STAGE, stage_rooms=STAGE_ROOMS, stage_flag_base=STAGE_FLAG_BASE, area_pages=AREA_PAGES,
        pages=pages), separators=(',', ':')))
    for pg in pages:
        print(pg['page'], pg['file'], 'stage', pg['stage'], 'slots', [r['slot'] for r in pg['rooms']])


if __name__ == '__main__':
    main()
