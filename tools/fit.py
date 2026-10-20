"""Fit world (x,z) -> map TIM pixel transforms per room.

The RE1 map has no native world->map projection, so each room's transform is fitted from its own
door AOT centres against the yellow door-marker clusters drawn for that room slot in the map TIM:
    px = tx + s*(a*x + b*z),  py = ty + s*(c*x + d*z)    with (a,b,c,d) one of 8 axis orientations.
Output data/room_xform.json keyed "<mapstage>-<room>" (mapstage 0..4) -> {page, slot, s, o, tx, ty, err, n}.
"""
import itertools, json, math, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
maps = json.loads((ROOT / 'data/map_rooms.json').read_text())
rdt = json.loads((ROOT / 'data/rdt.json').read_text())
ORIENT = [(1, 0, 0, -1), (-1, 0, 0, 1), (1, 0, 0, 1), (-1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0), (0, 1, -1, 0), (0, -1, 1, 0)]
ROTATIONS = (0, 1, 4, 5)
# camera-split extra slots (exe 0x43ca60): the room's AOTs may land in these too
EXTRA = {(0, 0x07): [(0, 0x1D)], (0, 0x0F): [(0, 0x1E)], (0, 0x10): [(1, 0x1E)], (0, 0x0C): [(0, 0x1F)],
         (1, 0x0F): [(1, 0x1D)], (2, 0x0B): [(2, 0x11)], (2, 0x0F): [(2, 0x12)], (4, 0x07): [(4, 0x16)]}  # proper rotations of (x, -z); 2,3,6,7 would be mirror images


def clusters(points):
    left, out = set(map(tuple, points)), []
    while left:
        seed = left.pop()
        group, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for n in [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]:
                if n in left:
                    left.remove(n)
                    group.append(n)
                    stack.append(n)
        out.append((sum(p[0] for p in group) / len(group) + 0.5, sum(p[1] for p in group) / len(group) + 0.5))
    return out


def slots_index():
    idx = {}
    for pg in maps['pages']:
        for r in pg['rooms']:
            idx[(pg['stage'], r['slot'])] = (pg['page'], r)
    return idx


def world_doors(stage, room):
    pts = set()
    for key, v in rdt.items():
        if (v['stage'] - 1) % 5 == stage and v['room'] == room:
            for x in v['records']:
                if x['op'] == 'door' and x['w'] and x['d']:
                    pts.add((x['x'] + x['w'] / 2, x['z'] + x['d'] / 2))
    return sorted(pts)


def room_points(stage, room):
    """Centres of the room's interaction AOTs (items, events, messages, doors): they lie inside or on the room."""
    pts = set()
    for v in rdt.values():
        if (v['stage'] - 1) % 5 == stage and v['room'] == room:
            for x in v['records']:
                w, h = x.get('w'), x.get('h', x.get('d'))
                if x['op'] in ('aot', 'item', 'door') and w and h and 16 < w < 6000 and 16 < h < 6000:
                    pts.add((x['x'] + w / 2, x['z'] + h / 2))
    return sorted(pts)


def contained(proj, mask, tol=2.0):
    return sum(any(abs(m[0] + .5 - px) <= tol and abs(m[1] + .5 - py) <= tol for m in mask) for px, py in proj)


def fit_room(wd, cl, s, orients=(0,), tol=2.5, pts=(), mask=(), allow=None):
    """Translation maximising door inliers (within tol px of a marker cluster) plus AOT containment in the room."""
    best = None
    for o in orients:
        a, b, c, d = ORIENT[o]
        proj = [(s * (a * x + b * z), s * (c * x + d * z)) for x, z in wd]
        ok = allow or [cl] * len(proj)
        for (px, py), (cx, cy) in ((p, q) for i, p in enumerate(proj) for q in ok[i]):
            tx, ty = cx - px, cy - py
            near = [(min(ok[j], key=lambda k: math.hypot(qx + tx - k[0], qy + ty - k[1])), (qx, qy)) for j, (qx, qy) in enumerate(proj)]
            inl = [(k, q) for k, q in near if math.hypot(q[0] + tx - k[0], q[1] + ty - k[1]) <= tol]
            if inl:
                tx = sum(k[0] - q[0] for k, q in inl) / len(inl)
                ty = sum(k[1] - q[1] for k, q in inl) / len(inl)
            e = sum(math.hypot(q[0] + tx - k[0], q[1] + ty - k[1]) for k, q in inl) / max(1, len(inl))
            # one matched door fixes translation but not which marker/rotation: the room's own AOTs must land in it
            inside = contained([(tx + s * (a * x + b * z), ty + s * (c * x + d * z)) for x, z in pts], mask) / len(pts) if pts else 0
            key = (-round(len(inl) + 2 * inside, 2), round(e, 2), o != 0)   # ties (2-door rooms are 180-degree ambiguous) keep the common orientation
            if not best or key < best[0]:
                best = (key, o, tx, ty)
    (neg, e, _), o, tx, ty = best
    a, b, c, d = ORIENT[o]
    proj = [(s * (a * x + b * z), s * (c * x + d * z)) for x, z in wd]
    ok = allow or [cl] * len(proj)
    inl = sum(min(math.hypot(qx + tx - k[0], qy + ty - k[1]) for k in ok[j]) <= tol for j, (qx, qy) in enumerate(proj))
    return e, o, tx, ty, inl


def stretch_fit(wd, cl, s, o, tol=2.5, pts=(), mask=(), allow=None):
    """Schematic rooms drawn stretched along one axis: per-axis scale from two matched doors (0.5..2.5x page scale)."""
    a, b, c, d = ORIENT[o]
    uv = [(a * x + b * z, c * x + d * z) for x, z in wd]
    best = None
    ok = allow or [cl] * len(uv)
    for i, j in itertools.permutations(range(len(uv)), 2):
        for ki, kj in itertools.product(ok[i], ok[j]):
            if ki == kj:
                continue
            sc = []
            for ax in (0, 1):
                du, dm = uv[j][ax] - uv[i][ax], kj[ax] - ki[ax]
                sc.append(dm / du if abs(du) >= 300 and abs(dm) >= 2 else s)   # markers in line on this axis: keep page scale
            if not all(0.5 * s <= k <= 2.5 * s for k in sc):
                continue
            tx, ty = ki[0] - sc[0] * uv[i][0], ki[1] - sc[1] * uv[i][1]
            proj = [(tx + sc[0] * u, ty + sc[1] * v) for u, v in uv]
            ds = [min(math.hypot(px - k[0], py - k[1]) for k in ok[n]) for n, (px, py) in enumerate(proj)]
            inl = sum(e <= tol for e in ds)
            inside = contained([(tx + sc[0] * (a * x + b * z), ty + sc[1] * (c * x + d * z)) for x, z in pts], mask) / len(pts) if pts else 0
            key = (-inl, -round(inside, 2), round(sum(e for e in ds if e <= tol) / max(1, inl), 2))
            if not best or key < best[0]:
                best = (key, sc[0], sc[1], tx, ty, inl)
    return best


def bbox_fit(pts, bbox, o, mask):
    """Per-axis scale mapping the room's AOT extent (rotated by o) onto its drawn bounding box."""
    a, b, c, d = ORIENT[o]
    us, vs = [a * x + b * z for x, z in pts], [c * x + d * z for x, z in pts]
    if max(us) - min(us) < 500 or max(vs) - min(vs) < 500:
        return None
    x0, y0, x1, y1 = bbox
    sx, sy = (x1 - x0) / (max(us) - min(us)), (y1 - y0) / (max(vs) - min(vs))
    tx, ty = x0 + .5 - sx * min(us), y0 + .5 - sy * min(vs)
    inside = contained([(tx + sx * u, ty + sy * v) for u, v in zip(us, vs)], mask) / len(pts)
    return inside, round(sx, 6), round(sy, 6), round(tx, 2), round(ty, 2)


def door_targets(stage, room):
    out = {}
    for v in rdt.values():
        if (v['stage'] - 1) % 5 == stage and v['room'] == room:
            for x in v['records']:
                if x['op'] == 'door' and x['w'] and x['d']:
                    ts = (x['target_stage'] - 1) % 5 if x['target_stage'] else stage
                    out[(x['x'] + x['w'] / 2, x['z'] + x['d'] / 2)] = (ts, x['target_room'])
    return out


def allowed_markers(stage, slot, idx, wd, cl):
    """Per door: the markers on the edge it shares with its target room (or, for off-page targets, markers touching
    no other room). A door may only match those, so a 2-door corridor cannot fit rotated 180 degrees (4-01)."""
    page = idx[(stage, slot)][0]
    touch = lambda q, key: key in idx and idx[key][0] == page and any(
        abs(a + .5 - q[0]) <= 2 and abs(b + .5 - q[1]) <= 2 for a, b in idx[key][1]['mask'])
    others = [k for k, (pg, _) in idx.items() if pg == page and k != (stage, slot)]
    tg = door_targets(stage, slot)
    out = []
    for w in wd:
        t = tg.get(w)
        if t in idx and idx[t][0] == page:
            ok = [q for q in cl if touch(q, t)]
        else:
            ok = [q for q in cl if not any(touch(q, k) for k in others)]
        out.append(ok or cl)
    return out


def main():
    idx = slots_index()
    # scale per page: maximise door inliers over that page's multi-door rooms, then minimise error
    page_scale = {}
    for page in range(len(maps['pages'])):
        cands = [(world_doors(st, sl), clusters(r['doors'])) for (st, sl), (pg, r) in idx.items() if pg == page]
        cands = [(wd, cl) for wd, cl in cands if len(wd) >= 2 and cl]
        def score(k):
            fits = [fit_room(wd, cl, k / 100000, ROTATIONS) for wd, cl in cands]
            return (-sum(f[4] for f in fits), sum(f[0] for f in fits))
        page_scale[page] = min(range(95, 125), key=score) / 100000 if cands else None
    known = [v for v in page_scale.values() if v]
    for page in page_scale:
        page_scale[page] = page_scale[page] or sorted(known)[len(known) // 2]
    print('page scales', page_scale)
    out = {}
    for (stage, slot), (page, r) in sorted(idx.items()):
        wd, cl = world_doors(stage, slot), clusters(r['doors'])
        best_s = page_scale[page]
        rec = dict(page=page, slot=slot, s=best_s, n=len(wd))
        if wd and cl:
            mask = set(map(tuple, r['mask'])) | {tuple(m) for e in EXTRA.get((stage, slot), []) if e in idx for m in idx[e][1]['mask']}
            allow = allowed_markers(stage, slot, idx, wd, cl)
            e, o, tx, ty, inl = fit_room(wd, cl, best_s, ROTATIONS, pts=room_points(stage, slot), mask=mask, allow=allow)
            rec.update(o=o, tx=round(tx, 2), ty=round(ty, 2), err=round(e, 2), inliers=inl)
            pts = room_points(stage, slot)
            st = stretch_fit(wd, cl, best_s, o, pts=pts, mask=mask, allow=allow) if len(wd) >= 2 and len(cl) >= 2 and inl < len(wd) else None
            a, b, c, d = ORIENT[o]
            was_in = contained([(tx + best_s * (a * x + b * z), ty + best_s * (c * x + d * z)) for x, z in pts], mask) / len(pts) if pts else 0
            now_in = st and (contained([(st[3] + st[1] * (a * x + b * z), st[4] + st[2] * (c * x + d * z)) for x, z in pts], mask) / len(pts) if pts else 0)
            if st and st[5] > inl and now_in >= was_in:   # e.g. guardhouse central corridor: 1/3 doors at page scale, 3/3 stretched
                rec.update(sx=round(st[1], 6), sy=round(st[2], 6), tx=round(st[3], 2), ty=round(st[4], 2), fit='stretch', inliers=st[5])
            elif pts and (stage, slot) not in EXTRA:
                a, b, c, d = ORIENT[o]
                door_in = contained([(tx + best_s * (a * x + b * z), ty + best_s * (c * x + d * z)) for x, z in pts], mask) / len(pts)
                box = bbox_fit(pts, r['bbox'], o, mask)
                # the map is schematic: when the room is drawn narrower/wider than its world size, stretch to its box
                doors_ok = box and all(min(math.hypot(box[3] + box[1] * (a * x + b * z) - q[0], box[4] + box[2] * (c * x + d * z) - q[1])
                                           for q in cl) <= 3 for x, z in wd)
                if box and doors_ok and box[0] >= door_in + 0.2:   # and its doors still sit on the yellow markers
                    rec.update(sx=box[1], sy=box[2], tx=box[3], ty=box[4], fit='bbox', contained=round(box[0], 2), door_contained=round(door_in, 2))
        else:
            rec.update(o=None, err=None)
        out[f'{stage}-{slot:02X}'] = rec
        print(f'{stage}-{slot:02X} page {page} doors {len(wd)}/{len(cl)} orient {rec.get("o")} inl {rec.get("inliers")} err {rec.get("err")}')
    assert out['3-05']['inliers'] == 3 and out['4-01']['inliers'] == 2, (out['3-05'], out['4-01'])   # stretched corridor; 4-01 must not fit rotated 180 deg
    (ROOT / 'data/room_xform.json').write_text(json.dumps(dict(orient=ORIENT, rooms=out), indent=1))


if __name__ == '__main__':
    main()
