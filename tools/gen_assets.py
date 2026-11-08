"""data/annotated.json -> src/overlay_data.h (4bpp label/icon bitmaps, markers with offline label layout).

All overlay geometry is in hi-res texels: S texels per PSX pixel. The runtime composes these bitmaps
into 256x256 4bpp TIM tiles and draws them as native sprites with UVs scaled by S.
"""
import argparse, json, math, os, struct, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
S = 8   # texels per PSX pixel (REbirth wraps sprite UVs at 256, so overlay textures stay 256 = 32 PSX px; S=16 needed 512 and broke, 2026-10-20)
TILE = 32 * S   # overlay tile texture size (32 PSX pixels per tile)
FONTS = Path(__file__).resolve().parents[1] / 'fonts'   # bundled OFL fonts: same output on any OS / CI
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font', default=str(FONTS / 'Pretendard-Medium.otf'))
parser.add_argument('--title-font-en', default=str(FONTS / 'NotoSerif-Italic.ttf'))
parser.add_argument('--title-font-ko', default=str(FONTS / 'NanumMyeongjo-Regular.ttf'))
args = parser.parse_args()
for path in (args.font, args.title_font_en, args.title_font_ko):
    ImageFont.truetype(path, 16)  # Fail before generating assets if a font cannot be loaded.
FONT = args.font
LATIN_SCALE = 0.92   # Pretendard's Latin runs ~8 % wider than its Hangul (and than the old Apple SD Gothic Neo)
FACE, OUTLINE = 0, S // 4   # Medium weight, 1-texel outline: Bold + 2-texel outline was blurry at map resolution
d = json.loads((ROOT / 'data/annotated.json').read_text())

# palette index -> RGB (0 = transparent)
# Nonzero RGB keeps the panel opaque in the native renderer (RGB zero is color-keyed).
PALETTE = [None, (9, 9, 9), (255, 240, 210), (60, 220, 255), (240, 240, 240), (255, 205, 70), (255, 150, 30),
           (175, 175, 175), (95, 95, 95), (150, 100, 40), (220, 60, 50), (60, 220, 70), (80, 140, 255),
           (176, 112, 255), (140, 100, 20), (255, 255, 255)]   # 13 (DCYAN, unused by icons before): event purple #B070FF (RE0 event colour)
BLACK, CREAM, CYAN, WHITE, GOLD, AMBER, GREY, DGREY, BRASS, RED, GREEN, BLUE, DCYAN, DGOLD, PURE = range(1, 16)
KIND = dict(room=1, save=1, lock=2, key=3, document=4, puzzle=5, common=6, enemy=7, event=8)
EVENT = DCYAN
FLAG_NONE, FLAG_PICKUP, FLAG_DOOR, FLAG_SOLVED, FLAG_KILL = 0, 1, 2, 3, 4
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


def text_bitmap(text, size, color, face=None, left=False, legend=False, align='c'):
    stroke = 3 * S // 4 if legend else OUTLINE
    if '\n' in text:   # two lines: titles left-aligned; names aligned toward their icon (RE0 rule): l / c / r
        parts = [text_bitmap(t, size, color, face) for t in text.split('\n')]
        gap = size // 4 if left else -2   # map titles ('MANSION' / '1F'): open line spacing; names stay tight
        w, h = max(p.width for p in parts), sum(p.height for p in parts) + gap * (len(parts) - 1)
        out = Image.new('L', (w, h))
        y = 0
        for part in parts:
            a = 'l' if left else align
            out.paste(part, (0 if a == 'l' else w - part.width if a == 'r' else (w - part.width) // 2, y), part.point(lambda v: 255 if v else 0))
            y += part.height + gap
        return out
    if not legend and not face and text.isascii():
        size = round(size * LATIN_SCALE)
    font = ImageFont.truetype(*(face or (FONT, )), size, **({} if face else dict(index=FACE)))
    l, t, r, b = font.getbbox(text, stroke_width=stroke)
    w, h = r - l + 2, b - t + 2
    fill = Image.new('L', (w, h))
    edge = Image.new('L', (w, h))
    ImageDraw.Draw(edge).text((1 - l, 1 - t), text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
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


def diamond(body, glyph):
    """9 x 9 cell diamond (4.5 PSX px, inside the 5 PSX HD icon box): black outline, `body` fill, white glyph cells (row, col)."""
    rows = []
    for r in range(9):
        half = 4 - abs(4 - r)
        rows.append(''.join('w' if (r, c) in glyph and abs(c - 4) < half else 'k' if abs(c - 4) == half else body if abs(c - 4) < half else '.' for c in range(9)))
    return '\n'.join(rows)


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
    'puzzle': icon(diamond('a', {(2, 4), (3, 4), (4, 4), (6, 4)})),   # orange diamond with '!' (RE0 rule)
    'event': icon(diamond('e', {(2, 3), (2, 4), (2, 5), (3, 3), (3, 5), (4, 5), (5, 4), (7, 4)})),   # purple diamond with '?'
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
# Enemy icons (assets/enemy-icons/, 32 x 32 RGBA, copied unchanged) each get their OWN 4bpp CLUT: index 0 transparent
# (alpha < 128), 15 colours from a median cut over that icon's opaque pixels, no dither. One shared CLUT for all kinds
# (candidates 4-5) pulled every icon into the same brown range. The runtime uploads one 256 texture per kind with its CLUT
# and draws each enemy as its own sprite. 32 texels = 4 PSX px, the size of the other icons.
import runpy as _rp
ENEMY_PNG = dict(zombie='zombie', cerberus='cerberus', spider='web-spinner', black_tiger='black-tiger', crow='crow',
                 hunter='hunter', wasp='wasp', plant42='plant-42', chimera='chimera', adder='adder', neptune='neptune',
                 tyrant='tyrant', yawn='yawn', fountain_plant='fountain-plant')
_enemy_rgba = {k: Image.open(ROOT / f'assets/enemy-icons/enemy-{v}.png').convert('RGBA') for k, v in ENEMY_PNG.items()}
assert all(im.size == (32, 32) for im in _enemy_rgba.values())
EI = _rp.run_path(str(ROOT / 'tools/enemy_icons.py'))
enemy_clut, hue_of = EI['enemy_clut'], EI['hue_of']
ENEMY_PALETTES, enemy_report = {}, {}
for k, im in _enemy_rgba.items():
    out, pal = enemy_clut(im)
    ICON_ID['enemy_' + k] = add_bitmap(out)
    ENEMY_PALETTES[k] = pal
    src = [p[:3] for p in im.get_flattened_data() if p[3] >= 128]
    dst = [pal[v] for v in out.get_flattened_data() if v]
    err = sum(math.dist(a, b) for a, b in zip(src, dst)) / len(src)
    hs, hd = hue_of(src), hue_of(dst, 1)
    enemy_report[k] = (err, hs, hd)
    # checks: mean RGB distance to the 32 x 32 source (after RGB555) below 24 of 441 (Tyrant's gradients are the worst,
    # about 21), dominant hue kept within 12 degrees
    assert err < 24, ('enemy icon colour error', k, err)
    assert hs is None or (hd is not None and min(abs(hs - hd), 360 - abs(hs - hd)) < 12), ('enemy hue lost', k, hs, hd)
for k in ('fountain_plant',):   # stays (lime) green: its source leaves are (163, 182, 13), hue 66; the shared CLUT made them tan
    assert 55 <= enemy_report[k][2] <= 165, ('plant not green', k, enemy_report[k])
print('enemy icons: own CLUT each;', ', '.join(f'{k} err {e:.1f} hue {hs and round(hs)}->{hd and round(hd)}' for k, (e, hs, hd) in enemy_report.items()))



# ---- HD-style icons for the FULL map only (the status screen keeps the pixel icons). Reused from the RE1 HD set
# (assets/hd-icons/, map.json: RE1 item name -> stem) plus new art dropped into assets/hd-icons-new/<stem>.png: the stems below
# are the file names the brief asks for, so adding a PNG and rebuilding needs no code change. A name without art keeps its pixel
# icon (the placeholder). Each distinct icon gets its own 256 texture + 16-colour CLUT at runtime, like the enemies.
NEW_STEMS = {'Armor Key': 'armor-key', 'Sword Key': 'sword-key', 'Shield Key': 'shield-key', 'Helmet Key': 'helmet-key', 'Master Key': 'master-key',
             'Control Room Key': 'control-room-key', 'Power Room Key': 'power-room-key', 'Key for Room 002': 'room-002-key',
             'Key for Room 003': 'room-003-key', 'Closet Key': 'closet-key', 'Emblem': 'emblem', 'Gold Emblem': 'gold-emblem', 'Flare': 'flare',
             'Slides': 'slides', 'Empty Bottle': 'empty-bottle', 'Water': 'water', 'UMB No.2': 'umb-no2', 'UMB No.4': 'umb-no4',
             'Herbicide': 'herbicide', 'Lockpick': 'lockpick', 'Broken Shotgun': 'broken-shotgun', 'Blank Book': 'blank-book', "Barry's Picture": 'barrys-picture'}
HD_DIRS = (ROOT / 'assets/hd-icons', ROOT / 'assets/hd-icons-new')
_hd_map = {}
for _cat in json.loads((ROOT / 'assets/hd-icons/map.json').read_text()).values():
    for _name, _v in _cat.items():
        if not _name.startswith('*'): _hd_map[_name] = _v['icon']
_unknown = [f.name for f in (ROOT / 'assets/hd-icons-new').glob('*.png') if f.stem not in NEW_STEMS.values()] if (ROOT / 'assets/hd-icons-new').is_dir() else []
_unknown = [u_ for u_ in _unknown if u_ != 'badge-event.png']
assert not _unknown, ('assets/hd-icons-new has files that are not in the brief (name them after the stems in NEW_STEMS):', _unknown)
def hd_stem(m):
    """HD icon stem for a marker, or None (placeholder = pixel icon): new art wins over a reused icon of the same item."""
    name = m.get('hdname')
    for stem in (NEW_STEMS.get(name), _hd_map.get(name), m.get('hdstem')):
        if stem and any((dd / f'{stem}.png').is_file() for dd in HD_DIRS): return stem
    return None
def hd_png(stem):
    for dd in reversed(HD_DIRS):   # new art first
        if (dd / f'{stem}.png').is_file(): return Image.open(dd / f'{stem}.png').convert('RGBA')
# HD icons are drawn larger than the 32 texel (4 PSX px) sprite: +20 % on the 1x full map, +50 % over the 1.43 zoom scale. The layouts
# reserve boxes of exactly the drawn size (src/re1_map.c HD_SCALE_1X / HD_SCALE_2X, rounded to whole PSX px).
HD_BOX1_PSX, HD_BOX2_PSX = (4 * 120 + 50) // 100, (4 * 214 + 50) // 100
assert (HD_BOX1_PSX, HD_BOX2_PSX) == (5, 9)
HD_BOX1 = add_bitmap(Image.new('L', (HD_BOX1_PSX * S, HD_BOX1_PSX * S)))
HD_BOX2_BASE = add_bitmap(Image.new('L', (50, 50)))   # x1.43 in the zoom stage -> 72 texels = 9 PSX px
assert round(50 * 1.43) == HD_BOX2_PSX * S
def swap_hd(on, box=None):
    """Full-map layouts use the HD icon boxes (32 texels); the status view and the restore keep the pixel icon."""
    for m in markers:
        if 'hd_bid' not in m: continue
        if on and 'px_icon' not in m: m['px_icon'], m['icon'] = m['icon'], box
        elif not on and 'px_icon' in m: m['icon'] = m.pop('px_icon')


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


def label(text, size, color, face=None, left=False, legend=False, align='c'):
    align = align if '\n' in text else 'c'
    k = (text, size, color, face, left, legend, align)
    if k not in label_cache:
        label_cache[k] = add_bitmap(text_bitmap(text, size, color, face, left, legend, align))
    return label_cache[k]


ROOM_SIZE, ITEM_SIZE = 15 * S // 4, 13 * S // 4   # sizes designed at S=4
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
                            y=(r['anchor'][1] + .5) * S, icon=-1, flagtype=FLAG_NONE, flag=0, chars=3, centre=True,
                            text=dict(en=r['name_en'], ko=r['name_ko'])))
for s in d['saves']:
    m = s['map']
    markers.append(dict(kind=KIND['save'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID['typewriter' if s['kind'] == 'typewriter' else 'itembox'], hdstem='badge-typewriter' if s['kind'] == 'typewriter' else 'badge-itembox',
                        flagtype=FLAG_NONE, flag=0, chars=3))
# RE0 map mod name rules: Korean 'A의 B' drops 의 unless the short form reads wrong (game-specific keep-list); 8+ characters
# wrap at the space nearest the middle; one word never splits. No quantities (user override of the RE0 xN rule, 2026-11-07).
KEEP_UI = {'어느 연구원의 유서', '어느 연구원의 편지', '최후의 책(상편)', '최후의 책(하편)'}
WEAPONS = set(range(1, 11))


def drop_ui(ko):
    return ko if ko in KEEP_UI or '의 ' not in ko else ko.replace('의 ', ' ', 1)


def name_lines(name):
    words = name.split(' ')
    if len(name) < 8 or len(words) < 2:
        return name
    n = min(range(1, len(words)), key=lambda n: abs(len(' '.join(words[:n])) - len(' '.join(words[n:]))))
    return ' '.join(words[:n]) + '\n' + ' '.join(words[n:])


def item_text(en, ko):
    return dict(en=name_lines(en), ko=name_lines(drop_ui(ko)))


assert drop_ui('사육사의 일지') == '사육사 일지' and drop_ui('최후의 책(상편)') == '최후의 책(상편)'
assert name_lines('Shotgun Shells') == 'Shotgun\nShells' and name_lines('Blue Gem Stone') == 'Blue Gem\nStone'
assert name_lines('Lockpick') == 'Lockpick' and name_lines('Armor Key') == 'Armor\nKey' and name_lines('Herb') == 'Herb'
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
            base = dict(kind=KIND['lock'], page=page_of(m), stage=m['stage'], slot=m['slot'], icon=ICON_ID['key'],
                        text=item_text(en, ko), hdname=en, color=GOLD, flagtype=FLAG_DOOR, flag=L['bit'], chars=ch, target=(tst, tslot))
            # RE0 rule (default, INI KeySide=0): the key sits on the door centre and never moves (side 3).
            # RE1 HD map mod rule (KeySide=1; gen_labels.key_sides / re1_mapnames.c): off the door along its normal, on the
            # side of the room not visited yet (else the destination). Horizontal door: icon + name side by side, above/below;
            # vertical door: icon over name, left/right. Both sides are generated; the runtime picks one.
            if door:
                markers.append(dict(base, x=door['cx'] * S, y=door['cy'] * S, side=3))
            for side in ((1, 2) if door else (0,)):
                markers.append(dict(base, x=m['px'] * S, y=m['py'] * S, door=door, side=side))
for i in d['items']:
    m = i['map']
    if not m:
        continue
    chars = sum(1 << c for c in i['chars'])
    cat = 'key' if i['item'] in WEAPONS else i['category']   # RE0 rule: weapons are key items
    guard = [guard_index(i['guards'].get(str(c))) for c in (0, 1)]
    if cat == 'common':
        col, ic = GREY, common_icon(i['item'])
    elif cat == 'key':
        col, ic = CYAN, 'weapon' if i['item'] in WEAPONS else 'dot'
    else:
        col, ic = WHITE, 'map' if 78 <= i['item'] <= 83 else 'doc'
    markers.append(dict(kind=KIND[cat], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID[ic], text=item_text(i['name_en'], i['name_ko']), color=col,
                        hdname=i['name_en'], hdstem='badge-map' if cat == 'document' and 78 <= i['item'] <= 83 else 'badge-document' if cat == 'document' else None,
                        flagtype=FLAG_PICKUP, flag=i['flag'], chars=chars, guard=guard))
for e in d['enemies']:   # icon only, no name (RE0 rule); hidden once Flg 0xC3874C[kill] is set
    m = e['map']
    markers.append(dict(kind=KIND['enemy'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID['enemy_' + e['kind']], flagtype=FLAG_KILL, flag=e['kill'], era=e['era'],
                        chars=sum(1 << c for c in e['chars']), guard=[guard_index(e['guards'].get(str(c))) for c in (0, 1)]))
for p in d['puzzles']:
    m = p['map']
    if not m:
        continue
    # solved conditions may differ per character (the Chris and Jill scripts use different flags: solved_by_char)
    by_char = p.get('solved_by_char')
    variants = [(1 << c, by_char[str(c)]) for c in p['chars']] if by_char else [(sum(1 << c for c in p['chars']), p['solved_when'])]
    for chars, solved in variants:
        markers.append(dict(kind=KIND['puzzle'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                            icon=ICON_ID['puzzle'], hdstem='badge-puzzle', text=item_text(p['name_en'], p['name_ko']), color=AMBER,
                            flagtype=FLAG_SOLVED if solved else FLAG_NONE, flag=len(conds), chars=chars))
        conds.extend(solved + [[255, 0, 0]] if solved else [])   # puzzle hidden once every condition holds
for e in d['events']:   # story scenes (tools/extract_events.py): icon only (RE0 rule: no name), hidden once the scene's flag is set
    m = e['map']
    markers.append(dict(kind=KIND['event'], page=page_of(m), stage=m['stage'], slot=m['slot'], x=m['px'] * S, y=m['py'] * S,
                        icon=ICON_ID['event'], hdstem='badge-event', flagtype=FLAG_SOLVED, flag=len(conds), era=e['era'],
                        chars=sum(1 << c for c in e['chars'])))
    conds.extend([e['flag'] + [1]] + [c for alt in e.get('hidden_also', []) for c in [[254, 0, 0]] + alt] + [[255, 0, 0]])   # 254: OR group
# an event icon never sits on a puzzle / key item / other event icon: try one-icon (6 px) steps around its point, nearest
# first, and keep only spots inside its own map room (a plain step right left the room for anchor-placed scenes)
_EV_MASK = {(pg['stage'], r['slot']): {tuple(q) for q in r['mask']} for pg in json.loads((ROOT / 'data/map_rooms.json').read_text())['pages'] for r in pg['rooms']}
_EV_STEPS = sorted(((dx, dy) for dx in range(-4, 5) for dy in range(-4, 5)), key=lambda t: (t[0] ** 2 + t[1] ** 2, -t[0], t[1]))
for ev in (m for m in markers if m['kind'] == KIND['event']):
    x0, y0, room = ev['x'], ev['y'], _EV_MASK[(ev['stage'], ev['slot'])]
    for dx, dy in _EV_STEPS:
        x, y = x0 + dx * 6 * S, y0 + dy * 6 * S
        if (int(x / S), int(y / S)) in room and not any(
                o is not ev and o['page'] == ev['page'] and o['kind'] in (KIND['puzzle'], KIND['key'], KIND['event']) and o['chars'] & ev['chars']
                and abs(o['x'] - x) < 6 * S and abs(o['y'] - y) < 6 * S for o in markers):
            ev['x'], ev['y'] = x, y
            break
    assert (int(ev['x'] / S), int(ev['y'] / S)) in room, ('event icon outside its room', ev['stage'], ev['slot'])


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
HD_KINDS, HD_PALETTES, hd_report = {}, [], {}
for m in markers:
    stem = hd_stem(m)
    if not stem: continue
    if stem not in HD_KINDS:
        im = hd_png(stem)
        assert im.size == (32, 32), ('HD icon must be 32 x 32', stem, im.size)
        out, pal = enemy_clut(im)
        src = [p[:3] for p in im.get_flattened_data() if p[3] >= 128]
        dst = [pal[v] for v in out.get_flattened_data() if v]
        err = sum(math.dist(a, b) for a, b in zip(src, dst)) / len(src)
        assert err < 30, ('HD icon colour error after reduction to 15 colours', stem, err)
        HD_KINDS[stem] = len(HD_KINDS); HD_PALETTES.append(pal); hd_report[stem] = (err, add_bitmap(out))
    m['hd_bid'] = hd_report[stem][1]; m['hd_kind'] = HD_KINDS[stem]
_new_used = sorted({s_ for s_ in HD_KINDS if (ROOT / 'assets/hd-icons-new' / f'{s_}.png').is_file()})
_missing = sorted(n for n, st in NEW_STEMS.items() if not (ROOT / 'assets/hd-icons-new' / f'{st}.png').is_file())
print('HD icons: %d distinct kinds on %d markers (%d from assets/hd-icons-new); placeholders (pixel icon) for %d of the 22 new names: %s' % (
    len(HD_KINDS), sum(1 for m in markers if 'hd_bid' in m), len(_new_used), len(_missing), ', '.join(_missing)))
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
    z, (ox, oy) = view['z'], ((0, 0) if view['z'] in (1, 4) else ORIGIN[page])
    return {(ox + x * z + i, oy + y * z + j) for x, y in pts for i in range(z) for j in range(z)}


def to_tex(view, page, x, y):
    """1x map texel coords -> view texel coords (status: map-relative, fullscreen: screen-absolute)."""
    if view['z'] == 1:
        return x, y
    ox, oy = (0, 0) if view['z'] == 4 else ORIGIN[page]
    return ox * S + view['z'] * x, oy * S + view['z'] * y


TOP, MID = (KIND['key'], KIND['puzzle']), (KIND['lock'], KIND['document'])
NAME_ORDER = {KIND['key']: 0, KIND['puzzle']: 1, KIND['lock']: 2, KIND['document']: 3, KIND['common']: 4}


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


ICON_GROW = 1.5   # names keep clear of OTHER markers' icons up to IconSize 150 %; the own icon's growth is handled at runtime


def core(m, vi, grow=1.0):
    """Central 70 % x 70 % of the icon, scaled about its centre by `grow` (an icon's own collision box)."""
    iw, ih = bitmaps[m['icon']][:2]
    x, y = m['ico'][vi]
    cx, cy, hw, hh = x + iw / 2, y + ih / 2, iw * .35 * grow, ih * .35 * grow
    return (round(cx - hw), round(cy - hh), round(cx + hw), round(cy + hh))


def door_side_key(m, vi, lang, view, page, ms, boxes):
    """RE1 HD rule (KeySide=1): key + name next to the door, on its side, sliding off other icons."""
    iw, ih = bitmaps[m['icon']][:2]
    dr = m['door']
    sgn = 1 if m['side'] == 1 else -1                       # 1: destination side, 2: the door's own room
    dx, dy = dr['dx'] * sgn, dr['dy'] * sgn
    dcx, dcy = to_tex(view, page, dr['cx'] * S, dr['cy'] * S)
    # clear the door: status map draws the whole native marker, fullscreen a 2-px bar on the wall line
    half, gap = (S * (2 if vi == 2 else 1) if vi > 0 else (dr['hw'] if dx else dr['hh']) * S), S // 2
    align = 'c' if not dx else 'l' if dx > 0 else 'r'
    bid = label(m['text'][lang], ITEM_SIZE, m['color'], align=align) if vi > 0 else -1
    lw_, lh_ = bitmaps[bid][:2] if bid >= 0 else (0, 0)
    g = 1 if lw_ else 0
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
        over = sum(overlap(o, q) for o in own for q in boxes if q[4] & m['chars'] and q[5] not in other)
        return over, ix, iy, lx, ly
    # ponytail: slide key + name away from the door (up to 3 px) until clear, then nudge only the name across its row
    span = ih if dx else iw
    nudges = [0] + [v for n in range(S // 2, span + 1, S // 2) for v in (-n, n)]
    # the runtime draws one icon position for both languages: English picks the key's distance, Korean reuses it
    ks = range(7) if lang == 'en' else [m['door_k'][vi]]
    _, ix, iy, lx, ly, _, k = min((place(gap + k * S // 2, n) + (abs(n) + k, k) for k in ks for n in nudges),
                                  key=lambda t: (t[0] > 0, t[0], t[5]))
    m.setdefault('door_k', {})[vi] = k
    m.setdefault('ico', {})[vi] = (round(ix), round(iy))
    if lw_:
        m.setdefault('lab', {})[(vi, lang)] = (bid, round(lx), round(ly))
        boxes.append((round(lx) - 2, round(ly) - 2, round(lx) + lw_ + 2, round(ly) + lh_ + 2, m['chars'], id(m), 2))


def place_name(m, vi, lang, bounds, boxes, idx):
    """RE0 rule: touching candidates right, left, below, above, then the 4 corners; first spot with weighted overlap 0, else
    the lowest. Common items only go where nothing weighing 2+ is hit. No second ring: one name height out (2-line names:
    6 PSX px) read as another marker's name in game (candidate 3: Magnum Rounds, Candles, Serum), so names always touch."""
    text = m['text'][lang]
    w, h = bitmaps[label(text, ITEM_SIZE, m['color'])][:2]
    x0, y0, x1, y1 = m['ico'][vi][0], m['ico'][vi][1], m['ico'][vi][0] + bitmaps[m['icon']][0], m['ico'][vi][1] + bitmaps[m['icon']][1]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx0, by0, bx1, by1 = (v * S for v in bounds)
    spots = [(x1, cy - h / 2, 'l', 1, 0), (x0 - w, cy - h / 2, 'r', -1, 0), (cx - w / 2, y1, 'c', 0, 1), (cx - w / 2, y0 - h, 'c', 0, -1),
             (x1, y1, 'l', 1, 1), (x0 - w, y1, 'r', -1, 1), (x1, y0 - h, 'l', 1, -1), (x0 - w, y0 - h, 'r', -1, -1)]
    best = None
    # each spot may also slide along the icon's edge (still touching it) by up to half the name, in 1/2 PSX px steps
    slides = [(k, spot, d) for k, spot in enumerate(spots)
              for d in [0] + [v for n in range(S // 2, (h if spot[3] else w) // 2 + 1, S // 2) for v in (-n, n)]]
    for k, (lx, ly, align, sx, sy), d in slides:
        lx, ly = (lx, ly + d) if sx and not sy else (lx + d, ly) if sy and not sx else (lx, ly)
        k = (k, abs(d))
        x = round(max(bx0, min(lx, bx1 - w))); y = round(max(by0, min(ly, by1 - h)))
        box = (x, y, x + w, y + h)
        hits = [(b[6], overlap(box, b)) for b in boxes if b[4] & m['chars'] and b[5] != id(m)]
        score, heavy = sum(wt * a for wt, a in hits), any(a and wt >= 2 for wt, a in hits)
        if m['kind'] == KIND['common'] and heavy:
            continue
        own = overlap(box, (x0, y0, x1, y1)) > 0   # the view bounds pushed the name back onto its own icon (ko names at the zoom canvas edge)
        if best is None or (own, score, k) < best[0]:
            best = ((own, score, k), x, y, align)
    if best is None:
        return False
    _, x, y, align = best
    m.setdefault('lab', {})[(vi, lang)] = (label(text, ITEM_SIZE, m['color'], align=align), x, y)
    boxes.append((x - 2, y - 2, x + w + 2, y + h + 2, m['chars'], id(m), 8 if m['kind'] in TOP else 2))
    return True


def layout_view(vi, lang):
    view, stats = VIEWS[vi], dict(inside=0, leader=0, wrapped=0, failed=0, names=0, hidden=0, covered=0, badge=0)
    idx = {id(m): k for k, m in enumerate(markers)}
    for page in range(len(d['pages'])):
        ms = [m for m in markers if m['page'] == page]
        walls = cells_of(view, page, [(i % 128, i // 128) for i, v in enumerate(MAP_PX[page]) if v == 7])
        boxes = []   # (x0, y0, x1, y1, chars, owner, weight): collision boxes for names (weights: RE0 rule)
        # 1) icons on their exact spot (a lock key on the door centre never moves)
        for m in ms:
            if m['icon'] >= 0 and not m.get('door'):
                iw, ih = bitmaps[m['icon']][:2]
                cx, cy = to_tex(view, page, m['x'], m['y'])
                m.setdefault('ico', {})[vi] = (round(cx - iw / 2), round(cy - ih / 2))
        # 2) tiers: key items and puzzles are never covered; a document centred on one moves to its bottom-right badge
        #    spot; a common item or enemy under one is hidden while that marker is shown (runtime 'cover')
        tops = [m for m in ms if m['kind'] in TOP]
        for m in ms:
            if m['icon'] < 0 or m.get('door') or m['kind'] in TOP or m['kind'] in (KIND['lock'], KIND['room']):
                continue
            hit = next((t for t in tops if t['chars'] & m['chars'] and overlap(core(t, vi), core(m, vi))), None)
            if not hit:
                continue
            if m['kind'] == KIND['document']:
                tx, ty = hit['ico'][vi]; tw, th = bitmaps[hit['icon']][:2]; iw, ih = bitmaps[m['icon']][:2]
                m['ico'][vi] = (round(tx + tw - iw * .35), round(ty + th - ih * .35)); stats['badge'] += lang == 'en'
            else:
                m.setdefault('cover', {})[vi] = idx[id(hit)]; stats['covered'] += lang == 'en'
        for m in ms:
            if m['icon'] >= 0 and not m.get('door'):
                boxes.append(core(m, vi, ICON_GROW) + (m['chars'], id(m), 8 if m['kind'] in TOP else 1))
        for m in ms:   # RE1 HD door-side keys (KeySide=1) step around the fixed icons
            if m.get('door'):
                door_side_key(m, vi, lang, view, page, ms, boxes)
        if vi == 0:    # status screen: icons only
            continue
        # 3) room names first: build-time, inside the room's real shape around its pole of inaccessibility, else outside
        #    with a leader line; nothing avoids them and they avoid only each other (RE0 rule)
        rooms = [m for m in ms if m.get('centre')]
        bid = {}
        spec = []
        for m in rooms:
            cells = cells_of(view, page, anchor_part((m['stage'], m['slot']), int(m['x'] // S), int(m['y'] // S)))
            t = m['text'][lang]
            b = label(t, view['size'], CREAM)
            room_w = max(c[0] for c in cells) - min(c[0] for c in cells) + 1
            if bitmaps[b][0] / S > 1.5 * room_w and ' ' in t:   # wider than 150 % of the room: wrap between words
                b = label(wrap(t, view['size']), view['size'], CREAM); stats['wrapped'] += 1
            bid[id(m)] = b
            spec.append(dict(key=id(m), cells=cells, lw=-(-bitmaps[b][0] // S), lh=-(-bitmaps[b][1] // S)))
        res, placed, lines = LL['place_rooms'](spec, walls, view['bounds']) if rooms else ({}, [], [])
        for m in rooms:
            w, h = bitmaps[bid[id(m)]][:2]
            r = res[id(m)]
            if r is None:   # nowhere free: centre on the room anchor
                cx, cy = to_tex(view, page, m['x'], m['y'])
                m.setdefault('lab', {})[(vi, lang)] = (bid[id(m)], round(cx - w / 2), round(cy - h / 2))
                stats['failed'] += 1; print('  no room for name:', m['text'][lang])
                continue
            (bx, by, bw, bh), line = r
            x, y = bx * S + (bw * S - w) // 2, by * S + (bh * S - h) // 2
            m.setdefault('lab', {})[(vi, lang)] = (bid[id(m)], x, y)
            # Room names draw first and are not collision targets for markers.
            stats['leader' if line else 'inside'] += 1
            if line:
                m.setdefault('lines', {})[(vi, lang)] = tuple(v * S + S // 2 for v in line)
        # 4) marker names by tier: key items, puzzles, locks, documents; common items last, only in free space; enemies none
        for m in sorted((m for m in ms if m.get('text') and not m.get('centre') and not m.get('door')),
                        key=lambda m: NAME_ORDER[m['kind']]):
            ok = place_name(m, vi, lang, view['bounds'], boxes, idx)
            stats['names' if ok else 'hidden'] += 1
    print('layout', ('status', 'fullscreen', 'zoom')[vi], lang, stats)



for vi in range(2):
    swap_hd(vi == 1, HD_BOX1)
    for lang in ('en', 'ko'):
        layout_view(vi, lang)
# The zoom view has its own placement in a 512x400 map canvas. Keep textures under 256; only small annotation rasters grow.
VIEWS += (dict(z=4, bounds=(0, 0, 512, 400), size=round(ROOM_SIZE * 1.43)),)
swap_hd(False)
swap_hd(True, HD_BOX2_BASE)
base_icons = [m['icon'] for m in markers]
zoom_icons = {}
for bid in set(base_icons) - {-1}:
    w, h, px = bitmaps[bid]
    image = Image.frombytes('L', (w, h), bytes(px)).resize((round(w * 1.43), round(h * 1.43)), Image.Resampling.NEAREST)
    zoom_icons[bid] = add_bitmap(image)
for m in markers:
    if m['icon'] >= 0: m['icon'] = zoom_icons[m['icon']]
ITEM_SIZE = round(ITEM_SIZE * 1.43)
for lang in ('en', 'ko'): layout_view(2, lang)
ITEM_SIZE = round(ITEM_SIZE / 1.43)
for m, bid in zip(markers, base_icons): m['icon'] = bid
swap_hd(False)
# Full-data check (RE0 rule: a name touches its own marker): every placed marker name, both languages, is at most 1 PSX px
# from its own icon box; candidate 3 had names one line height away (Magnum Rounds, Candles, Serum).
NAME_GAP_MAX = S
far = []
for m in markers:
    if m.get('centre') or m['icon'] < 0:
        continue
    for vi, lang in ((v, l) for v in (1, 2) for l in ('en', 'ko')):
        if (vi, lang) not in m.get('lab', {}):
            continue
        bid, x, y = m['lab'][(vi, lang)]; w, h = bitmaps[bid][:2]
        ib = HD_BOX2_BASE if vi == 2 and 'hd_bid' in m else HD_BOX1 if 'hd_bid' in m else m['icon']
        (ix, iy), (iw, ih) = m['ico'][vi], bitmaps[zoom_icons[ib] if vi == 2 else ib][:2]
        gap = max(0, ix - (x + w), x - (ix + iw), iy - (y + h), y - (iy + ih))
        if gap > NAME_GAP_MAX:
            far.append((m['page'], lang, m['text'][lang], m.get('side'), gap / S, (x // S, y // S, w // S, h // S), (ix // S, iy // S)))
assert not far, ('names away from their marker', far[:10], len(far))
for vi in (1, 2):
    print('name adjacency check ok: view', vi, sum(1 for m in markers for k in m.get('lab', {}) if k[0] == vi and not m.get('centre')), 'names')


# ---- legends (both views): RE2 "DISPLAY STATUS" block, rows [0]..[9] with their state as text, hints and readouts
LEGEND_BODY_SIZE, LEGEND_TITLE_SIZE = 20 * S // 4, 22 * S // 4   # the requested /4 typography at the internal texture scale
FULL_LEGEND_SIZE = LEGEND_BODY_SIZE
ON, OFF = (': ON', ': 켬'), (': OFF', ': 끔')
FULL_ROWS = [  # (variants (en, ko), colour when on). Order: [0] all, [1] rooms, [2] locks, [3] key items, [4] files, [5] puzzles, [6] events, [7] common, [8] enemies, [9] scope
    ([('[0] ALL', '[0] 전체')], PURE), ([('[1] ROOMS', '[1] 방 이름')], CREAM), ([('[2] LOCKS', '[2] 잠긴 문')], GOLD),
    ([('[3] KEY ITEMS', '[3] 핵심 아이템')], CYAN), ([('[4] FILES & MAPS', '[4] 문서·지도')], WHITE), ([('[5] PUZZLES', '[5] 퍼즐')], AMBER),
    ([('[6] EVENTS', '[6] 이벤트')], EVENT), ([('[7] ITEMS', '[7] 일반 아이템')], GREY), ([('[8] ENEMIES', '[8] 적')], RED),
    ([('[9] SCOPE: VISITED', '[9] 범위: 방문한 방'), ('[9] SCOPE: REVEALED', '[9] 범위: 공개된 방'), ('[9] SCOPE: ALL ROOMS', '[9] 범위: 모든 방')], PURE)]
LANG_LABEL = ('[\\] LANGUAGE: ENGLISH', '[\\] 언어: 한국어')   # key VK_OEM_5; Korean keyboards show it as ₩ (README writes \(₩))
full_legend = []   # [row][variant][on/off][lang]
for k, (variants, col) in enumerate(FULL_ROWS):
    rows = []
    for en, ko in variants + [variants[-1]] * (3 - len(variants)):
        if k <= 8:
            rows.append(((label(en + ON[0], FULL_LEGEND_SIZE, col, legend=True), label(ko + ON[1], FULL_LEGEND_SIZE, col, legend=True)),
                         (label(en + OFF[0], FULL_LEGEND_SIZE, DGREY, legend=True), label(ko + OFF[1], FULL_LEGEND_SIZE, DGREY, legend=True))))
        else:
            rows.append(((label(en, FULL_LEGEND_SIZE, col, legend=True), label(ko, FULL_LEGEND_SIZE, col, legend=True)),) * 2)
    full_legend.append(rows)
full_legend_title = (label('Map Notes', LEGEND_TITLE_SIZE, PURE, legend=True), label('지도 메모', LEGEND_TITLE_SIZE, PURE, legend=True))   # RE0 wording
# RE0 rule 4: one colour per category, shared by the legend row and every name of that category. Names are drawn with the
# legend CLUT (runtime layer 1), so equal palette indices give equal colours.
ROW_OF_KIND = {KIND['lock']: 2, KIND['key']: 3, KIND['document']: 4, KIND['puzzle']: 5, KIND['common']: 7}
for m in markers:
    if m.get('centre'):
        assert FULL_ROWS[1][1] == CREAM
    elif m.get('text'):
        assert m['color'] == FULL_ROWS[ROW_OF_KIND[m['kind']]][1], ('name colour differs from its legend row', m['kind'], m['text'])

TITLE_EN, TITLE_KO = (args.title_font_en,), (args.title_font_ko,)
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
# A separate CLUT changes only legend text; rooms/items/icons retain ov_palette.
legend_palette = list(PALETTE)
def snap555(c):
    """Nearest colour the RGB555 palette can show (5 bits per channel, expanded as v<<3|v>>2), as an RGB triple whose
    rgb555() floor lands on that value."""
    five = [round(v * 31 / 255) for v in c]
    return tuple(-(-f * 255 // 31) for f in five)
COMMON_RGB = (184, 188, 196)   # all map mods: cool grey #B8BCC4 for COMMON ITEMS (user 2026-11-08; was lavender #B4A7D6)
HINT_RGB = (150, 156, 172)     # adjustment hints: dimmer than every legend row, a cool grey
OFF_RGB = (106, 106, 106)      # disabled legend rows: #6A6A6A, darker than the common-item grey so they stay distinct
LEADER_RGB = (140, 140, 140)   # room-name leader lines (legend CLUT index BLUE, unused by names/legend text)
# every category colour goes through snap555 so a [Colors] default typed in the INI (runtime: round to 5 bits per channel) gives
# exactly the baked colour
DEFAULT_RGB = dict(Rooms=(240, 226, 190), Locks=(255, 205, 70), KeyItems=(90, 220, 255), Files=(255, 140, 210), Puzzles=(255, 150, 40),
                   Events=PALETTE[EVENT], CommonItems=COMMON_RGB, Enemies=PALETTE[RED])
COLOR_KEYS = [('Rooms', CREAM), ('Locks', GOLD), ('KeyItems', CYAN), ('Files', WHITE), ('Puzzles', AMBER), ('Events', EVENT),
              ('CommonItems', GREY), ('Enemies', RED)]
for idx, rgb in {BLACK:(16,16,16), DGREY:snap555(OFF_RGB), BRASS:snap555(HINT_RGB), PURE:(255,255,255), BLUE:LEADER_RGB,
                 **{i: snap555(DEFAULT_RGB[k]) for k, i in COLOR_KEYS}}.items():
    legend_palette[idx] = rgb
out.append('static const unsigned char ov_color_index[8]={' + ','.join(str(i) for _, i in COLOR_KEYS) + '};')
out.append('static const unsigned short ov_legend_palette[16]={' + ','.join(str(rgb555(c)) for c in legend_palette) + '};')
out.append(f'#define OV_ENEMY_KINDS {len(ENEMY_PNG)}')
out.append('static const short ov_enemy_icons[OV_ENEMY_KINDS]={' + ','.join(str(ICON_ID['enemy_' + k]) for k in ENEMY_PNG) + '};')
out.append('static const unsigned short ov_enemy_palettes[OV_ENEMY_KINDS][16]={' + ','.join(
    '{' + ','.join(str(rgb555(c)) for c in ENEMY_PALETTES[k]) + '}' for k in ENEMY_PNG) + '};')
out.append(f'#define OV_HD_KINDS {max(len(HD_KINDS), 1)}')
out.append('static const short ov_hd_icons[OV_HD_KINDS]={' + (','.join(str(hd_report[k][1]) for k in HD_KINDS) or '-1') + '};')
out.append('static const unsigned short ov_hd_palettes[OV_HD_KINDS][16]={' + (','.join('{' + ','.join(str(rgb555(c)) for c in pal) + '}' for pal in HD_PALETTES) or '{0}') + '};')
_eb = [bitmaps[ICON_ID['enemy_' + k]][2] for k in ENEMY_PNG]
assert len(set(_eb)) == len(_eb), 'two enemy kinds share an icon'
# RE0 map mod legend format (candidate 49): a lone key in brackets like [0]..[9], [H], [~] and [TAB]; key pairs without
# brackets, alternatives joined with ' · ', combinations with ' + '. The modifier is INI [Keys] Modifier (Shift / Ctrl).
def legend_label(en, ko):
    return (label(en, LEGEND_BODY_SIZE, PURE, legend=True), label(ko, LEGEND_BODY_SIZE, PURE, legend=True))
HINT_SIZE = 15 * S // 4   # adjustment hints: smaller than the 20/4 legend rows and dimmer (BRASS in the legend CLUT)
def hint_label(en, ko):
    return (label(en, HINT_SIZE, BRASS, legend=True), label(ko, HINT_SIZE, BRASS, legend=True))
MODS = ('Shift', 'Ctrl')
def fold_label(en, ko):
    """Folded-legend hint ([~] Map Notes): the usual legend text on its own opaque black box, so it stays readable when it sits
    over the zoomed map at the screen's bottom-left (RE0 rule)."""
    pad = 2 * S // 4 * 2
    out_ids = []
    for text in (en, ko):
        im = text_bitmap(text, LEGEND_BODY_SIZE, PURE, legend=True)
        box = Image.new('L', (im.width + 2 * pad, im.height + 2 * pad), BLACK)
        box.paste(im, (pad, pad), im.point(lambda v: 255 if v else 0))
        out_ids.append(add_bitmap(box))
    return tuple(out_ids)
readouts = dict(
    name_size=[hint_label(f'- · + NAME SIZE: {n}%', f'- · + 이름 크기: {n}%') for n in range(50, 151, 10)],
    name_opacity=[hint_label(f'[ · ] NAME OPACITY: {n}%', f'[ · ] 이름 불투명도: {n}%') for n in range(10, 101, 10)],
    icon_size=[[hint_label(f'{mod} + - · + ICON SIZE: {n}%', f'{mod} + - · + 아이콘 크기: {n}%') for n in range(50, 201, 10)] for mod in MODS],
    icon_opacity=[[hint_label(f'{mod} + [ · ] ICON OPACITY: {n}%', f'{mod} + [ · ] 아이콘 불투명도: {n}%') for n in range(10, 101, 10)] for mod in MODS])
# [H] cycles: 0 all names, 1 all but common items, 2 none (INI ItemNames, runtime item_names)
hints = dict(names=[legend_label('[H] ITEM NAMES: ' + en, '[H] 아이템 이름: ' + ko) for en, ko in (('ALL', '모두'), ('NO COMMON', '일반 제외'), ('OFF', '끔'))],
             tab=[hint_label('[TAB] FULL MAP', '[TAB] 전체 지도'), hint_label('[TAB] CLOSE MAP', '[TAB] 지도 닫기')],
             hide=legend_label('[~] HIDE', '[~] 숨김'), fold=fold_label('[~] Map Notes', '[~] 지도 메모'),
             lang=legend_label(*LANG_LABEL))   # [\\] language: same row style (colour, size) as [H]
out.append('static const short ov_name_size[11][2]={' + ','.join('{%d,%d}' % p for p in readouts['name_size']) + '};')
out.append('static const short ov_name_opacity[10][2]={' + ','.join('{%d,%d}' % p for p in readouts['name_opacity']) + '};')
for name, n in (('icon_size', 16), ('icon_opacity', 10)):
    out.append(f'static const short ov_{name}[2][{n}][2]=' + '{' + ','.join('{' + ','.join('{%d,%d}' % p for p in v) + '}' for v in readouts[name]) + '};')
out.append('static const short ov_hint_names[3][2]={' + ','.join('{%d,%d}' % p for p in hints['names']) + '};')
# the zoom key is the game's own confirm/examine action (read from its mapped input, so config.ini Key_Def / Joy_Def apply)
zoom_hints = [hint_label('[CONFIRM] ZOOM: 1x', '[결정] 확대: 1x'), hint_label('[CONFIRM] ZOOM: 2x · PAN', '[결정] 확대: 2x · 이동')]
out.append('static const short ov_zoom_hint[2][2]={' + ','.join('{%d,%d}' % p for p in zoom_hints) + '};')
out.append('static const short ov_hint_tab[2][2]={' + ','.join('{%d,%d}' % p for p in hints['tab']) + '};')
out.append('static const short ov_hint_hide[2]={%d,%d};' % hints['hide'])
out.append('static const short ov_hint_lang[2]={%d,%d};' % hints['lang'])
out.append('static const short ov_hint_fold[2]={%d,%d};' % hints['fold'])
# Cell rows: 0..9 category/scope, 10 name size, 11 name opacity, 12 icon size, 13 icon opacity, 14 [H], 15 [TAB], 16 zoom hint, 18 [\\] language.
def row_ids(r):
    if r < 10: return [b for v in full_legend[r] for st in v for b in st]
    if r in (10, 11): return [b for p in readouts['name_size' if r == 10 else 'name_opacity'] for b in p]
    if r in (12, 13): return [b for v in readouts['icon_size' if r == 12 else 'icon_opacity'] for p in v for b in p]
    if r == 16: return [b for p in zoom_hints for b in p]
    if r == 18: return list(hints['lang'])
    return [b for p in hints['names' if r == 14 else 'tab'] for b in p]
def extent(ids, axis): return max(bitmaps[b][axis] for b in ids)
LEGEND_ROWS = [r for r in range(16) if r not in (10, 11, 12, 13, 15)] + [18]
height = extent([b for r in LEGEND_ROWS for b in row_ids(r)], 1)
step = height + S // 4
hint_height = extent([b for r in (10, 11, 12, 13, 15, 16) for b in row_ids(r)], 1)
hint_step = hint_height + S // 4
title_h = extent(full_legend_title, 1)
def cells(groups, y0, rows_max, row_step=None):
    """Columns of rows, left to right from x = 8 PSX with a 6 PSX gap (10 before the hint group, which is the groups after
    the first `rows_max`-row legend columns marked by a leading None); asserts they fit the 312 PSX screen width."""
    row_step = row_step or step
    gap_before = [g[0] is None for g in groups]
    groups = [[r for r in g if r is not None] for g in groups]
    widths = [extent([b for r in g for b in row_ids(r)], 0) for g in groups]
    xs = [8]
    for i, w in enumerate(widths[:-1]): xs.append(xs[-1] + (w + S - 1) // S + (8 if gap_before[i + 1] else 4))
    assert xs[-1] * S + widths[-1] <= 312 * S, ("legend too wide", xs, widths, [[(r, extent(row_ids(r), 0)) for r in g] for g in groups])
    assert all(len(g) <= rows_max for g in groups)
    out_cells = []
    for g, x, hint in zip(groups, xs, gap_before):
        for k, r in enumerate(g):
            out_cells.append((r, x * S, y0 + (hint_step if hint else step) * k + ((step - hint_step) * 0 if hint else 0)))
    return out_cells, xs
full_y, status_y = 205 * S + title_h + S // 4, 185 * S + title_h + S // 4
full_cells, full_x = cells([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 14, 18], [None, 10, 11, 16], [12, 13, 15]], full_y, 4)
status_cells, status_x = cells([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 18], [None, 15]], status_y, 3)   # icons only: no name rows or readouts
assert full_y + 3 * step + height <= 240 * S and status_y + 2 * step + height <= 216 * S
hide_x = 8 * S + extent(full_legend_title, 0) + 4 * S   # [~] HIDE right after the title
out += ['static const short ov_full_cells[%d][3]={%s};' % (len(full_cells), ','.join('{%d,%d,%d}' % c for c in full_cells)),
        'static const short ov_status_cells[%d][3]={%s};' % (len(status_cells), ','.join('{%d,%d,%d}' % c for c in status_cells)),
        f'#define OV_FULL_CELLS {len(full_cells)}', f'#define OV_STATUS_CELLS {len(status_cells)}', f'#define OV_HIDE_X {hide_x}']
print('legend geometry', full_x, full_y, status_x, status_y, step)
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
# HD-off notice: drawn at 1 texel = 1 PSX pixel, because with Classic REbirth's HD loader off (or Retro Mode on) the x8 overlay
# textures cannot be sampled and every other overlay raster would be unreadable. Short English text (two lines), 256 x 32.
NOTICE_LINES = ('HD TEXTURES OFF - MAP TEXT IS UNREADABLE', 'Enable HDLoader / disable RetroMode (REbirth)')
_nf = ImageFont.truetype(FONT, 9, index=FACE)
_ni = Image.new('L', (256, 32))
_nd = ImageDraw.Draw(_ni)
_edge, _fill = Image.new('L', (256, 32)), Image.new('L', (256, 32))
for _k, _t in enumerate(NOTICE_LINES):
    ImageDraw.Draw(_edge).text((2, 2 + 12 * _k), _t, font=_nf, fill=255, stroke_width=1, stroke_fill=255)
    ImageDraw.Draw(_fill).text((2, 2 + 12 * _k), _t, font=_nf, fill=255)
_ni.paste(BLACK, mask=_edge.point(lambda v: 255 if v >= 96 else 0)); _ni.paste(PURE, mask=_fill.point(lambda v: 255 if v >= 110 else 0))
assert max(_edge.getbbox()[2], _fill.getbbox()[2]) <= 254, 'notice text wider than its 256 texel raster'
_np = list(_ni.getdata())
out.append('static const unsigned char ov_notice_pixels[4096]={' + ','.join(str(_np[i] | (_np[i + 1] << 4)) for i in range(0, 256 * 32, 2)) + '};')
_ni.resize((1024, 128), Image.NEAREST).convert('P').save(ROOT / 'local/candidate-8/hd-notice-x4.png') if (ROOT / 'local/candidate-8').is_dir() else None
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
out.append('typedef struct { unsigned char kind,page,stage,slot,flagtype,chars; unsigned short flag; short icon; short ico[3][2]; OvLabel lab[3][2]; unsigned short guard[2]; unsigned char side, tstage, tslot; short cover[3]; unsigned char era; short hd; } OvMarker;')
out.append(f'#define OV_MARKER_COUNT {len(markers)}')
def lab(m, vi, lang):
    return m.get('lab', {}).get((vi, lang), (-1, 0, 0))
out.append('static const OvMarker ov_markers[]={' + ','.join(
    f"{{{m['kind']},{m['page']},{m['stage']},{m['slot']},{m['flagtype']},{m['chars']},{m['flag']},{m['icon']},"
    "{" + ','.join('{%d,%d}' % m.get('ico', {}).get(v, (0, 0)) for v in range(3)) + "}," +
    "{" + ','.join('{' + ','.join('{%d,%d,%d}' % lab(m, vi, lang) for lang in ('en', 'ko')) + '}' for vi in range(3)) + "}," + "{%d,%d}" % tuple(m.get('guard', (0xFFFF, 0xFFFF))) + ",%d,%d,%d,{%d,%d,%d},%d,%d}" % ((m.get('side', 0),) + tuple(m.get('target', (0, 0))) + tuple(m.get('cover', {}).get(v, -1) for v in range(3)) + (m.get('era', 0), m.get('hd_bid', -1)))
    for m in markers) + '};')
# leader lines of room names placed outside their room (texels, same spaces as the labels)
lines = [(k, vi, li, *m['lines'][(vi, lang)]) for k, m in enumerate(markers) for vi in range(3) for li, lang in enumerate(('en', 'ko'))
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
    iw, ih = bitmaps[HD_BOX1 if 'hd_bid' in m else m['icon']][:2]   # the full-map layout used the HD icon box
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
# Room names are exempt (RE0 rule: drawn first, nothing avoids them); the lock variants of one door (side 3 / 1 / 2) and
# markers hidden under a key item ('cover') are never on screen together.
def _covis(a, b):
    if a is b or not a['chars'] & b['chars'] or a.get('centre') or b.get('centre') or 1 in a.get('cover', {}) or 1 in b.get('cover', {}):
        return False
    return not (a['kind'] == b['kind'] == KIND['lock'] and a['flag'] == b['flag'] and a.get('side') != b.get('side'))
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
                (ix, iy), (iw, ih) = b['ico'][1], bitmaps[HD_BOX1 if 'hd_bid' in b else b['icon']][:2]
                ow = max(0, min(xa + wa, ix + iw) - max(xa, ix)) * max(0, min(ya + ha, iy + ih) - max(ya, iy))
                if ow > iw * ih / 2:
                    overlaps.append((lang, page, 'name/icon', (a['kind'], b['kind']), (xa // S, ya // S)))
print('fullscreen overlaps (co-visible):', len(overlaps))
for o in overlaps:
    print('  ', o)
