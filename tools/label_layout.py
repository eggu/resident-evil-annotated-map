"""Room-name placement, ported from the RE2 map mod (diagnostics/key-map-names-20261014/generate_room_names.py).

Rule (RE2): tightest rooms first; a name stays inside its room when its box sits on the room's own shape
(>= 90 % coverage, tried with 2 px / 1 px / no wall margin), as close to the room centroid as possible and
clear of names already placed. Names that do not fit get a two-line retry by the caller, then go outside the
floor shapes with the shortest axis-aligned leader line starting on an edge pixel of the room.
All coordinates are PSX cells of the target view (status map 1x, fullscreen 2x).
"""
FIT = 0.9
SMALL = 0.8


def hit(a, b):
    return a[0] < b[0] + b[2] + 1 and b[0] < a[0] + a[2] + 1 and a[1] < b[1] + b[3] + 1 and b[1] < a[1] + a[3] + 1


def erode(cells):
    return {c for c in cells if all((c[0] + i, c[1] + j) in cells for i in (-1, 0, 1) for j in (-1, 0, 1))}


def _sat(cells, x0, y0, w, h):
    s = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        row = 0
        for x in range(w):
            row += (x0 + x, y0 + y) in cells
            s[y + 1][x + 1] = s[y][x + 1] + row
    return s


def _box(s, x, y, bw, bh):
    h, w = len(s) - 1, len(s[0]) - 1
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + bw, w), min(y + bh, h)
    return 0 if x1 <= x0 or y1 <= y0 else s[y1][x1] - s[y0][x1] - s[y1][x0] + s[y0][x0]


def fit_inside(cells, lw, lh, placed):
    """Best label box (x, y, w, h) on the room's own cells, else None."""
    if not cells:
        return None
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    s = _sat(cells, x0, y0, w, h)
    for scale, need in ((1.0, FIT), (SMALL, 1.0)):
        bw, bh = max(1, round(lw * scale)), max(1, round(lh * scale))
        best = None
        for by in range(-bh // 2, h - bh // 2):
            for bx in range(-bw // 2, w - bw // 2):
                if _box(s, bx, by, bw, bh) < need * bw * bh:
                    continue
                px, py = x0 + bx + bw // 2, y0 + by + bh // 2           # label centre
                if (px, py) not in cells:
                    continue
                box = (px - lw // 2, py - lh // 2, lw, lh)
                if any(hit(box, b) for b in placed):
                    continue
                score = (px - cx) ** 2 + (py - cy) ** 2
                if best is None or score < best[0]:
                    best = (score, box)
        if best:
            return best[1]
    return None


def leader(cells, occ, blocked, lw, lh, placed, lines, bounds, walls=frozenset(), kmax=40, pad=0):
    """Shortest axis-aligned leader from an edge cell of the room to a label box in free space (the line itself is not checked)."""
    best = None
    bx0, by0, bx1, by1 = bounds
    cx = (min(c[0] for c in cells) + max(c[0] for c in cells)) / 2
    for (sx, sy) in cells:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if (sx + dx, sy + dy) in cells:
                continue
            for k in range(1, kmax):
                if best and k >= best[0]:
                    break
                ex, ey = sx + dx * k, sy + dy * k
                if occ.get((ex, ey), walls) is not walls and occ[(ex, ey)] is not cells:
                    break   # the leader may cross walls but not another room
                for sh in (0, 3, -3, 6, -6, 9, -9):
                    if (dy and abs(sh) > lw // 2 - 2) or (dx and abs(sh) > lh // 2 - 1):
                        continue
                    if dy:
                        box = (ex - lw // 2 + sh, ey - lh + 1 if dy < 0 else ey, lw, lh)
                    else:
                        box = (ex - lw + 1 if dx < 0 else ex, ey - lh // 2 + sh, lw, lh)
                    if box[0] < bx0 or box[1] < by0 or box[0] + lw > bx1 or box[1] + lh > by1:
                        continue
                    # pad: free margin kept around the name (roomy spots first)
                    if any((x, y) in blocked for y in range(box[1] - pad, box[1] + lh + pad) for x in range(box[0] - pad, box[0] + lw + pad)):
                        continue
                    if any(hit((box[0] - pad, box[1] - pad, lw + 2 * pad, lh + 2 * pad), b) for b in placed):
                        continue
                    # the leader line itself ignores collisions (may run under names, icons and other lines): a room ringed
                    # by neighbouring names (1F Tiger Statue Room) still gets its name outside
                    align = abs(sx - cx) if dy else 0
                    cost = k + abs(sh) * 0.1 + align * 0.05
                    if best is None or cost < best[0]:
                        best = (cost, box, (sx, sy, ex, ey))
    return best


def place_rooms(rooms, walls, bounds, obstacles=()):
    """rooms: [dict(key, cells:set, lw, lh)] -> {key: (box, line|None)} or None for 'needs wrap / failed'."""
    occ = {}
    for r in rooms:
        for c in r['cells']:
            occ[c] = r['cells']
    for c in walls:
        occ.setdefault(c, walls)
    blocked = {(x + i, y + j) for x, y in occ for j in (-1, 0, 1) for i in (-1, 0, 1)}
    rooms_only = {c for c, owner in occ.items() if owner is not walls}
    placed, lines, out = list(obstacles), [], {}   # item/puzzle names and icons were placed first
    for r in sorted(rooms, key=lambda r: len(r['cells'])):           # tightest rooms choose first
        for cells in (erode(erode(r['cells'])), erode(r['cells']), r['cells']):
            box = fit_inside(cells, r['lw'], r['lh'], placed)
            if box:
                out[r['key']] = (box, None)
                placed.append(box)
                break
    for r in sorted(rooms, key=lambda r: min(c[1] for c in r['cells'])):
        if r['key'] in out:
            continue
        # passes: free space off the floor; crowded map: over wall lines, never another room or name; a ringed room:
        # the line may cross other rooms but the name still sits off every floor; last resort: anywhere clear of other
        # names and icons (may cover other rooms' floor). Within each, a roomy spot (2-cell margin) wins over a tight
        # one, even if its leader line is longer.
        best = None
        for occ_, blk, km in ((occ, blocked, 40), (occ, rooms_only, 40), ({}, blocked, 60), ({}, rooms_only, 60), ({}, set(), 60)):
            for pad in (2, 1, 0):
                best = leader(r['cells'], occ_, blk, r['lw'], r['lh'], placed, lines, bounds, walls, kmax=km, pad=pad)
                if best:
                    break
            if best:
                break
        if best:
            out[r['key']] = (best[1], best[2])
            placed.append(best[1])
            lines.append(best[2])
        else:
            out[r['key']] = None
    return out, placed, lines


if __name__ == '__main__':
    # one runnable check: a wide room keeps its name inside; a 2x2 closet gets a leader line to free space
    big = {(x, y) for x in range(0, 30) for y in range(0, 10)}
    tiny = {(x, y) for x in range(40, 42) for y in range(4, 6)}
    res, _, _ = place_rooms([dict(key='big', cells=big, lw=12, lh=4), dict(key='tiny', cells=tiny, lw=10, lh=4)], set(), (0, 0, 80, 40))
    (bx, by, bw, bh), line = res['big']
    assert line is None and all((x, y) in big for x in range(bx, bx + bw) for y in range(by, by + bh)), res['big']
    box, line = res['tiny']
    assert line and (line[0], line[1]) in tiny and not any(hit(box, (x, y, 0, 0)) for x, y in tiny), res['tiny']
    print('label_layout ok', res)
