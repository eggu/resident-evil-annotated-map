"""data/annotated.json -> src/overlay_data.h (4bpp label/icon bitmaps, markers with offline label layout).

All overlay geometry is in hi-res texels: S texels per PSX pixel. The runtime composes these bitmaps
into 256x256 4bpp TIM tiles and draws them as native sprites with UVs scaled by S.
"""
import json, os, struct, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
S = 8   # texels per PSX pixel (REbirth wraps sprite UVs at 256, so overlay textures stay 256 = 32 PSX px; S=16 needed 512 and broke, 2026-10-20)
TILE = 32 * S   # overlay tile texture size (32 PSX pixels per tile)
FONT = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
FACE, OUTLINE = 2, S // 4   # Medium face, 1-texel outline: Bold + 2-texel outline was blurry at map resolution
d = json.loads((ROOT / 'data/annotated.json').read_text())

# palette index -> RGB (0 = transparent)
# Nonzero RGB keeps the panel opaque in the native renderer (RGB zero is color-keyed).
PALETTE = [None, (9, 9, 9), (255, 240, 210), (60, 220, 255), (240, 240, 240), (255, 205, 70), (255, 150, 30),
           (175, 175, 175), (95, 95, 95), (150, 100, 40), (220, 60, 50), (60, 220, 70), (80, 140, 255),
           (20, 100, 130), (140, 100, 20), (255, 255, 255)]
BLACK, CREAM, CYAN, WHITE, GOLD, AMBER, GREY, DGREY, BRASS, RED, GREEN, BLUE, DCYAN, DGOLD, PURE = range(1, 16)
KIND = dict(room=1, save=1, lock=2, key=3, document=4, puzzle=5, common=6)
FLAG_NONE, FLAG_PICKUP, FLAG_DOOR, FLAG_SOLVED = 0, 1, 2, 3
conds = []   # solved conditions: (ck group, bit, required state), terminated by group 255
guard_rows = []   # placement guards: (group, bit, flags) flags: 1 is_set, 2 negated, 4 new guard, 8 new alternative; group 255 ends
def guard_index(alts):
    if not alts or any(not alt for alt in alts):   # an unguarded record: always placed
        return 0xFFFF
    start = len(guard_rows)
    for alt in alts:
        first_alt = True
        for g in alt:
            conds = g['conds'] if g['exact'] else []   # partly unknown guard (cmpb, item checks...): treated as passing
            for k, (grp, bit, is_set) in enumerate(conds or [[254, 0, 0]]):
                guard_rows.append((grp, bit, is_set | (2 if g['negated'] else 0) | (4 if k == 0 else 0) | (8 if first_alt and k == 0 else 0)))
                first_alt = False
    guard_rows.append((255, 0, 0))
    return start


bitmaps = []    # (w, h, bytes 1 px/byte)


def add_bitmap(img):
    w, h = img.size
    bitmaps.append((w, h, img.tobytes()))
    return len(bitmaps) - 1


def text_bitmap(text, size, color, face=None, left=False):
    if '\n' in text:   # two-line room name (RE2 retry), lines centred; titles left-aligned
        parts = [text_bitmap(t, size, color, face) for t in text.split('\n')]
        w, h = max(p.width for p in parts), sum(p.height for p in parts) - 2
        out = Image.new('L', (w, h))
        y = 0
        for part in parts:
            out.paste(part, (0 if left else (w - part.width) // 2, y), part.point(lambda v: 255 if v else 0))
            y += part.height - 2
        return out
    font = ImageFont.truetype(*(face or (FONT, )), size, **({} if face else dict(index=FACE)))
    l, t, r, b = font.getbbox(text, stroke_width=OUTLINE)
    w, h = r - l + 2, b - t + 2
    fill = Image.new('L', (w, h))
    edge = Image.new('L', (w, h))
    ImageDraw.Draw(edge).text((1 - l, 1 - t), text, font=font, fill=255, stroke_width=OUTLINE, stroke_fill=255)
    ImageDraw.Draw(fill).text((1 - l, 1 - t), text, font=font, fill=255)
    out = Image.new('L', (w, h))
    out.paste(BLACK, mask=edge.point(lambda v: 255 if v >= 96 else 0))
    out.paste(color, mask=fill.point(lambda v: 255 if v >= 100 else 0))
    return out


def icon(pattern, scale=S):
    """ASCII pixel art (one char per PSX-ish pixel cell of size `scale`) -> bitmap."""
    cmap = {'.': 0, 'k': BLACK, 'c': CYAN, 'w': WHITE, 'g': GOLD, 'a': AMBER, 'y': GREY, 'd': DGREY, 'b': BRASS,
            'r': RED, 'n': GREEN, 'u': BLUE, 'e': DCYAN, 'o': DGOLD, 'p': PURE, 'm': CREAM}
    rows = [r for r in pattern.strip().split('\n')]
    w, h = len(rows[0]), len(rows)
    img = Image.new('L', (w * scale // 2, h * scale // 2))
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            for dy in range(scale // 2):
                for dx in range(scale // 2):
                    px[x * scale // 2 + dx, y * scale // 2 + dy] = cmap[ch]
    return img


# icons are drawn on a half-PSX-pixel grid (each char = 2x2 texels at S=4)
ICONS = {
    'key': icon("""
.kkkk.....
kggggk....
kgkkgkkkkk
kggggggggk
.kkkkkgkgk
.....kkkkk"""),
    'dot': icon("""
.kkkk.
kcccck
kcccck
kcccck
kcccck
.kkkk."""),
    'doc': icon("""
kkkkkk.
kwwwwkk
kwkkwwk
kwwwwwk
kwkkkwk
kwwwwwk
kkkkkkk"""),
    'puzzle': icon("""
...kk...
..kaak..
.kaaaak.
kaaaaaak
.kaaaak.
..kaak..
...kk..."""),
    'typewriter': icon("""
.kkkkkk.
.kmmmmk.
kkkkkkkk
kddddddk
kdydydyk
kkkkkkkk"""),
    'itembox': icon("""
kkkkkkkk
kbbbbbbk
kkkkkkkk
kbbogbbk
kbbbbbbk
kkkkkkkk"""),
    'ammo': icon("""
.kk.kk.
kgkkgk.
kgkkgk.
kbkkbk.
kbkkbk.
kkkkkk."""),
    'shell': icon("""
kkkkk
krrrk
krrrk
kgggk
kkkkk"""),
    'herb_g': icon("""
.kkkk.
knnnnk
knnnnk
.knnk.
..kk.."""),
    'herb_r': icon("""
.kkkk.
krrrrk
krrrrk
.knnk.
..kk.."""),
    'herb_b': icon("""
.kkkk.
kuuuuk
kuuuuk
.knnk.
..kk.."""),
    'spray': icon("""
.kkk.
kpppk
kwrwk
kwwwk
kwwwk
kkkkk"""),
    'ribbon': icon("""
..kkk..
.kdddk.
kdwwwdk
kdwkwdk
kdwwwdk
.kdddk.
..kkk.."""),
    'weapon': icon("""
kkkkkkk.
kyyyyyyk
kkkkdkk.
...kdk..
...kkk.."""),
    'map': icon("""
kkkkkkk
knnwnnk
knwwwnk
kwwnwwk
kkkkkkk"""),
}
ICON_ID = {k: add_bitmap(v) for k, v in ICONS.items()}


def common_icon(item):
    if 1 <= item <= 10:
        return 'weapon'
    if item in (11, 13, 14):
        return 'ammo'
    if 12 <= item <= 18:
        return 'shell'
    if item == 47:
        return 'ribbon'
    if item == 65:
        return 'spray'
    if item == 67:
        return 'herb_r'
    if item == 69:
        return 'herb_b'
    return 'herb_g'


label_cache = {}


def label(text, size, color, face=None, left=False):
    k = (text, size, color, face, left)
    if k not in label_cache:
        label_cache[k] = add_bitmap(text_bitmap(text, size, color, face, left))
    return label_cache[k]


ROOM_SIZE, ITEM_SIZE, LEGEND_SIZE = 15 * S // 4, 13 * S // 4, 13 * S // 4   # sizes designed at S=4
markers = []  # dict(kind, page, stage, slot, x, y, icon, en, ko, flagtype, flag, chars)


def page_of(m):
    return d['rooms'][f"{m['stage']}-{m['slot']:02X}"]['page']


# camera-split slots repeat their room's name: label only the largest slot of each name per page
label_slot = {}
for k, r in d['rooms'].items():
    best = label_slot.get((r['page'], r['name_en']))
    if not best or r['pixels'] > d['rooms'][best]['pixels']:
        label_slot[(r['page'], r['name_en'])] = k
for k, r in d['rooms'].items():
    if r['name_ko'] and label_slot[(r['page'], r['name_en'])] == k:
        markers.append(dict(kind=KIND['room'], page=r['page'], stage=r['stage'], slot=r['slot'], x=(r['anchor'][0] + .5) * S,
                            y=(r['anchor'][1] + .5) * S, icon=-1, en=label(r['name_en'], ROOM_SIZE, CREAM),
                            ko=label(r['name_ko'], ROOM_SIZE, CREAM), flagtype=FLAG_NONE, flag=0, chars=3, centre=True,
                            text=dict(en=r['name_en'], ko=r['name_ko'])))
for s in d['saves']:
    m = s['map']
    markers.append(dict(kind=KIND['save'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID['typewriter' if s['kind'] == 'typewriter' else 'itembox'], en=-1, ko=-1,
                        flagtype=FLAG_NONE, flag=0, chars=3))
for L in d['locks']:
    seen_doors = []   # both rooms record the same door (and each draws its own marker): one key per physical door
    for sd in L['sides']:
        m = sd['map']
        if not m:
            continue
        dr0 = sd.get('door')
        if dr0:
            pg = page_of(m)
            if any(p == pg and abs(x - dr0['cx']) <= 2.5 and abs(y - dr0['cy']) <= 2.5 for p, x, y in seen_doors):
                continue
            seen_doors.append((pg, dr0['cx'], dr0['cy']))
        chars = 0
        for c in L['chars']:
            chars |= 1 << c
        if L['jill_lockpick']:   # Chris: Sword Key; Jill: Lockpick (exe 0x455b9f)
            variants = [(1, L['key_en'], L['key_ko']), (2, 'Lockpick', '락픽')]
        else:
            variants = [(chars, L['key_en'], L['key_ko'])]
        door = sd.get('door')
        tst, tslot = (int(t, 16) for t in sd['target'].split('-'))
        for ch, en, ko in variants:
            # RE1 HD map mod rule (gen_labels.key_sides / re1_mapnames.c): the key sits off the door along its normal, on the
            # side of the room not visited yet (else the destination). Horizontal door: icon + name side by side, above/below;
            # vertical door: icon over name, left/right. Both sides are generated; the runtime picks one.
            for side in ((1, 2) if door else (0,)):
                markers.append(dict(kind=KIND['lock'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                                    icon=ICON_ID['key'], en=label(en, ITEM_SIZE, GOLD), ko=label(ko, ITEM_SIZE, GOLD),
                                    flagtype=FLAG_DOOR, flag=L['bit'], chars=ch, door=door, side=side, target=(tst, tslot)))
for i in d['items']:
    m = i['map']
    if not m:
        continue
    chars = sum(1 << c for c in i['chars'])
    cat = i['category']
    guard = [guard_index(i['guards'].get(str(c))) for c in (0, 1)]
    if cat == 'common':
        markers.append(dict(kind=KIND['common'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                            icon=ICON_ID[common_icon(i['item'])], en=-1, ko=-1, flagtype=FLAG_PICKUP, flag=i['flag'], chars=chars, guard=guard))
    else:
        col, ic = (CYAN, 'dot') if cat == 'key' else (WHITE, 'map' if 78 <= i['item'] <= 83 else 'doc')
        markers.append(dict(kind=KIND[cat], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                            icon=ICON_ID[ic], en=label(i['name_en'], ITEM_SIZE, col), ko=label(i['name_ko'], ITEM_SIZE, col),
                            flagtype=FLAG_PICKUP, flag=i['flag'], chars=chars, guard=guard))
for p in d['puzzles']:
    m = p['map']
    if not m:
        continue
    markers.append(dict(kind=KIND['puzzle'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID['puzzle'], en=label(p['name_en'], ITEM_SIZE, AMBER), ko=label(p['name_ko'], ITEM_SIZE, AMBER),
                        flagtype=FLAG_SOLVED if p['solved_when'] else FLAG_NONE, flag=len(conds), chars=sum(1 << c for c in p['chars'])))
    conds.extend(p['solved_when'] + [[255, 0, 0]] if p['solved_when'] else [])   # puzzle hidden once every condition holds


# ---- label layout: RE2 room-name rule (tools/label_layout.py), separately per view and language
import runpy as _rp
LL = _rp.run_path(str(ROOT / 'tools/label_layout.py'))
ITEM_M2 = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn/Item_m2'
MAP_PX = []
for page in d['pages']:
    tim = (ITEM_M2 / page['file']).read_bytes()
    at = 8 + struct.unpack_from('<I', tim, 8)[0]
    MAP_PX.append(tim[at + 12:at + 12 + 128 * 100])
SLOT_MASK = {(pg['stage'], r['slot']): [tuple(m) for m in r['mask']]
             for pg in json.loads((ROOT / 'data/map_rooms.json').read_text())['pages'] for r in pg['rooms']}
def anchor_part(key, ax, ay):
    """The connected piece of a room's map cells that holds its anchor: a name never goes to a detached stray piece
    (3-02 Room 001 Bathroom also owns a wall-less block below the save room in MAP0A.TIM)."""
    left, parts = set(SLOT_MASK[key]), []
    while left:
        seed = left.pop(); part, stack = {seed}, [seed]
        while stack:
            x, y = stack.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in left:
                    left.remove(n); part.add(n); stack.append(n)
        parts.append(part)
    return min(parts, key=lambda q: min((x - ax) ** 2 + (y - ay) ** 2 for x, y in q))


FULL_TOP, FULL_BOTTOM = 10, 204            # fullscreen map area (PSX); RE2-style title top-left, legend bottom-left


def full_origin(page):
    """Fullscreen 2x map origin (PSX): page content centred in the map area, with a top margin."""
    pts = [(i % 128, i // 128) for i, v in enumerate(MAP_PX[page]) if v == 7 or v >= 13]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    return (320 - 2 * (x1 - x0 + 1)) // 2 - 2 * x0, FULL_TOP + (FULL_BOTTOM - FULL_TOP - 2 * (y1 - y0 + 1)) // 2 - 2 * y0


ORIGIN = [full_origin(p) for p in range(len(d['pages']))]
VIEWS = (dict(z=1, bounds=(-14, -3, 142, 99), size=13 * S // 4), dict(z=2, bounds=(2, FULL_TOP - 2, 318, FULL_BOTTOM + 2), size=ROOM_SIZE))


def wrap(text, size):
    words = text.split()
    parts, join = (words, ' '.join) if len(words) > 1 else (list(text), ''.join)
    if len(parts) < 2:
        return None
    font = ImageFont.truetype(FONT, size, index=FACE)
    n = min(range(1, len(parts)), key=lambda n: abs(font.getlength(join(parts[:n])) - font.getlength(join(parts[n:]))))
    return join(parts[:n]) + '\n' + join(parts[n:])


def cells_of(view, page, pts):
    z, (ox, oy) = view['z'], ((0, 0) if view['z'] == 1 else ORIGIN[page])
    return {(ox + x * z + i, oy + y * z + j) for x, y in pts for i in range(z) for j in range(z)}


def to_tex(view, page, x, y):
    """1x map texel coords -> view texel coords (status: map-relative, fullscreen: screen-absolute)."""
    if view['z'] == 1:
        return x, y
    ox, oy = ORIGIN[page]
    return ox * S + 2 * x, oy * S + 2 * y


def layout_view(vi, lang):
    view, stats = VIEWS[vi], dict(inside=0, leader=0, wrapped=0, failed=0)
    for page in range(len(d['pages'])):
        ms = [m for m in markers if m['page'] == page]
        walls = cells_of(view, page, [(i % 128, i // 128) for i, v in enumerate(MAP_PX[page]) if v == 7])
        # icons at their exact spot, then item / puzzle / lock names next to them (they have priority);
        # room names come last and move off them, or go outside with a leader line
        boxes = []
        for m in sorted(ms, key=lambda m: bool(m.get('door'))):   # fixed icons first: lock keys then step around them
            if m['icon'] >= 0:
                iw, ih = bitmaps[m['icon']][:2]
                cx, cy = to_tex(view, page, m['x'], m['y'])
                dr = m.get('door')
                if dr:
                    sgn = 1 if m['side'] == 1 else -1                       # 1: destination side, 2: the door's own room
                    dx, dy = dr['dx'] * sgn, dr['dy'] * sgn
                    dcx, dcy = to_tex(view, page, dr['cx'] * S, dr['cy'] * S)
                    # clear the door: status map draws the whole native marker, fullscreen a 2-px bar on the wall line
                    half, gap = (S if vi == 1 else (dr['hw'] if dx else dr['hh']) * S), S // 2
                    lw_, lh_ = bitmaps[m[lang]][:2] if vi == 1 and m[lang] >= 0 else (0, 0)
                    g = 1 if lw_ else 0
                    # key next to the door (same spot in both languages), name continuing away from the door, upright:
                    #   vertical door   |door| (key) [name]      (mirrored on the left side)
                    #   horizontal door  door / (key) / [name]   (stacked; mirrored above)
                    other = {id(o) for o in ms if o.get('door') is dr and o['side'] != m['side']}   # never on screen together
                    def place(gap, nudge=0):
                        if dx:
                            ix = dcx + dx * (half + gap) + (0 if dx > 0 else -iw)
                            iy = dcy - ih / 2
                            lx, ly = (ix + iw + g if dx > 0 else ix - g - lw_), iy + (ih - lh_) / 2 + nudge
                        else:
                            ix = dcx - iw / 2
                            iy = dcy + dy * (half + gap) + (0 if dy > 0 else -ih)
                            lx, ly = ix + (iw - lw_) / 2 + nudge, (iy + ih + g if dy > 0 else iy - g - lh_)
                        own = [(ix + iw * .15, iy + ih * .15, ix + iw * .85, iy + ih * .85)] + ([(lx, ly, lx + lw_, ly + lh_)] if lw_ else [])
                        over = sum(max(0, min(o[2], q[2]) - max(o[0], q[0])) * max(0, min(o[3], q[3]) - max(o[1], q[1]))
                                   for o in own for q in boxes if q[4] & m['chars'] and q[5] not in other)
                        return over, ix, iy, lx, ly
                    # ponytail: slide key + name away from the door (up to 3 px) until clear; layout order is unchanged
                    # still blocked (an icon right in the name's row): nudge only the name across the row, at most one icon size
                    span = ih if dx else iw
                    nudges = [0] + [v for n in range(S // 2, span + 1, S // 2) for v in (-n, n)]
                    over, ix, iy, lx, ly = min((place(gap + k * S // 2, n) + (abs(n) + k,) for k in range(7) for n in nudges),
                                               key=lambda t: (t[0] > 0, t[0], t[5]))[:5]
                    cx, cy = ix + iw / 2, iy + ih / 2
                    if lw_:
                        m.setdefault('lab', {})[(vi, lang)] = (m[lang], round(lx), round(ly))
                        boxes.append((round(lx) - 2, round(ly) - 2, round(lx) + lw_ + 2, round(ly) + lh_ + 2, m['chars'], id(m)))
                m.setdefault('ico', {})[vi] = (round(cx - iw / 2), round(cy - ih / 2))
                # names may cover up to half an icon: only its central 70 % x 70 % (~49 % of the area) is an obstacle
                boxes.append((round(cx - iw * .35), round(cy - ih * .35), round(cx + iw * .35), round(cy + ih * .35), m['chars'], id(m)))
        bx0, by0, bx1, by1 = (v * S for v in view['bounds'])
        for m in ms:
            if m.get('centre') or m[lang] < 0 or (m.get('door') and vi == 1):   # lock names were placed with their key
                continue
            if vi == 0:   # status screen shows room names only
                m.setdefault('lab', {})[(vi, lang)] = (m[lang], 0, 0)
                continue
            w, h = bitmaps[m[lang]][:2]
            cx, cy = to_tex(view, page, m['x'], m['y'])
            ih = bitmaps[m['icon']][1] if m['icon'] >= 0 else 0
            iw = bitmaps[m['icon']][0] if m['icon'] >= 0 else 0
            # marker-name gap = 40 % of the original (3 / 4 texels at S=4 incl. the bitmap's 1-texel padding)
            gv, gh = 0, 0   # touching boxes; the bitmap's 1-texel padding is the only gap
            cands = [(cx - w / 2, cy - ih / 2 - h - gv), (cx - w / 2, cy + ih / 2 + gv), (cx + iw / 2 + gh, cy - h / 2), (cx - iw / 2 - gh - w, cy - h / 2)]
            best = None
            for n in (0, 2, 4, 8, 12):
                for ci, (lx, ly) in enumerate(cands):
                    pref = 0
                    for dx, dy in ((0, 0), (0, -n), (0, n), (n, 0), (-n, 0)):
                        x = round(max(bx0, min(lx + dx * S, bx1 - w))); y = round(max(by0, min(ly + dy * S, by1 - h)))
                        box = (x - 2, y - 2, x + w + 2, y + h + 2)
                        over = sum(max(0, min(box[2], b[2]) - max(box[0], b[0])) * max(0, min(box[3], b[3]) - max(box[1], b[1]))
                                   for b in boxes if b[4] & m['chars'] and b[5] != id(m))   # not against its own icon
                        key = (over, pref, (x + w / 2 - cx) ** 2 + (y + h / 2 - cy) ** 2)
                        if not best or key < best[0]:
                            best = (key, x, y)
                if best and best[0][0] == 0:
                    break
            _, x, y = best
            m.setdefault('lab', {})[(vi, lang)] = (m[lang], x, y)
            boxes.append((x - 2, y - 2, x + w + 2, y + h + 2, m['chars'], id(m)))
        # item names, icons and lock keys are obstacles for room names (PSX cells)
        obstacles = [(b[0] // S, b[1] // S, max(1, -(-b[2] // S) - b[0] // S), max(1, -(-b[3] // S) - b[1] // S)) for b in boxes]
        rooms = [m for m in ms if m.get('centre')] if vi == 1 else []   # status screen shows icons only
        bid = {id(m): label(m['text'][lang], view['size'], CREAM) for m in rooms}
        def run():
            spec = [dict(key=id(m), cells=cells_of(view, page, anchor_part((m['stage'], m['slot']), int(m['x'] // S), int(m['y'] // S))),
                         lw=-(-bitmaps[bid[id(m)]][0] // S), lh=-(-bitmaps[bid[id(m)]][1] // S)) for m in rooms]
            return LL['place_rooms'](spec, walls, view['bounds'], obstacles)
        res, placed, lines = run() if rooms else ({}, [], [])
        retry = [m for m in rooms if res[id(m)] is None or res[id(m)][1]]
        for m in retry:
            t = wrap(m['text'][lang], view['size'])
            if t:
                bid[id(m)] = label(t, view['size'], CREAM)
        if retry and rooms:
            res, placed, lines = run()
        for m in rooms:
            w, h = bitmaps[bid[id(m)]][:2]
            r = res[id(m)]
            if r is None:   # nowhere free: centre on the room anchor
                cx, cy = to_tex(view, page, m['x'], m['y'])
                m.setdefault('lab', {})[(vi, lang)] = (bid[id(m)], round(cx - w / 2), round(cy - h / 2))
                stats['failed'] += 1
                continue
            (bx, by, bw, bh), line = r
            m.setdefault('lab', {})[(vi, lang)] = (bid[id(m)], bx * S + (bw * S - w) // 2, by * S + (bh * S - h) // 2)
            stats['leader' if line else 'inside'] += 1
            stats['wrapped'] += '\n' in [k for k, v in label_cache.items() if v == bid[id(m)]][0][0]
            if line:
                m.setdefault('lines', {})[(vi, lang)] = tuple(v * S + S // 2 for v in line)
    print('layout', ('status', 'fullscreen')[vi], lang, stats)


for vi in range(2):
    for lang in ('en', 'ko'):
        layout_view(vi, lang)


# ---- legends
# status screen: compact, 2 rows x 5 columns inside the map panel below the floor drawing
# short forms: all ten keys share one line on the status screen
LEGEND = [('Annotated Map', '주석 지도'), ('0 All', '0 전체'), ('1 Rooms', '1 방'),
          ('2 Locks', '2 문'), ('3 Keys', '3 주요템'), ('4 Files', '4 문서'),
          ('5 Puzzles', '5 퍼즐'), ('6 Items', '6 일반템'), ('8 Visited', '8 방문'),
          ('8 All', '8 전체 방'), ('9 KO', '9 EN'), ('7 Zoom', '7 확대'), ('7 Back', '7 원래'), ('M Close', 'M 닫기'),
          ('8 Revealed', '8 공개')]
LEG_COLORS = [CREAM, PURE, CREAM, GOLD, CYAN, WHITE, AMBER, GREY, PURE, PURE, PURE, PURE, PURE, PURE, PURE]
# one line of 10 entries inside the map panel (box x 32..137 PSX = 105 wide), each advancing by its width + gap
STATUS_GAP = 1   # PSX
def _status_fits(size, lang):
    tot = 0
    for rows in ((1,), (2,), (3,), (4,), (5,), (6,), (7,), (11, 12), (8, 9, 14), (10,)):
        tot += max(text_bitmap(LEGEND[r][lang], size, PURE).width for r in rows) / S + STATUS_GAP
    return tot - STATUS_GAP <= 105
# largest font per language that keeps the line inside the panel (Korean labels are shorter, so they get bigger)
STATUS_LEGEND_SIZE = [next(sz for sz in range(16 * S // 4, 5 * S // 4, -1) if _status_fits(sz, lang)) for lang in (0, 1)]
print('status legend font en/ko', [z / S for z in STATUS_LEGEND_SIZE])
STATUS_LEGEND_COL = 0
legend = []
en_sz, ko_sz = STATUS_LEGEND_SIZE
for (en, ko), col in zip(LEGEND, LEG_COLORS):
    legend.append((label(en, en_sz, col), label(ko, ko_sz, col),
                   label(en, en_sz, DGREY), label(ko, ko_sz, DGREY)))
# fullscreen: RE2 "DISPLAY STATUS" block, rows [0]..[9] with their state as text
FULL_LEGEND_SIZE = 14 * S // 4   # ~18 screen px at 1600x1200, like RE2
ON, OFF = (': ON', ': 켬'), (': OFF', ': 끔')
FULL_ROWS = [  # (variants (en, ko), colour when on)
    ([('[0] ALL', '[0] 전체')], PURE), ([('[1] ROOMS', '[1] 방·저장')], CREAM), ([('[2] LOCKS', '[2] 문·열쇠')], GOLD),
    ([('[3] KEY ITEMS', '[3] 주요템')], CYAN), ([('[4] FILES & MAPS', '[4] 문서·지도')], WHITE), ([('[5] PUZZLES', '[5] 퍼즐')], AMBER),
    ([('[6] ITEMS', '[6] 일반템')], GREY),
    ([('[7] VIEW: LARGE', '[7] 보기: 크게'), ('[7] VIEW: SMALL', '[7] 보기: 작게'), ('[M] CLOSE MAP', '[M] 지도 닫기')], PURE),
    ([('[8] SCOPE: VISITED', '[8] 범위: 방문한 방'), ('[8] SCOPE: REVEALED', '[8] 범위: 공개된 방'), ('[8] SCOPE: ALL ROOMS', '[8] 범위: 모든 방')], PURE),
    ([('[9] LANGUAGE: ENGLISH', '[9] 언어: 한국어')], PURE)]
full_legend = []   # [row][variant][on/off][lang]
for k, (variants, col) in enumerate(FULL_ROWS):
    rows = []
    for en, ko in variants + [variants[-1]] * (3 - len(variants)):
        if k <= 6:
            rows.append(((label(en + ON[0], FULL_LEGEND_SIZE, col), label(ko + ON[1], FULL_LEGEND_SIZE, col)),
                         (label(en + OFF[0], FULL_LEGEND_SIZE, DGREY), label(ko + OFF[1], FULL_LEGEND_SIZE, DGREY))))
        else:
            rows.append(((label(en, FULL_LEGEND_SIZE, col), label(ko, FULL_LEGEND_SIZE, col)),) * 2)
    full_legend.append(rows)
full_legend_title = (label('DISPLAY STATUS', FULL_LEGEND_SIZE, PURE), label('표시 상태', FULL_LEGEND_SIZE, PURE))
# RE2-style area title: large serif, two lines, top-left
TITLE_EN, TITLE_KO = ('/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf',), ('/System/Library/Fonts/Supplemental/AppleMyungjo.ttf',)
TITLE_SIZE = 40 * S // 4
# navigation arrows (floor up/down, area left/right) and the player arrow (16 headings)
def triangle(w, h, pts, fill=GREEN):
    im = Image.new('L', (w, h)); dr = ImageDraw.Draw(im)
    dr.polygon(pts, fill=BLACK); inset = [(x + (w / 2 - x) * 0.18, y + (h / 2 - y) * 0.18) for x, y in pts]
    dr.polygon(inset, fill=fill); return im
NW, NH = 12 * S, 9 * S
nav = [add_bitmap(triangle(NW, NH, [(NW / 2, 0), (NW - 1, NH - 1), (0, NH - 1)])),                                         # up
       add_bitmap(triangle(NW, NH, [(0, 0), (NW - 1, 0), (NW / 2, NH - 1)])),                                                  # down
       add_bitmap(triangle(NH, NW, [(NH - 1, 0), (NH - 1, NW - 1), (0, NW / 2)])),                                             # left
       add_bitmap(triangle(NH, NW, [(0, 0), (0, NW - 1), (NH - 1, NW / 2)]))]                                                  # right
import math
AR = 8 * S   # texels per atlas cell (8 PSX)
arrow_atlas = Image.new('L', (4 * AR, 4 * AR))
for k in range(16):   # heading k * 22.5 deg clockwise from screen-up
    a = math.radians(k * 22.5); c = AR / 2
    pts = [(x * AR / 64, y * AR / 64) for x, y in ((0, -26), (17, 22), (0, 12), (-17, 22))]
    rot = [(c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
    cell = Image.new('L', (AR, AR)); dr = ImageDraw.Draw(cell)
    dr.polygon(rot, fill=BLACK)
    dr.polygon([(c + (x - c) * 0.72, c + (y - c) * 0.72) for x, y in rot], fill=GREEN)
    arrow_atlas.paste(cell, ((k % 4) * AR, (k // 4) * AR))


def rgb555(c):
    if c is None:
        return 0
    r, g, b = (v * 31 // 255 for v in c)
    return 0x8000 | (b << 10) | (g << 5) | r


assert rgb555(PALETTE[BLACK]) & 0x7fff, 'Background must not use native RGB-zero color key'

out = ['/* Generated by tools/gen_assets.py from data/annotated.json. Do not edit. */', f'#define OV_SCALE {S}',
       f'static const unsigned short ov_palette[16]={{{",".join(str(rgb555(c)) for c in PALETTE)}}};']
page_names = [('Mansion 1F', '저택 1층'), ('Mansion 2F', '저택 2층'), ('Mansion B1', '저택 지하'),
              ('Courtyard', '정원'), ('Caves', '지하 동굴'), ('Guardhouse 1F', '기숙사 1층'), ('Guardhouse B1', '기숙사 지하'),
              ('Laboratory B1', '연구소 B1'), ('Laboratory B2', '연구소 B2'), ('Laboratory B3', '연구소 B3'), ('Laboratory B4', '연구소 B4')]
page_titles = [(label(en.upper().replace(' ', '\n', 1), TITLE_SIZE, WHITE, TITLE_EN, True), label(ko.replace(' ', '\n', 1), TITLE_SIZE, WHITE, TITLE_KO, True))
               for en, ko in page_names]
out.append('static const short ov_page_titles[11][2]={' + ','.join('{%d,%d}' % pair for pair in page_titles) + '};')
out.append('static const short ov_full_legend[10][3][2][2]={' + ','.join('{' + ','.join('{' + ','.join('{%d,%d}' % st for st in v) + '}' for v in row) + '}' for row in full_legend) + '};')
out.append('static const short ov_full_legend_title[2]={%d,%d};' % full_legend_title)
_w = lambda rows: max(bitmaps[b][0] for r in rows for v in r for st in v for b in st)
col2 = -(-_w(full_legend[:5]) // S) + 6
right = 8 + col2 + -(-_w(full_legend[5:]) // S)
out.append(f'#define OV_FULL_LEGEND_COL2 {col2}')
out.append(f'#define OV_FULL_LEGEND_RIGHT {right}')
out.append(f'#define OV_STATUS_LEGEND_GAP {STATUS_GAP}')
print('fullscreen legend col2', col2, 'right edge', right)
# player position: world (x, z) of the current room -> map TIM pixels (tools/fit.py; exe has no projection)
_xf = json.loads((ROOT / 'data/room_xform.json').read_text())
xrows = []
for st in range(5):
    for rm in range(32):
        r = _xf['rooms'].get(f'{st}-{rm:02X}')
        room = d['rooms'].get(f'{st}-{rm:02X}')
        if not room:
            xrows.append('{0}'); continue
        ax, ay = room['anchor']
        if r and r.get('o') is not None:
            sx, sy = r.get('sx', r['s']), r.get('sy', r['s'])
            xrows.append('{1,%d,%d,%d,%d,%d,%d,%d,%d}' % (r['o'], room['page'], round(r['tx'] * 256), round(r['ty'] * 256),
                                                        round(sx * (1 << 24)), round(sy * (1 << 24)), ax, ay))
        else:
            xrows.append('{2,0,%d,0,0,0,0,%d,%d}' % (room['page'], ax, ay))   # no fit: room anchor
out.append('typedef struct { signed char kind, o; unsigned char page; int tx256, ty256, sx24, sy24; short ax, ay; } OvXform;')
out.append('static const OvXform ov_xform[5][32]={' + ','.join('{' + ','.join(xrows[st * 32:st * 32 + 32]) + '}' for st in range(5)) + '};')
out.append('static const signed char ov_orient[8][4]={' + ','.join('{%d,%d,%d,%d}' % tuple(o) for o in _xf['orient']) + '};')
out.append('static const short ov_nav[4]={%d,%d,%d,%d};' % tuple(nav))
_ap = arrow_atlas.tobytes()
out.append('#define OV_ARROW_CELL %d' % (AR // S))
out.append(f'#define OV_TILE_TEX {TILE}')
out.append(f'static const unsigned char ov_arrow_pixels[{TILE * TILE // 2}]={{' + ','.join(str(_ap[i] | (_ap[i + 1] << 4)) for i in range(0, len(_ap), 2)) + '};')
# Original map geometry only; runtime applies the existing visited/current-room flags.
item_m2 = ITEM_M2
# Preserve the original blue grid palette separately from annotation colors.
import runpy
load_tim = runpy.run_path(str(ROOT / 'tools/tim.py'))['load']
blue, _ = load_tim(item_m2 / 'Map_blue.tim')
blue = blue.convert('RGB')
# Repeat the original 8x8 cell in logical pixels; never resize the background.
background_palette = list(PALETTE)
background_colors = sorted(set(blue.crop((0, 0, 8, 8)).get_flattened_data()))
background_indices = {color: i + 2 for i, color in enumerate(background_colors)}
for color, i in background_indices.items(): background_palette[i] = color
px = bytes(background_indices[blue.getpixel((x % 8, y % 8))] for y in range(256) for x in range(256))
packed = bytes(px[i] | (px[i+1] << 4) for i in range(0, len(px), 2))
out.append('static const unsigned short ov_background_palette[16]={' + ','.join(str(rgb555(c)) for c in background_palette) + '};')
out.append('static const unsigned char ov_background_pixels[32768]={' + ','.join(map(str, packed)) + '};')
map_pixels = []
for page in d['pages']:
    tim = (item_m2 / page['file']).read_bytes()
    assert struct.unpack_from('<II', tim) == (16, 9)
    at = 8 + struct.unpack_from('<I', tim, 8)[0]
    length, _, _, words, height = struct.unpack_from('<IHHHH', tim, at)
    assert words * 2 == 128 and height >= 100 and length >= 12 + 128 * 100
    map_pixels.append(tim[at + 12:at + 12 + 128 * 100])
out.append('static const unsigned char ov_map_pixels[11][12800]={' + ','.join('{' + ','.join(map(str, px)) + '}' for px in map_pixels) + '};')
blob, offs = bytearray(), []
for w, h, px in bitmaps:
    offs.append(len(blob))
    row = (w + 1) // 2
    for y in range(h):
        for x in range(0, w, 2):
            a = px[y * w + x]
            b = px[y * w + x + 1] if x + 1 < w else 0
            blob.append(a | (b << 4))
out.append(f'#define OV_BITMAP_COUNT {len(bitmaps)}')
out.append('typedef struct { unsigned short w,h; unsigned off; } OvBitmap;')
out.append('static const OvBitmap ov_bitmaps[]={' + ','.join(f'{{{w},{h},{o}}}' for (w, h, _), o in zip(bitmaps, offs)) + '};')
out.append(f'static const unsigned char ov_pixels[{len(blob)}]={{' + ','.join(str(b) for b in blob) + '};')
# lab[view][lang] = {bitmap, x, y}: view 0 status (texels relative to the map), 1 fullscreen (screen texels)
out.append('typedef struct { short bid,x,y; } OvLabel;')
out.append('typedef struct { unsigned char kind,page,stage,slot,flagtype,chars; unsigned short flag; short icon; short ico[2][2]; OvLabel lab[2][2]; unsigned short guard[2]; unsigned char side, tstage, tslot; } OvMarker;')
out.append(f'#define OV_MARKER_COUNT {len(markers)}')
def lab(m, vi, lang):
    return m.get('lab', {}).get((vi, lang), (-1, 0, 0))
out.append('static const OvMarker ov_markers[]={' + ','.join(
    f"{{{m['kind']},{m['page']},{m['stage']},{m['slot']},{m['flagtype']},{m['chars']},{m['flag']},{m['icon']},"
    f"{{{{{m.get('ico', {}).get(0, (0, 0))[0]},{m.get('ico', {}).get(0, (0, 0))[1]}}},{{{m.get('ico', {}).get(1, (0, 0))[0]},{m.get('ico', {}).get(1, (0, 0))[1]}}}}},"
    "{" + ','.join('{' + ','.join('{%d,%d,%d}' % lab(m, vi, lang) for lang in ('en', 'ko')) + '}' for vi in range(2)) + "}," + "{%d,%d}" % tuple(m.get('guard', (0xFFFF, 0xFFFF))) + ",%d,%d,%d}" % ((m.get('side', 0),) + tuple(m.get('target', (0, 0))))
    for m in markers) + '};')
# leader lines of room names placed outside their room (texels, same spaces as the labels)
lines = [(k, vi, li, *m['lines'][(vi, lang)]) for k, m in enumerate(markers) for vi in range(2) for li, lang in enumerate(('en', 'ko'))
         if (vi, lang) in m.get('lines', {})]
out.append('typedef struct { unsigned short marker; unsigned char view,lang; short x0,y0,x1,y1; } OvLine;')
out.append(f'#define OV_LINE_COUNT {len(lines)}')
out.append('static const OvLine ov_lines[]={' + (','.join('{%d,%d,%d,%d,%d,%d,%d}' % t for t in lines) or '{0}') + '};')
out.append('static const short ov_full_origin[11][2]={' + ','.join('{%d,%d}' % o for o in ORIGIN) + '};')
out.append('static const unsigned short ov_guards[][3]={' + (','.join('{%d,%d,%d}' % g for g in guard_rows) or '{255,0,0}') + '};')
out.append('static const unsigned short ov_conds[][3]={' + (','.join('{%d,%d,%d}' % tuple(c) for c in conds) or '{255,0,0}') + '};')
# fullscreen terrain = the native map's own CLUT colours (exe loader 0x43bfb0, flash TIM: current room +1..+3 = 0x1F)
_clut = [struct.unpack_from('<256H', (ITEM_M2 / p['file']).read_bytes(), 20) for p in d['pages']]
NORMAL, VARIANT = (0x12dc, 0xe1, 0xe1, 0x81a4, 0x81a4, 0), (0x12dc, 0xe1, 0xe1, 0x81a4, 0x83f4, 0x279)
variant = [[int(tuple(c[13 + 6 * k:19 + 6 * k]) == VARIANT) for k in range(32)] for c in _clut]
assert all(tuple(c[13 + 6 * k:19 + 6 * k]) in (NORMAL, VARIANT) or not c[13 + 6 * k] or k >= 32 for c in _clut for k in range(32))
assert all(c[7] == 0x5ad6 for c in _clut)
STP = 0x8000
amber3, amber4 = STP | (2 << 10) | (15 << 5) | 28, STP | (1 << 10) | (11 << 5) | 22    # same as the runtime tint()
# 1 wall, 2 door, 3 edge, 4 fill, 5 variant fill, 6 variant +5, 7 current (red), 8/9 remaining-item amber
terrain_palette = [0, 0x5ad6, 0x12dc, 0xe1, 0x81a4, 0x83f4, 0x279, 0x1f, amber3, amber4, 0, 0, 0, 0, 0, 0]
out.append('static const unsigned short ov_terrain_palette[16]={' + ','.join(map(str, terrain_palette)) + '};')
out.append('static const unsigned char ov_slot_variant[11][32]={' + ','.join('{' + ','.join(map(str, v)) + '}' for v in variant) + '};')
out.append(f'#define OV_LEGEND_ROWS {len(legend)}')
out.append('static const short ov_legend[][4]={' + ','.join('{%d,%d,%d,%d}' % t for t in legend) + '};')
# per-room remaining-item list for the orange room tint: (stage, slot, flag, chars)
tint = sorted({(i['map']['stage'], i['map']['slot'], i['flag'], sum(1 << c for c in i['chars'])) for i in d['items'] if i['map']})
out.append(f'#define OV_TINT_COUNT {len(tint)}')
out.append('static const unsigned char ov_tint[][4]={' + ','.join('{%d,%d,%d,%d}' % t for t in tint) + '};')
(ROOT / 'src/overlay_data.h').write_text('\n'.join(out) + '\n')
print('bitmaps', len(bitmaps), 'pixels', len(blob), 'markers', len(markers), 'tint', len(tint))
# ---- review previews: build/layout-<status|full>-<page>-<lang>.png (terrain + every marker/name/leader)
PREVIEW_PAGES = [int(v) for v in os.environ.get('ANNOTATED_PREVIEW', '').split(',') if v]   # e.g. ANNOTATED_PREVIEW=0,1 (slow at S=8)
TER = {7: (180, 180, 180)}
for vi, vname in enumerate(('status', 'full')):
    z = VIEWS[vi]['z']
    for page in PREVIEW_PAGES:
        for lang in ('en', 'ko'):
            W, H = (160 * S, 104 * S) if vi == 0 else (320 * S, 240 * S)
            ox, oy = ((16 * S, 3 * S) if vi == 0 else (0, 0))
            im = Image.new('RGB', (W, H), (14, 14, 40)); p = im.load()
            mo = (0, 0) if vi == 0 else ORIGIN[page]
            for i, v in enumerate(MAP_PX[page]):
                if v == 7 or v >= 13:
                    c = TER.get(v, (230, 180, 32) if (v - 13) % 6 == 0 else (32, 106, 0))
                    x0, y0 = ox + (mo[0] + (i % 128) * z) * S, oy + (mo[1] + (i // 128) * z) * S
                    for yy in range(y0, y0 + z * S):
                        for xx in range(x0, x0 + z * S):
                            if 0 <= xx < W and 0 <= yy < H: p[xx, yy] = c
            for m in markers:
                if m['page'] != page:
                    continue
                ln = m.get('lines', {}).get((vi, lang))
                if ln:
                    for xx in range(min(ln[0], ln[2]), max(ln[0], ln[2]) + 2):
                        for yy in range(min(ln[1], ln[3]), max(ln[1], ln[3]) + 2):
                            if 0 <= ox + xx < W and 0 <= oy + yy < H: p[ox + xx, oy + yy] = PALETTE[GREY]
                ico = m.get('ico', {}).get(vi)
                lab = m.get('lab', {}).get((vi, lang))
                for bid, bx, by in ((m['icon'], *(ico or (0, 0))), (lab if lab and (vi == 1 or m['kind'] == 1) else (-1, 0, 0))):
                    if bid < 0:
                        continue
                    w, h, data = bitmaps[bid]
                    for y in range(h):
                        for x in range(w):
                            c = data[y * w + x]
                            if c and 0 <= ox + bx + x < W and 0 <= oy + by + y < H: p[ox + bx + x, oy + by + y] = PALETTE[c]
            im.save(ROOT / f'build/layout-{vname}-{page:02d}-{lang}.png')
# ---- self-check: lock keys follow the door direction (vertical door: |door| key name row; horizontal: stacked)
for m in markers:
    dr = m.get('door')
    if not dr or not m.get('side'):
        continue
    sgn = 1 if m['side'] == 1 else -1
    dx, dy = dr['dx'] * sgn, dr['dy'] * sgn
    page = m['page']
    dcx, dcy = to_tex(VIEWS[1], page, dr['cx'] * S, dr['cy'] * S)
    iw, ih = bitmaps[m['icon']][:2]
    ix, iy = m['ico'][1]
    for lang in ('en', 'ko'):
        bid, lx, ly = m['lab'][(1, lang)]
        w, h = bitmaps[bid][:2]
        if dx:   # vertical door: icon beside the door, name in the same row beyond it
            assert (ix - dcx) * dx > 0 and abs(iy + ih / 2 - dcy) < 1 and abs(ly + h / 2 - (iy + ih / 2)) <= ih + 1, ('vertical door', m['page'], dr)
            assert (lx - ix) * dx > 0, ('name not beyond the key', m['page'], dr)
        else:    # horizontal door: icon above/below, name stacked beyond it
            assert (iy - dcy) * dy > 0 and abs(ix + iw / 2 - dcx) < 1 and abs(lx + w / 2 - (ix + iw / 2)) <= iw + 1, ('horizontal door', m['page'], dr)
            assert (ly - iy) * dy > 0, ('name not beyond the key', m['page'], dr)
print('lock layout self-check ok:', sum(1 for m in markers if m.get('side')), 'lock markers')
# ---- self-check: names that can be on screen together (same character; not the two sides of one door) must not overlap
# each other or cover more than half of a visible icon (fullscreen view)
def _covis(a, b):
    return a is not b and a['chars'] & b['chars'] and not (a.get('door') and a.get('door') is b.get('door') and a['side'] != b['side'])
overlaps = []
for lang in ('en', 'ko'):
    for page in range(len(d['pages'])):
        ms = [m for m in markers if m['page'] == page and 1 in m.get('ico', {}) or m['page'] == page and (1, lang) in m.get('lab', {})]
        labs = [(m, *m['lab'][(1, lang)]) for m in ms if (1, lang) in m.get('lab', {})]
        for i, (a, ba, xa, ya) in enumerate(labs):
            wa, ha = bitmaps[ba][:2]
            for b, bb, xb, yb in labs[i + 1:]:
                wb, hb = bitmaps[bb][:2]
                if _covis(a, b) and xa < xb + wb and xb < xa + wa and ya < yb + hb and yb < ya + ha:
                    overlaps.append((lang, page, 'name/name', a.get(lang + '_t', ''), bitmaps and (a['kind'], b['kind']), (xa // S, ya // S)))
            for b in ms:
                if 1 not in b.get('ico', {}) or not _covis(a, b):
                    continue
                (ix, iy), (iw, ih) = b['ico'][1], bitmaps[b['icon']][:2]
                ow = max(0, min(xa + wa, ix + iw) - max(xa, ix)) * max(0, min(ya + ha, iy + ih) - max(ya, iy))
                if ow > iw * ih / 2:
                    overlaps.append((lang, page, 'name/icon', (a['kind'], b['kind']), (xa // S, ya // S)))
print('fullscreen overlaps (co-visible):', len(overlaps))
for o in overlaps:
    print('  ', o)
