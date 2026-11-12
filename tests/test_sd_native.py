"""SD mode through the real Biohazard.exe image (unicorn): mode selection, what is drawn, caching, zoom clipping, ignored keys.

Run: RE1_GAME_DIR=<game> .venv/bin/python tests/test_sd_native.py
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests')); sys.path.insert(0, str(ROOT / 'tools'))
from sd_emu import boot
import build_sd as B

hdr = (ROOT / 'src/sd_assets.h').read_text()
icon_px = [int(v) for v in re.search(r'sd_icon_px\[\d+\] = \{([\d,]+)\}', hdr)[1].split(',')]
icons = [tuple(map(int, m)) for m in re.findall(r'\{(\d+),(\d+),(\d+)\}', re.search(r'sd_icons\[\] = \{(.*?)\};', hdr, re.S)[1])]
marks = re.findall(r'\{(\d+),\{\{(-?\d+),(-?\d+)\},\{(-?\d+),(-?\d+)\},\{(-?\d+),(-?\d+)\}\},\{(-?\d+),(-?\d+),(-?\d+)\}\}', re.search(r'sd_marks\[\] = \{(.*?)\};\ntypedef', hdr, re.S)[1])
marks = [dict(icon=int(m[0]), pos=[(int(m[1]), int(m[2])), (int(m[3]), int(m[4])), (int(m[5]), int(m[6]))], cover=list(map(int, m[7:]))) for m in marks]
sd = json.loads((ROOT / 'build/sd-markers.json').read_text())
ms = sd['markers']
assert len(marks) == len(ms)
PAL = list(B.PAL.values())
rgb = lambda c: ((c[0] >> 3) << 3 | (c[0] >> 3) >> 2, (c[1] >> 3) << 3 | (c[1] >> 3) >> 2, (c[2] >> 3) << 3 | (c[2] >> 3) >> 2)


def icon_at(img, mark, view, dx=0, dy=0):
    """True when the marker's SD icon is on the image at its position (cream is the Rooms colour: not compared)."""
    off, w, h = icons[mark['icon']]
    x0, y0 = mark['pos'][view][0] + dx, mark['pos'][view][1] + dy
    for j in range(h):
        for i in range(w):
            v = icon_px[off + j * w + i]
            if v == 0 or PAL[v] is None: continue
            X, Y = x0 + i, y0 + j
            if not (0 <= X < 320 and 0 <= Y < 240) or img[Y][X][:3] != rgb(PAL[v]): return False
    return True


# 1) mode selection ------------------------------------------------------------------------------------------------------
def draws_notice(sp): return any(s['wh'] == (256, 32) for s in sp)
for label, kw, want_sd in (('HDLoader=0 (Auto)', dict(HDLoader=0), True), ('RetroMode=1 (Auto)', dict(RetroMode=1), True),
                           ('HDLoader missing (Auto)', dict(HDLoader=None), True), ('HD on (Auto)', dict(HDLoader=1), False),
                           ('DisplayMode=SD, HD on', dict(HDLoader=1, DisplayMode='SD'), True),
                           ('DisplayMode=HD, HD off', dict(HDLoader=0, DisplayMode='HD'), False)):
    emu = boot(**kw)
    emu.scene(0, visited=range(124)); emu.poke('ov_fullscreen', 1)
    up, sp = emu.draw(); up, sp = emu.draw()
    sd_like = bool(sp) and not draws_notice(sp) and len(sp) < 14
    if label.startswith('DisplayMode=HD'): assert draws_notice(sp), label
    elif want_sd: assert sd_like, (label, len(sp))
    else: assert len(sp) > 14 or not sd_like, (label, len(sp))
    print('mode', label, '->', 'SD' if sd_like else 'notice' if draws_notice(sp) else 'HD', f'({len(sp)} sprites)')

# 2) full-screen map, page 0, Chris, everything on and every room revealed -------------------------------------------------
emu = boot(HDLoader=0)
img, sp = emu.render(0, 1)
assert len(sp) <= 12 and all(s['n'] == 0xfffffffe and s['count'] == 1 for s in sp), len(sp)
seen = dict(ok=0, bad=[], skipped=0)
page = [i for i, m in enumerate(ms) if m['page'] == 0 and marks[i]['icon'] != 0xFFFF and m['chars'] & 1 and not (m['kind'] == 2 and m['side'] in (1, 2))]
boxes = {i: (marks[i]['pos'][1][0], marks[i]['pos'][1][1], marks[i]['pos'][1][0] + icons[marks[i]['icon']][1], marks[i]['pos'][1][1] + icons[marks[i]['icon']][2]) for i in page}
overlap = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
rooms_px = {(x, y) for y in range(240) for x in range(320) if img[y][x][3]}
for i in page:
    m, k = ms[i], marks[i]
    if m['kind'] == 7 or k['cover'][1] >= 0: seen['skipped'] += 1; continue
    if icon_at(img, k, 1): seen['ok'] += 1
    elif any(j != i and overlap(boxes[i], boxes[j]) for j in page): seen['skipped'] += 1   # another icon (or a name) lies over it
    else: seen['bad'].append((i, m['kind'], m['name']))   # hidden by its own conditions (placement guards of event items, era 2 = mansion revisit) or a bug
print('full map page 0: icons exact', seen['ok'], 'overlapped/enemy/covered', seen['skipped'], 'not drawn', seen['bad'])
assert seen['ok'] > 40, seen   # the rest: enemies, covered, or under another icon
assert len(seen['bad']) <= 5, seen['bad']

# 3) the legend and the title are drawn, the opaque band is on the bottom, room names exist --------------------------------
band = [(x, y) for y in range(206, 240) for x in range(320) if img[y][x][3]]
assert len(band) > 1500, len(band)
assert sum(1 for y in range(8, 20) for x in range(8, 120) if img[y][x][3]) > 50, 'page title'

# 4) unchanged frames upload nothing; a toggle changes only what it must ------------------------------------------------------
up, sp = emu.draw()
assert not up, 'an unchanged SD frame uploaded textures'
up, sp = emu.press(0x31) or (None, None)   # key 1: rooms off
img_off, _ = emu.render(0, 1)
n_off = sum(1 for y in range(204) for x in range(320) if img_off[y][x][3])
n_on = sum(1 for y in range(204) for x in range(320) if img[y][x][3])
assert n_off < n_on, (n_off, n_on)
emu.press(0x31)

# 5) Korean ------------------------------------------------------------------------------------------------------------------
img_ko, _ = emu.render(0, 1, lang='ko')
assert img_ko != img and sum(1 for y in range(204) for x in range(320) if img_ko[y][x][3]) > 500
emu.render(0, 1, lang='en')

# 6) size / opacity keys do nothing in SD ----------------------------------------------------------------------------------------
before, _ = emu.render(0, 1)
emu.press(0xBD); emu.press(0xBB); emu.press(0xDB)    # - + [
after, _ = emu.render(0, 1)
assert before == after, 'NameSize / NameOpacity changed the SD map'

# 7) zoom: nothing outside the window, no half icon, names inside the screen ----------------------------------------------------
bottom = 204   # the zoom window ends where the legend band starts
for pan in ((96, 100), (0, 0), (192, 200), (-80, 0)):
    z, sp = emu.render(0, 2, pan=pan)
    names = sum(1 for y in range(4, bottom - 2) for x in range(320) if z[y][x][3])
    assert names > 100, (pan, names)
    k_ok = 0
    for i in page:
        m, k = ms[i], marks[i]
        if k['cover'][2] >= 0: continue
        w, h = icons[k['icon']][1:]
        x, y = k['pos'][2][0] - pan[0], k['pos'][2][1] - pan[1]
        inside = x >= 0 and y >= 0 and x + w <= 320 and y + h <= bottom
        if inside and m['kind'] in (2, 3, 5) and icon_at(z, k, 2, -pan[0], -pan[1]): k_ok += 1
        if not inside and m['kind'] in (2, 3, 5):   # a marker the edge would slice is left out whole: its top-left texel is not drawn
            off = icons[k['icon']][0]
            assert not (0 <= x < 320 and 0 <= y < bottom and z[y][x][3] and icon_px[off] and icon_at(z, k, 2, -pan[0], -pan[1])), ('sliced icon', i, pan)
    print('zoom pan', pan, 'overlay texels', names, 'exact icons', k_ok)

# 8) names are part of the map (user 2026-11-13): panning moves every map-layer texel by exactly the pan, nothing is re-placed
a, _ = emu.render(0, 2, pan=(96, 100))
b, _ = emu.render(0, 2, pan=(104, 100))
same = tot = 0
for y in range(40, 190):
    for x in range(40, 300):
        if a[y][x][3] or b[y][x - 8][3]:
            tot += 1; same += a[y][x] == b[y][x - 8]
assert tot > 300 and same >= tot * 0.995, (same, tot)
d, _ = emu.render(0, 2, pan=(96, 108))
same = tot = 0
for y in range(40, 186):
    for x in range(40, 300):
        if a[y + 8][x][3] or d[y][x][3]:
            tot += 1; same += a[y + 8][x] == d[y][x]
assert tot > 300 and same >= tot * 0.995, ('vertical pan', same, tot)
print('zoom names scroll with the map: horizontal and vertical pan move every texel exactly', same, tot)

# 9) crowded pages (Mansion 1F / 2F): names on the zoom view only; other pages keep names on the 1x full-screen view
def names_texels(page, view):
    on, _ = emu.render(page, view)
    emu.press(0x31)
    off, _ = emu.render(page, view)
    emu.press(0x31)
    return sum(1 for y in range(204) for x in range(320) if on[y][x][3]) - sum(1 for y in range(204) for x in range(320) if off[y][x][3])
n0, n5 = names_texels(0, 1), names_texels(5, 1)
assert n5 > 400 and n0 < 250, ('names on the 1x view: page 5', n5, 'page 0 (crowded)', n0)
assert names_texels(0, 2) > 800, 'zoom view of a crowded page shows names'
print('1x full-screen names: crowded page', n0, 'texels (room icons only), page 5', n5)

# 10) floor / area arrows: drawn on the 1x full-screen map when the page has neighbours, not on the zoom view; green with a black rim
def green(img, x0, y0, w, h): return sum(1 for y in range(y0, y0 + h) for x in range(x0, x0 + w) if img[y][x][3] and img[y][x][1] > 160 and img[y][x][0] < 120)
img, sp = emu.render(0, 1, mapstate={12: 3, 13: 2})
assert green(img, 154, 2, 12, 9) > 20 and green(img, 154, 194, 12, 9) > 20 and green(img, 5, 114, 9, 12) > 20, 'floor / area arrows missing'
assert any(s['flags'] == 0x50000000 for s in sp), 'arrows are drawn semi-transparent (blinking) as in HD'
img, _ = emu.render(0, 2, mapstate={12: 3, 13: 2})
assert green(img, 154, 2, 12, 9) < 5, 'no floor arrows on the zoom view (as HD)'
print('floor / area arrows ok')
print('SD native ok')
