"""Audit world->map room transforms: doors that miss their markers and room AOTs landing outside the room.

A door with no marker on the page (stairs, ladders, page links) is expected to miss, so a room is flagged only when
more doors miss than it has unmarked doors, or when under 70 % of its AOT points land inside its own floor shape.
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import fit

ROOT = Path(__file__).resolve().parents[1]


def audit():
    idx = fit.slots_index()
    xf = json.loads((ROOT / 'data/room_xform.json').read_text())
    names = {k: v['name_en'] for k, v in json.loads((ROOT / 'data/annotated.json').read_text())['rooms'].items()}
    out = []
    for (st, sl), (pg, r) in sorted(idx.items()):
        k = f'{st}-{sl:02X}'
        x = xf['rooms'][k]
        if x.get('o') is None:
            continue   # no doors to fit: drawn at the room anchor
        a, b, c, d = xf['orient'][x['o']]
        sx, sy = x.get('sx', x['s']), x.get('sy', x['s'])
        proj = lambda X, Z: (x['tx'] + sx * (a * X + b * Z), x['ty'] + sy * (c * X + d * Z))
        mask, pts, wd, cl = set(map(tuple, r['mask'])), fit.room_points(st, sl), fit.world_doors(st, sl), fit.clusters(r['doors'])
        inside = fit.contained([proj(*p) for p in pts], mask) / len(pts) if pts else 1.0
        ok = fit.allowed_markers(st, sl, idx, wd, cl) if cl else []
        miss = [round(min(math.hypot(proj(*w)[0] - q[0], proj(*w)[1] - q[1]) for q in ok[i]), 1) for i, w in enumerate(wd)] if cl else []
        tg = fit.door_targets(st, sl)
        onpage = [tg.get(w) in idx and idx[tg.get(w)][0] == pg for w in wd]   # stairs/ladders lead off the page: no marker
        miss = [e for e, on in zip(miss, onpage) if e > 2.5 and on]
        if miss or inside < 0.7:
            out.append((k, names.get(k), pg, x.get('fit'), f'{len(wd) - len(miss)}/{len(wd)} doors, {len(cl)} markers', round(inside, 2), miss))
    return out


if __name__ == '__main__':
    bad = audit()
    for row in bad:
        print(*row)
    print(len(bad), 'flagged')
