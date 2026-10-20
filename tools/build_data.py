"""Consolidate extracted + curated data into data/annotated.json (wiki and runtime source of truth).

Coordinates are map-TIM pixels of the page the marker is drawn on. Map stage = (RDT folder - 1) % 5
(folders 6/7 are the mansion revisit and share the mansion map pages and flags).
"""
import json, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import verify_items  # noqa: E402
D = ROOT / 'data'
rdt = json.loads((D / 'rdt.json').read_text())
maps = json.loads((D / 'map_rooms.json').read_text())
xf = json.loads((D / 'room_xform.json').read_text())
slot_names = json.loads((D / 'slot_names.json').read_text())
match = json.loads((D / 'room_match.json').read_text())
cur = json.loads((D / 'curated.json').read_text())
items = {int(k): v for k, v in json.loads((D / 'items.json').read_text()).items()}
for k, v in cur['item_names'].items():
    items[int(k)] = v
ORIENT = xf['orient']
CHARS = ('Chris', 'Jill')
COMMON = set(range(1, 19)) | {47, 65} | set(range(67, 76))
DOCS = set(range(78, 84)) | set(range(95, 129))


def category(item):
    if item in COMMON:
        return 'common'
    if item in DOCS:
        return 'document'
    return 'key'


# ---- map slots
slots = {}          # (stage, slot) -> dict(page, mask set, anchor)
for pg in maps['pages']:
    for r in pg['rooms']:
        slots[(pg['stage'], r['slot'])] = dict(page=pg['page'], mask={tuple(p) for p in r['mask']}, anchor=r['anchor'], bbox=r['bbox'])

slots_doors = {(pg['stage'], r['slot']): [tuple(p) for p in r['doors']] for pg in maps['pages'] for r in pg['rooms']}
page_of_slot = {(pg['stage'], r['slot']): pg['page'] for pg in maps['pages'] for r in pg['rooms']}
import os, struct
_ITEM_M2 = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn/Item_m2'
page_px = {}
for pg in maps['pages']:
    _t = (_ITEM_M2 / pg['file']).read_bytes()
    _at = 8 + struct.unpack_from('<I', _t, 8)[0]
    page_px[pg['page']] = _t[_at + 12:_at + 12 + 128 * 100]
all_room_px = {}   # page -> every room/door pixel (anything not here is wall or empty)
for pg in maps['pages']:
    for r in pg['rooms']:
        all_room_px.setdefault(pg['page'], set()).update(map(tuple, r['mask']), map(tuple, r['doors']))

# camera-dependent extra slots from exe 0x43ca60 (room -> extra slots it may light up)
EXTRA_SLOTS = {(0, 0x07): [(0, 0x1D)], (0, 0x0F): [(0, 0x1E)], (0, 0x10): [(1, 0x1E)], (0, 0x0C): [(0, 0x1F)],
               (1, 0x0F): [(1, 0x1D)], (2, 0x0B): [(2, 0x11)], (2, 0x0F): [(2, 0x12)], (4, 0x07): [(4, 0x16)]}


def slot_name(stage, slot):
    page = slots.get((stage, slot), {}).get('page')
    cands = slot_names.get(str(page), {}).get(str(slot)) if page is not None else None
    if cands:
        n = max(cands, key=lambda c: c['votes'])['name']
        return cur['slug_names'].get(n, n)
    m = match.get(f'{stage + 1}-{slot:02X}', {}).get('name')
    return cur['slug_names'].get(m, m) if m else None


def room_slots(stage, room):
    out = [(stage, room)] if (stage, room) in slots else []
    return out + [s for s in EXTRA_SLOTS.get((stage, room), []) if s in slots]


def project(stage, room, x, z):
    """World -> (stage, slot, px, py) snapped inside one of the room's slots."""
    cand = room_slots(stage, room)
    if not cand:
        return None
    rec = xf['rooms'].get(f'{stage}-{room:02X}')
    if rec and rec.get('o') is not None:
        a, b, c, d = ORIENT[rec['o']]
        s = rec['s']
        sx, sy = rec.get('sx', s), rec.get('sy', s)   # per-axis scale where the room is drawn stretched (fit.py bbox_fit)
        px, py = rec['tx'] + sx * (a * x + b * z), rec['ty'] + sy * (c * x + d * z)
        home = slots[(stage, room)]['page'] if (stage, room) in slots else None
        best = None
        for st in cand:
            sl = slots[st]
            if sl['page'] != home:
                continue
            q = min(sl['mask'], key=lambda m: (m[0] + .5 - px) ** 2 + (m[1] + .5 - py) ** 2)
            dist = math.hypot(q[0] + .5 - px, q[1] + .5 - py)
            inside = (int(px), int(py)) in sl['mask']
            key = (0 if inside else 1, dist)
            if not best or key < best[0]:
                best = (key, st, (px, py) if inside else (q[0] + .5, q[1] + .5))
        if best:
            return best[1][0], best[1][1], round(best[2][0], 1), round(best[2][1], 1)
    st = cand[0]
    a = slots[st]['anchor']
    return st[0], st[1], a[0] + .5, a[1] + .5


def door_clusters(stage, slot):
    """Connected yellow door-marker pixel groups drawn for one map slot."""
    if (stage, slot) not in slots_doors:
        return []
    left, out = set(slots_doors[(stage, slot)]), []
    while left:
        seed = left.pop(); group, stack = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in left:
                    left.remove(n); group.append(n); stack.append(n)
        out.append(group)
    return out


def door_geometry(pr, target):
    """Door marker nearest the projected door AOT. Both rooms draw their half of the marker, so the marker is grown over
    every room's door pixels on the page. A door is vertical when the wall touches the marker above/below (left/right ->
    horizontal); the key goes across the door on the side of the destination room (runtime: the unvisited room)."""
    stage, slot, px, py = pr
    page = page_of_slot[(stage, slot)]
    P = page_px[page]
    is_door = lambda x, y: 0 <= x < 128 and 0 <= y < 100 and P[y * 128 + x] >= 13 and (P[y * 128 + x] - 13) % 6 == 0
    is_wall = lambda x, y: 0 <= x < 128 and 0 <= y < 100 and P[y * 128 + x] == 7
    near = [(x, y) for x in range(int(px) - 4, int(px) + 5) for y in range(int(py) - 4, int(py) + 5) if is_door(x, y)]
    if not near:   # projection a few px off: nearest door marker this room draws
        near = slots_doors.get((stage, slot), [])
    if not near:
        return None
    seed = min(near, key=lambda q: (q[0] + .5 - px) ** 2 + (q[1] + .5 - py) ** 2)
    g, stack = {seed}, [seed]
    while stack:
        x, y = stack.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in g and is_door(*n):
                g.add(n); stack.append(n)
    xs, ys = [p[0] for p in g], [p[1] for p in g]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
    v = any(is_wall(x, y0 - 1) for x in range(x0, x1 + 1)) + any(is_wall(x, y1 + 1) for x in range(x0, x1 + 1))
    h = any(is_wall(x0 - 1, y) for y in range(y0, y1 + 1)) + any(is_wall(x1 + 1, y) for y in range(y0, y1 + 1))
    assert v != h, ('door orientation undecided', stage, slot, (x0, y0, x1, y1), v, h)
    horizontal = h > v
    tmask = set()
    for sl in room_slots(*target):
        tmask |= slots[sl]['mask']
    own = slots[(stage, slot)]['mask']
    best = None
    for dx, dy in (((0, -1), (0, 1)) if horizontal else ((-1, 0), (1, 0))):   # across the door only
        score = 0
        for k in range(1, 8):
            q = (int(cx - .5 + dx * k) if dx else int(cx), int(cy - .5 + dy * k) if dy else int(cy))
            score += 2 * (q in tmask) - (q in own)
        if best is None or score > best[0]:
            best = (score, dx, dy)
    return dict(cx=round(cx, 1), cy=round(cy, 1), horizontal=horizontal, dx=best[1], dy=best[2], toward_target=best[0] > 0,
                hw=round((x1 - x0 + 1) / 2, 1), hh=round((y1 - y0 + 1) / 2, 1))


def norm_room_key(v):
    return (v['stage'] - 1) % 5, v['room'], v['player']


def main():
    rooms = {}
    for (stage, slot), sl in sorted(slots.items()):
        en = slot_name(stage, slot)
        if not en:  # camera-split part of another room (exe 0x43ca60)
            parent = next(((st, rm) for (st, rm), ex in EXTRA_SLOTS.items() if (stage, slot) in ex), None)
            en = slot_name(*parent) if parent else None
        if en == 'Black Tiger Room':
            ko = '거미 방'
        else:
            ko = cur['room_ko'].get(en)
        rooms[f'{stage}-{slot:02X}'] = dict(stage=stage, slot=slot, page=sl['page'], name_en=en, name_ko=ko,
                                            anchor=sl['anchor'], bbox=sl['bbox'], pixels=len(sl['mask']),
                                            visited_bit=maps['stage_flag_base'][stage] + slot)
    # ---- items
    pick = {}
    for key, v in rdt.items():
        stage, room, player = norm_room_key(v)
        for x in v['records']:
            if x['op'] != 'item' or not x['item']:
                continue
            if (x['x'], x['z'], x['w'], x['h']) == (0, 0, 16, 16):
                continue   # Barry's hand-over in the main hall (Acid Rounds, Lockpick): not a pickup on the map
            k = (stage, x['flag'], x['item'])
            p = pick.setdefault(k, dict(item=x['item'], flag=x['flag'], stage=stage, room=room, chars=set(),
                                        positions=set(), folders=set(), guarded=False, amount=x['amount'], alts={}))
            # SCD guards of this placement (evaluated at runtime: shown if any record would place the item now)
            alt = [dict(negated=g['negated'], conds=[[c['group'], c['bit'], c['is_set']] for c in g['conds'] if c['kind'] == 'ck'],
                        exact=all(c['kind'] == 'ck' for c in g['conds'])) for g in x['guards']]
            if alt not in p['alts'].setdefault(player, []):
                p['alts'][player].append(alt)
            p['chars'].add(player)
            p['folders'].add(v['stage'])
            p['guarded'] |= bool(x['guards'])
            if x['w'] > 16 and x['h'] > 16:   # 0/1-sized AOTs are given by an examine event elsewhere in the room
                p['positions'].add((x['x'] + x['w'] / 2, x['z'] + x['h'] / 2))
    # pickups given by an event script (no item_aot_set), e.g. the 2F map in the fireplace frame
    for e in cur.get('event_items', []):
        pick[(e['stage'], e['flag'], e['item'])] = dict(item=e['item'], flag=e['flag'], stage=e['stage'], room=e['room'],
                                                       chars=set(e['chars']), positions={(e['x'], e['z'])},
                                                       folders=set(e['folders']), guarded=True, amount=1,
                                                       alts={c: [e['guards']] for c in e['chars']})
    out_items = []
    er_contents, er_by_name = verify_items.load_pages()
    for (stage, flag, item), p in sorted(pick.items()):
        pos = sorted(p['positions'])
        if pos:
            wx, wz = sum(q[0] for q in pos) / len(pos), sum(q[1] for q in pos) / len(pos)
            pr = project(stage, p['room'], wx, wz)
            exact = True
        else:
            pr = None
            cand = room_slots(stage, p['room'])
            if cand:
                a = slots[cand[0]]['anchor']
                pr = (cand[0][0], cand[0][1], a[0] + .5, a[1] + .5)
            exact = False
        name = items.get(item, {})
        # evilresource pages for this RDT room: content/adjacency match + every map slot's highlight name
        er_pages = {match[f'{f if f < 6 else f - 5}-{p["room"]:02X}']['page'] for f in p['folders']
                    if f'{f if f < 6 else f - 5}-{p["room"]:02X}' in match and match[f'{f if f < 6 else f - 5}-{p["room"]:02X}']['page']}
        for sl in room_slots(stage, p['room']):
            er_pages |= er_by_name.get(rooms.get(f'{sl[0]}-{sl[1]:02X}', {}).get('name_en'), set())
        evidence = {CHARS[c]: verify_items.verdict(name.get('en') or '', c, er_pages, er_contents) for c in sorted(p['chars'])}
        out_items.append(dict(item=item, name_en=name.get('en') or f'Item {item}', name_ko=name.get('ko') or name.get('en') or f'아이템 {item}',
                              category=category(item), flag=flag, stage=stage, room=p['room'],
                              chars=sorted(p['chars']), folders=sorted(p['folders']), event_guarded=p['guarded'],
                              exact_position=exact, amount=p['amount'],
                              evidence={c: dict(status=v[0], page=v[1], desc=v[2]) for c, v in evidence.items()},
                              guards={str(c): a for c, a in p.get('alts', {}).items()},
                              map=dict(zip(('stage', 'slot', 'px', 'py'), pr)) if pr else None))
    # show only verified pickups, per character; the rest stays in the wiki audit
    excluded = []
    for it in out_items:
        shown = [c for c in it['chars'] if it['evidence'][CHARS[c]]['status'] == 'pickup']
        if shown != it['chars']:
            excluded.append(dict(it, hidden_chars=[c for c in it['chars'] if c not in shown]))
        it['chars'] = shown
    out_items = [it for it in out_items if it['chars']]
    # ---- locks
    locks = {}
    for key, v in rdt.items():
        stage, room, player = norm_room_key(v)
        for x in v['records']:
            if x['op'] != 'door' or not (x['lock_flag'] & 0x80) or x['key'] in (0, 254, 255):
                continue
            bit = x['lock_flag'] & 0x3f
            L = locks.setdefault(bit, dict(bit=bit, key=x['key'], sides={}, chars=set()))
            L['chars'].add(player)
            side = (stage, room)
            L['sides'].setdefault(side, dict(stage=stage, room=room, target=((x['target_stage'] - 1) % 5 if x['target_stage'] else stage, x['target_room']),
                                             pos=(x['x'] + x['w'] / 2, x['z'] + x['d'] / 2)))
    out_locks = []
    for bit, L in sorted(locks.items()):
        sides = []
        for (stage, room), sd in sorted(L['sides'].items()):
            pr = project(stage, room, *sd['pos'])
            sides.append(dict(stage=stage, room=room, target=f'{sd["target"][0]}-{sd["target"][1]:02X}',
                              map=dict(zip(('stage', 'slot', 'px', 'py'), pr)) if pr else None,
                              door=door_geometry(pr, sd['target']) if pr else None))
        key = L['key']
        out_locks.append(dict(bit=bit, key=key, key_en=items.get(key, {}).get('en'), key_ko=items.get(key, {}).get('ko'),
                              jill_lockpick=key == 51, chars=sorted(L['chars']), sides=sides))
    # ---- save points
    saves = {}
    for key, v in rdt.items():
        stage, room, player = norm_room_key(v)
        for x in v['records']:
            if x['op'] == 'aot' and x['sce'] in ('typewriter', 'itembox') and x['w']:
                k = (x['sce'], stage, room)
                saves.setdefault(k, set()).add((x['x'] + x['w'] / 2, x['z'] + x['h'] / 2))
    out_saves = []
    for (kind, stage, room), pts in sorted(saves.items()):
        wx, wz = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        pr = project(stage, room, wx, wz)
        if pr:
            out_saves.append(dict(kind=kind, stage=stage, room=room, map=dict(zip(('stage', 'slot', 'px', 'py'), pr))))
    # ---- puzzles
    out_puz = []
    for pz in cur['puzzles']:
        stage, room = (int(t, 16) for t in pz['room'].split('-'))
        # 'at' = the world point of the AOT that triggers the puzzle (curated, with its RDT source); else the room anchor
        cand = room_slots(stage, room)
        if pz.get('place'):   # evilresource direction inside the drawn room, where the AOT/fit disagrees
            sl = (stage, pz.get('slot', room)); m = slots[sl]['mask']
            x0, y0, x1, y1 = slots[sl]['bbox']
            tx, ty = {'center': ((x0 + x1) / 2, (y0 + y1) / 2), 'sw': (x0, y1), 'e': (x1, (y0 + y1) / 2)}[pz['place']]
            if pz['place'] != 'center':
                tx, ty = min(m, key=lambda q: (q[0] + .5 - tx) ** 2 + (q[1] + .5 - ty) ** 2)
                tx, ty = tx + .5, ty + .5
            pr = (sl[0], sl[1], round(tx + (.5 if pz['place'] == 'center' else 0), 1), round(ty + (.5 if pz['place'] == 'center' else 0), 1))
        elif pz.get('at'):
            pr = project(stage, room, *pz['at'])
        elif cand and 'heliport' not in pz['source']:
            pr = (cand[0][0], cand[0][1], slots[cand[0]]['anchor'][0] + .5, slots[cand[0]]['anchor'][1] + .5)
        else:
            pr = None
        out_puz.append(dict(stage=stage, room=room, items=pz['items'], chars=pz.get('chars', [0, 1]), note=pz['note'],
                            source=pz['source'], guide=pz.get('guide', False), name_en=pz['name_en'], name_ko=pz['name_ko'], solved_when=pz.get('solved_when', []), solved_source=pz.get('solved_source', ''),
                            items_en=[items[i]['en'] for i in pz['items']], items_ko=[items[i]['ko'] for i in pz['items']],
                            map=dict(zip(('stage', 'slot', 'px', 'py'), pr)) if pr else None))
    pages = [dict(page=p['page'], file=p['file'], stage=p['stage']) for p in maps['pages']]
    result = dict(
        native=dict(map_state=0xB38DE0, page_stage=maps['page_stage'], area_pages=maps['area_pages'],
                    stage_flag_base=maps['stage_flag_base'], visited_flags=0xC387A0, pickup_flags=0xC3876C,
                    door_flags=0xC38744, stage_no=0xC386F0, room_no=0xC386F1),
        pages=pages, rooms=rooms, items=out_items, items_excluded=excluded, locks=out_locks, saves=out_saves, puzzles=out_puz)
    (D / 'annotated.json').write_text(json.dumps(result, indent=1, ensure_ascii=False))
    cats = defaultdict(int)
    for i in out_items:
        cats[i['category']] += 1
    print('rooms', len(rooms), 'items', dict(cats), 'locks', len(out_locks), 'saves', len(out_saves), 'puzzles', len(out_puz))
    print('excluded', len(excluded), sorted({(e['name_en'], e['evidence'][CHARS[c]]['status']) for e in excluded for c in e['hidden_chars']}))
    print('unnamed slots', [k for k, r in rooms.items() if not r['name_en']])
    print('no-ko', sorted({r['name_en'] for r in rooms.values() if r['name_en'] and not r['name_ko']}))


if __name__ == '__main__':
    main()
