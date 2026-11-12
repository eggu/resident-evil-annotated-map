"""SD atlas for the Classic REbirth HD loader off (user decisions 2026-11-12) -> src/sd_assets.h.

1x pixel markers (9x9, enemies 5x5), the approved RE1 lock table (body colour + pattern per key), Galmuri9 room names and legend with
a 1 px shadow, one name colour. Inputs: build/sd-markers.json (tools/gen_assets.py, ov_markers order) and data/sd-layout.json
(tools/sd_layout.py). Text is stored as 1-bit ink masks; src/sd_draw.h draws the shadow and picks the colour.

    .venv/bin/python tools/build_sd.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
import sys; sys.path.insert(0, str(ROOT / 'tools'))
from sd_layout import CROWDED   # pages with this many named rooms show names on the zoom view only
FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
LINE_H = 11
VIEWS = (0, 1, 2)   # 0 status screen (icons only), 1 full-screen map, 2 zoom canvas
Z = {0: 1, 1: 2, 2: 4}
# one 16-colour palette for the whole map layer (icons, names, leaders); 'C' (cream) is replaced at run time by the Rooms colour
PAL = {'.': None, 'k': (8, 8, 8), 'C': (255, 240, 200), 'Y': (240, 200, 60), 'p': (176, 112, 255), 'c': (136, 232, 255), 'g': (90, 205, 90),
       'r': (220, 50, 50), 'b': (70, 110, 240), 'o': (140, 150, 60), 'H': (190, 190, 200), 'w': (250, 250, 250), 'Z': (110, 110, 120),
       'Q': (110, 60, 25), 'M': (235, 215, 170), 'm': (150, 150, 150)}
LETTER = {k: i for i, k in enumerate(PAL)}


def bgr555(c):
    return 0 if c is None else 0x8000 | (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10   # bit 15 set: not the transparent colour key


def diamond(f, glyph):
    rows = []
    for r in range(9):
        h = 4 - abs(4 - r)
        rows.append(''.join('w' if (r, c) in glyph and abs(c - 4) < h else 'k' if abs(c - 4) == h else f if abs(c - 4) < h else '.' for c in range(9)))
    return '|'.join(rows)


def herb(f): return '|'.join(['.........', '.kkkkkkk.', '.k' + f * 5 + 'k.', '..k' + f * 3 + 'k..', '..k' + f * 3 + 'k..', '...k' + f + 'k...', '...k' + f + 'k...', '....k....', '.........'])
def ammo(f): return '|'.join(['.........', '.........', '.Y.Y.Y.Y.', 'kkkkkkkkk', 'k' + f * 7 + 'k', 'k' + f * 7 + 'k', 'kkkkkkkkk', '.........', '.........'])
def grenade(f): return '...kkk...|..k' + f * 3 + 'k..|.k' + f * 5 + 'k.|.k' + f * 5 + 'k.|.kmmmmmk.|.kmmmmmk.|.kmmmmmk.|..kkkkk..|.........'


# Lock markers, user-approved table common/sd-lock-assignments.py (K1): 2-row shackle, 9x7 body in the key's characteristic colour,
# a 3x3 or full 7x5 pattern in another. Letters follow PAL here (the script's W -> w, R -> r, m -> M).
S3 = {'+': '.x.|xxx|.x.', 'x': 'x.x|.x.|x.x', '-': '...|xxx|...', 'o': 'xxx|xxx|xxx', '□': 'xxx|x.x|xxx', '|': '.x.|.x.|.x.',
      '∩': 'xxx|x.x|x.x', '||': 'x.x|x.x|x.x', '|||': 'x.x.x|x.x.x|x.x.x', '▽': 'xxxxx|.xxx.|..x..'}
S7 = {'sword3': '.......|....x..|.xxxxx.|....x..|.......', 'check': 'x.x.x.x|.x.x.x.|x.x.x.x|.x.x.x.|x.x.x.x'}


def lock(body, sym, fg):
    if sym in S7: grid = S7[sym].split('|')
    else:
        s = S3[sym].split('|'); p = (7 - len(s[0])) // 2
        grid = ['.' * 7] + ['.' * p + r + '.' * (7 - p - len(s[0])) for r in s] + ['.' * 7]
    inner = [''.join(fg if c == 'x' else body for c in r) for r in grid]
    return '|'.join(['..kkkkk..', '.kk...kk.', 'kkkkkkkkk'] + ['k' + r + 'k' for r in inner] + ['kkkkkkkkk'])


LOCKS = {   # key name in data/annotated.json -> lock art (body, pattern, pattern colour)
    'Armor Key': lock('Y', '▽', 'Q'), 'Sword Key': lock('H', 'sword3', 'Q'), 'Helmet Key': lock('H', '∩', 'Q'),
    'Closet Key': lock('Z', '|', 'w'), 'Shield Key': lock('Y', '□', 'Q'), 'Master Key': lock('Y', 'x', 'r'),
    'Power Room Key': lock('Q', '|', 'Y'), 'Key for Room 002': lock('M', '||', 'Q'), 'Key for Room 003': lock('b', '|||', 'w'),
    'Control Room Key': lock('H', 'check', 'Z'),
    'Lockpick': lock('H', '|', 'Q'),   # Jill's lock pick: the RE2 small key / lock pick marker (series-wide), not in the approved RE1 table
}
ICONS = {
    'puzzle': diamond('Y', {(2, 4), (3, 4), (4, 4), (6, 4)}),
    'event': diamond('p', {(2, 3), (2, 4), (2, 5), (3, 5), (4, 4), (6, 4)}),
    'key': '.........|...kkk...|..kccck..|.kccccck.|.kccccck.|.kccccck.|..kccck..|...kkk...|.........',
    'herb_g': herb('g'), 'herb_r': herb('r'), 'herb_b': herb('b'),
    'ammo_handgun': ammo('r'), 'ammo_shotgun': ammo('o'), 'ammo_magnum': ammo('H'),
    'grenade': grenade('m'), 'grenade_acid': grenade('Y'), 'grenade_flame': grenade('r'),
    'spray': '...kkk...|...kmk...|..kkkkk..|..kwwwk..|..kwrwk..|..krrrk..|..kwrwk..|..kwwwk..|..kkkkk..',
    'ribbon': '..kkkkk..|.kmmmmmk.|kmwwwwwmk|kmwkkkwmk|kmwkmkwmk|kmwkkkwmk|kmwwwwwmk|.kmmmmmk.|..kkkkk..',
    'file': '.kkkkkk..|.kwwwwkk.|.kwkkwwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kkkkkkk.',
    'map': '.........|kkkkkkkkk|kMrQMYQMk|kMMQMMQMk|kMMQMgQMk|kMMQMMQMk|kkkkkkkkk|.........|.........',
    'typewriter': '.........|..kkkkk..|..kwwwk..|kkkkkkkkk|kmmmmmmmk|kZZZZZZZk|kmmmmmmmk|kkkkkkkkk|.........',
    'itembox': '.........|kkkkkkkkk|kQQQQQQQk|kkkkkkkkk|kQQQYQQQk|kQQQQQQQk|kQQQQQQQk|kkkkkkkkk|.........',
    'enemy': 'kk.kk|krkrk|.krk.|krkrk|kk.kk',
}
# SD item icons (RE1 item ids): ammo by weapon, the three special rounds as grenades, herbs, spray, ribbon
COMMON = {11: 'ammo_handgun', 12: 'ammo_shotgun', 14: 'ammo_magnum', 16: 'grenade', 17: 'grenade_acid', 18: 'grenade_flame',
          47: 'ribbon', 65: 'spray', 67: 'herb_r', 68: 'herb_g', 69: 'herb_b'}


def triangle(w, h, pts):
    """Floor / area arrow: black outline, green fill (the HD arrows' shape), 1x."""
    im = Image.new('L', (w, h)); d = ImageDraw.Draw(im)
    d.polygon(pts, fill=LETTER['k'])
    d.polygon([(x + (w / 2 - x) * .25, y + (h / 2 - y) * .25) for x, y in pts], fill=LETTER['g'])
    return np.asarray(im, np.uint8)


def player_arrow(k):
    """Player heading k (22.5 degrees clockwise from up) in a 9x9 cell, black outline and green fill."""
    import math
    a, c = math.radians(k * 22.5), 4.0
    pts = [(0, -4.2), (2.9, 3.6), (0, 2.0), (-2.9, 3.6)]
    rot = [(c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a)) for x, y in pts]
    im = Image.new('L', (9, 9)); d = ImageDraw.Draw(im)
    d.polygon(rot, fill=LETTER['k'])
    d.polygon([(c + (x - c) * .6, c + (y - c) * .6) for x, y in rot], fill=LETTER['g'])
    return np.asarray(im, np.uint8)


def icon_image(p):
    rows = p.split('|')
    a = np.zeros((len(rows), len(rows[0])), np.uint8)
    for y, r in enumerate(rows):
        for x, c in enumerate(r): a[y, x] = LETTER[c]
    return a


def text_mask(text):
    """Galmuri9 ink, no anti-aliasing, lines LINE_H apart (the shadow is drawn at run time, 1 px down-right, inside the box)."""
    lines = text.split('\n')
    m = Image.new('1', (max(int(FONT.getlength(l)) for l in lines) + 1, LINE_H * len(lines)))
    d = ImageDraw.Draw(m)
    for i, l in enumerate(lines): d.text((0, LINE_H * i), l, font=FONT, fill=1)
    return np.array(m, bool)


LEGEND = dict(
    rows=[('[0] All', '[0] 전체'), ('[1] Rooms', '[1] 방 이름'), ('[2] Locks', '[2] 잠긴 문'), ('[3] Key Items', '[3] 핵심 아이템'),
          ('[4] Files/Maps', '[4] 문서·지도'), ('[5] Puzzles', '[5] 퍼즐'), ('[6] Events', '[6] 이벤트'), ('[7] Items', '[7] 아이템'),
          ('[8] Enemies', '[8] 적')],
    scope=[('[9] Visited', '[9] 방문한 방'), ('[9] Revealed', '[9] 공개된 방'), ('[9] All rooms', '[9] 모든 방')],
    lang=('[\\] English', '[\\] 한국어'),
    zoom=[('[Confirm] Zoom 1x', '[결정] 확대 1x'), ('[Confirm] Zoom 2x, Pan', '[결정] 확대 2x, 이동')],
    tab=[('[TAB] Map', '[TAB] 지도'), ('[TAB] Close', '[TAB] 닫기')],
    hide=('[~] Hide', '[~] 숨김'), fold=('[~] Map Notes', '[~] 지도 메모'))
FULL_BAND = (205, 11)    # legend band of the full-screen map: top y, row pitch (3 rows end at 238)
STATUS_BAND = (186, 10)  # status screen: below the map window, above y 216


def main():
    sd = json.loads((ROOT / 'build/sd-markers.json').read_text())
    layout = json.loads((ROOT / 'data/sd-layout.json').read_text())
    annotated = json.loads((ROOT / 'data/annotated.json').read_text())
    ms = sd['markers']
    icon_px, icons, icon_id = bytearray(), [], {}
    def add_icon(key, a):
        if key not in icon_id:
            icon_id[key] = len(icons); icons.append((len(icon_px), a.shape[1], a.shape[0])); icon_px.extend(a.tobytes())
        return icon_id[key]
    for k, p in ICONS.items(): add_icon(('icon', k), icon_image(p))
    for k, p in LOCKS.items(): add_icon(('lock', k), icon_image(p))
    nav = [triangle(12, 9, [(6, 0), (11, 8), (0, 8)]), triangle(12, 9, [(0, 0), (11, 0), (6, 8)]),
           triangle(9, 12, [(8, 0), (8, 11), (0, 6)]), triangle(9, 12, [(0, 0), (0, 11), (8, 6)])]
    nav_ids = [add_icon(('nav', i), a) for i, a in enumerate(nav)]
    arrow_ids = [add_icon(('arrow', k), player_arrow(k)) for k in range(16)]
    # text masks (1 bit per texel, rows padded to bytes)
    text_px, texts, text_id = bytearray(), [], {}
    def add_text(t):
        if t not in text_id:
            m = text_mask(t)
            packed = np.packbits(m, axis=1)
            text_id[t] = len(texts); texts.append((len(text_px), m.shape[1], m.shape[0])); text_px.extend(packed.tobytes())
        return text_id[t]
    leg = lambda pair: [add_text(t) for t in pair]
    rows = [leg(p) for p in LEGEND['rows']]
    scope = [leg(p) for p in LEGEND['scope']]
    lang, hide, fold = leg(LEGEND['lang']), leg(LEGEND['hide']), leg(LEGEND['fold'])
    zoom = [leg(p) for p in LEGEND['zoom']]
    tab = [leg(p) for p in LEGEND['tab']]
    titles = [[add_text(en), add_text(ko)] for en, ko in sd['page_names']]
    # legend cells: columns of rows, left to right; r: 0-8 category, 9 scope, 10 language, 11 zoom, 12 tab, 13 hide
    def width(r, lg):
        ids = rows[r] if r < 9 else sum(scope, []) if r == 9 else {10: lang, 11: sum(zoom, []), 12: sum(tab, []), 13: hide}[r]
        return max(texts[i][1] for i in ids)
    def cells(order, band, nrows, gap=6):
        top, pitch = band
        out, x = [], 4
        for c in range(0, len(order), nrows):
            col = order[c:c + nrows]
            for k, r in enumerate(col): out.append((r, x, top + pitch * k))
            x += max(width(r, 0) for r in col) + gap
        assert x - gap <= 318, ('legend too wide', x - gap)
        return out
    full_cells = cells([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13], FULL_BAND, 3)   # the zoom hint (11) sits under the page title
    status_cells = cells([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13], STATUS_BAND, 3)
    # markers -------------------------------------------------------------------------------------------------------------
    def icon_of(m):
        k = m['kind']
        if k == 1 and not m['centre']: return icon_id[('icon', m['sd'])] if m['sd'] in ('typewriter', 'itembox') else None
        if k == 2: return None if m['side'] in (1, 2) else icon_id[('lock', 'Lockpick' if m['name'] == 'Lockpick' else m['name'])]
        if k == 3: return icon_id[('icon', 'key')]
        if k == 4: return icon_id[('icon', 'map' if 78 <= m['item'] <= 83 else 'file')]
        if k == 5: return icon_id[('icon', 'puzzle')]
        if k == 6: return icon_id[('icon', COMMON[m['item']])]
        if k == 7: return icon_id[('icon', 'enemy')]
        if k == 8: return icon_id[('icon', 'event')]
        return None
    marks = []   # per marker: icon, pos[3], cover[3]
    for i, m in enumerate(ms):
        ic = icon_of(m)
        pos = []
        for v in VIEWS:
            if ic is None: pos.append((0, 0)); continue
            ox, oy = sd['origin'][m['page']] if v == 1 else (0, 0)
            w, h = icons[ic][1:]
            pos.append((ox + round(m['x'] * Z[v] - w / 2), oy + round(m['y'] * Z[v] - h / 2)))
        marks.append(dict(icon=ic, pos=pos, cover=[-1, -1, -1]))
    # tiers (as the HD layout): key items and puzzles are never covered; a document on one moves to its bottom-right corner,
    # a common item or enemy waits until that marker is gone (run time 'cover')
    box = lambda p, ic: (p[0] + 2, p[1] + 2, p[0] + icons[ic][1] - 2, p[1] + icons[ic][2] - 2)
    hit = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    tops = [i for i, m in enumerate(ms) if m['kind'] in (3, 5) and marks[i]['icon'] is not None]
    for i, m in enumerate(ms):
        if marks[i]['icon'] is None or m['kind'] not in (4, 6, 7): continue
        for v in VIEWS:
            t = next((t for t in tops if ms[t]['page'] == m['page'] and ms[t]['chars'] & m['chars'] and hit(box(marks[t]['pos'][v], marks[t]['icon']), box(marks[i]['pos'][v], marks[i]['icon']))), None)
            if t is None: continue
            if m['kind'] == 4:
                tp = marks[t]['pos'][v]; marks[i]['pos'][v] = (tp[0] + 6, tp[1] + 6)
            else: marks[i]['cover'][v] = t
    # rooms -------------------------------------------------------------------------------------------------------------------
    named_on = {}
    for m in ms:
        if m['centre']: named_on[m['page']] = named_on.get(m['page'], 0) + 1
    crowded = [int(named_on.get(p, 0) >= CROWDED) for p in range(11)]
    room_rows, missing = [], []
    for i, m in enumerate(ms):
        if not m['centre']: continue
        entry = []
        for v in (1, 2):
            for li, lg in enumerate(('en', 'ko')):
                o = layout.get(str(m['page']), {}).get(str(v), {}).get(str(m['slot']), {}).get(lg)
                if o is None:   # no name on the full-screen view of a crowded page
                    if v == 1 and crowded[m['page']]: entry.append(dict(sprite=0xFFFF, x=0, y=0, n=0, pt=[0] * 6)); continue
                    missing.append((m['page'], v, m['slot'], lg)); entry.append(None); continue
                pts = [q for p in o['leader'][:3] for q in p]
                entry.append(dict(sprite=add_text(o['text']), x=o['x'], y=o['y'], n=len(o['leader'][:3]), pt=pts + [0] * (6 - len(pts))))
        room_rows.append((i, entry))
    assert not missing, ('rooms without an SD layout (run tools/sd_layout.py):', missing[:5])
    # emit ---------------------------------------------------------------------------------------------------------------------
    L = ['/* generated by tools/build_sd.py from build/sd-markers.json and data/sd-layout.json: the SD atlas. Do not edit. */',
         'static const unsigned short sd_pal[16] = {' + ','.join(str(bgr555(c)) for c in PAL.values()) + '};   /* index 2 (cream) is the Rooms colour at run time */',
         f'static const unsigned char sd_icon_px[{len(icon_px)}] = {{' + ','.join(map(str, icon_px)) + '};',
         'typedef struct { unsigned short off; unsigned char w, h; } SdIcon;',
         'static const SdIcon sd_icons[] = {' + ','.join('{%d,%d,%d}' % t for t in icons) + '};',
         f'static const unsigned char sd_text_px[{len(text_px)}] = {{' + ','.join(map(str, text_px)) + '};',
         'typedef struct { unsigned off; unsigned short w, h; } SdText;   /* 1 bit per texel, rows padded to bytes */',
         'static const SdText sd_texts[] = {' + ','.join('{%d,%d,%d}' % t for t in texts) + '};',
         'static const unsigned short sd_nav_icon[4] = {%s};' % ','.join(map(str, nav_ids)),
         'static const unsigned short sd_arrow_icon[16] = {%s};   /* player heading cells, 9x9 */' % ','.join(map(str, arrow_ids)),
         'static const unsigned short sd_row[9][2] = {' + ','.join('{%d,%d}' % tuple(r) for r in rows) + '};',
         'static const unsigned short sd_scope[3][2] = {' + ','.join('{%d,%d}' % tuple(r) for r in scope) + '};',
         'static const unsigned short sd_lang[2] = {%d,%d};' % tuple(lang),
         'static const unsigned short sd_zoom[2][2] = {' + ','.join('{%d,%d}' % tuple(r) for r in zoom) + '};',
         'static const unsigned short sd_tab[2][2] = {' + ','.join('{%d,%d}' % tuple(r) for r in tab) + '};',
         'static const unsigned short sd_hide[2] = {%d,%d};' % tuple(hide),
         'static const unsigned short sd_fold[2] = {%d,%d};' % tuple(fold),
         'static const unsigned short sd_title[11][2] = {' + ','.join('{%d,%d}' % tuple(r) for r in titles) + '};',
         'typedef struct { unsigned char r; short x, y; } SdCell;   /* r: 0-8 category, 9 scope, 10 language, 11 zoom, 12 tab, 13 hide */',
         f'#define SD_FULL_CELLS {len(full_cells)}', f'#define SD_STATUS_CELLS {len(status_cells)}',
         'static const SdCell sd_full_cells[] = {' + ','.join('{%d,%d,%d}' % c for c in full_cells) + '};',
         'static const SdCell sd_status_cells[] = {' + ','.join('{%d,%d,%d}' % c for c in status_cells) + '};',
         f'#define SD_STATUS_FOLD_Y {STATUS_BAND[0]}', f'#define SD_FULL_BAND {FULL_BAND[0] - 1}   /* the opaque legend panel starts here */',
         'typedef struct { unsigned short icon; short pos[3][2]; short cover[3]; } SdMark;   /* icon 0xFFFF: none; indexed like ov_markers */',
         'static const SdMark sd_marks[] = {' + ','.join('{%d,{%s},{%s}}' % (0xFFFF if k['icon'] is None else k['icon'], ','.join('{%d,%d}' % p for p in k['pos']), ','.join(map(str, k['cover']))) for k in marks) + '};',
         'typedef struct { unsigned short sprite; short x, y; unsigned char n; short pt[6]; } SdName;',
         'typedef struct { unsigned short marker; SdName v[2][2]; } SdRoom;   /* [view 1 full, 2 zoom][lang] */',
         f'#define SD_ROOM_COUNT {len(room_rows)}',
         'static const unsigned char sd_crowded[11] = {%s};   /* names only on the zoom view */' % ','.join(map(str, crowded)),
         'static const SdRoom sd_rooms[SD_ROOM_COUNT] = {' + ',\n'.join('{%d,{%s}}' % (i, ','.join('{%s}' % ','.join('{%d,%d,%d,%d,{%s}}' % (e['sprite'], e['x'], e['y'], e['n'], ','.join(map(str, e['pt']))) for e in entry[a * 2:a * 2 + 2]) for a in (0, 1))) for i, entry in room_rows) + '};']
    for k in ICONS: L.append(f'#define SDI_{k.upper()} {icon_id[("icon", k)]}')
    (ROOT / 'src/sd_assets.h').write_text('\n'.join(L) + '\n')
    print(f'{len(icons)} icons, {len(texts)} texts ({len(text_px)} bytes), {len(room_rows)} rooms, legend cells full {len(full_cells)} status {len(status_cells)}')


if __name__ == '__main__':
    main()
