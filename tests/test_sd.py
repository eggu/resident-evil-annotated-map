"""SD mode data checks: the layout (data/sd-layout.json) and the atlas (src/sd_assets.h, tools/build_sd.py).

Run: RE1_GAME_DIR=<game> .venv/bin/python tests/test_sd.py
Layout: every named room has a name in both views and languages; boxes stay on screen, off the HUD, off every map pixel and off the
(non-enemy) icons, keep clear of each other; each leader starts inside its room and ends 1 px from its name.
Atlas: every palette index fits 4 bits, the locks of one page are told apart, text boxes match the layout's sizes.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import sd_layout as L, build_sd as B

sd = json.loads((ROOT / 'build/sd-markers.json').read_text())
layout = json.loads((ROOT / 'data/sd-layout.json').read_text())
rooms = json.loads((ROOT / 'data/map_rooms.json').read_text())
ms = sd['markers']
named = [m for m in ms if m['centre']]
problems = []
forced, loose = [], []


def box(o):
    w, h = L.size_of(o['text'])
    return o['x'], o['y'], o['x'] + w, o['y'] + h


def hit(a, b, pad=0):
    return a[0] - pad < b[2] and b[0] - pad < a[2] and a[1] - pad < b[3] and b[1] - pad < a[3]


for page in sorted({m['page'] for m in named}):
    pg = rooms['pages'][page]
    px = L.map_pixels(pg['file'])
    for view, spec in L.VIEWS.items():
        z, W, H = spec['z'], spec['W'], spec['H']
        mx, my = L.MARGIN if view == 2 else (0, 0)   # zoom names are stored in map coordinates and may lie in the pan margin
        crowded = sum(1 for m in named if m['page'] == page) >= L.CROWDED
        if view == 1 and crowded:
            assert not layout[str(page)].get('1'), ('crowded page has full-screen names', page)
            continue
        ox, oy = sd['origin'][page] if view == 1 else (0, 0)
        scale = lambda cs: {(ox + x * z + i, oy + y * z + j) for x, y in cs for i in range(z) for j in range(z)}
        pix = scale((i % 128, i // 128) for i, v in enumerate(px) if v == 7 or v >= 13)
        cells = {r['slot']: scale(map(tuple, r['mask'])) for r in pg['rooms']}
        icons = [(ox + round(m['x'] * z) - 4, oy + round(m['y'] * z) - 4, m['kind']) for m in ms
                 if m['page'] == page and m['kind'] != 7 and not m['centre'] and m['side'] not in (1, 2)]
        hud = [(x, y, x + w, y + h) for x, y, w, h in L.HUD] if view == 1 else []
        for lang in ('en', 'ko'):
            placed = []
            for m in (m for m in named if m['page'] == page):
                o = layout[str(page)][str(view)].get(str(m['slot']), {}).get(lang)   # (the check below also covers inside names)
                tag = (page, view, lang, m['text']['en'])
                if o is None:
                    problems.append(('no layout', tag)); continue
                b = box(o)
                if o['forced']: forced.append(tag)
                if b[0] < -mx or b[1] < -my or b[2] > W - mx or b[3] > (L.LEGEND_TOP if view == 1 else H - my): problems.append(('name off screen', tag, b))
                if o.get('inside'):
                    if o['leader'] or not all((x, y) in cells[m['slot']] for x in range(b[0], b[2]) for y in range(b[1], b[3])): problems.append(('inside name not on its room', tag))
                    if view != 2: problems.append(('inside name on the 1x view', tag))
                if any(hit(b, h) for h in hud): problems.append(('name on the HUD', tag, b))
                if o.get('loose'): loose.append(tag + (o['loose'],))
                elif not o.get('inside') and any(b[0] <= x < b[2] and b[1] <= y < b[3] for x, y in pix): problems.append(('name over the map', tag))
                covers = {k for x, y, k in icons if hit(b, (x, y, x + 9, y + 9))}
                allowed = {0: set(), 1: set(), 2: {4, 6}, 3: {2, 4, 6}}[o.get('loose', 0)]
                if covers - allowed: problems.append(('name over an icon', tag, covers))
                for other_tag, other in placed:
                    if hit(b, other, 1): problems.append(('names closer than 2 px', tag, other_tag))
                placed.append((tag, b))
                if o['leader'] and not o.get('inside'):
                    sx, sy = o['leader'][0]; ex, ey = o['leader'][-1]
                    if (sx, sy) not in cells[m['slot']]: problems.append(('leader starts outside its room', tag, (sx, sy)))
                    gap = max(b[0] - ex, ex - (b[2] - 1), b[1] - ey, ey - (b[3] - 1))
                    if gap != 1: problems.append(('leader end not 1 px from the name', tag, gap))
                    if len(o['leader']) > 3: problems.append(('leader with more than one bend', tag))
# no name was forced onto its room (nowhere free): they would sit on the map
# a crowded English full-screen page may leave one or two names centred on their room (no leader): allowed, reported
if any(t[1] != 1 or t[2] != 'en' for t in forced) or len(forced) > 3: problems.append(('names with no free place', forced))

# atlas ---------------------------------------------------------------------------------------------------------------------
assert max(max(B.icon_image(p).flat) for p in list(B.ICONS.values()) + list(B.LOCKS.values())) < 16
assert len(B.PAL) == 16
for a in [B.player_arrow(k) for k in range(16)] + [B.triangle(12, 9, [(6, 0), (11, 8), (0, 8)])]:
    assert a.max() < 16
for name, art in B.LOCKS.items():
    r = art.split('|')
    assert len(r) == 9 and all(len(x) == 9 for x in r), name
by_art = {}
for name, art in B.LOCKS.items(): by_art.setdefault(art, []).append(name)
assert all(len(v) == 1 for v in by_art.values()), ('two keys share one padlock', [v for v in by_art.values() if len(v) > 1])
# lock markers on one page must differ
for page in range(11):
    keys = {m['name'] for m in ms if m['kind'] == 2 and m['page'] == page and m['side'] in (0, 3)}
    arts = {B.LOCKS[k] for k in keys}
    assert len(arts) == len(keys), ('padlocks of page', page, keys)
unknown = {m['name'] for m in ms if m['kind'] == 2} - set(B.LOCKS)
assert not unknown, ('keys without a padlock', unknown)
items = {m['item'] for m in ms if m['kind'] == 6}
assert items <= set(B.COMMON), ('common items without an SD icon', items - set(B.COMMON))
hdr = (ROOT / 'src/sd_assets.h').read_text()
assert int(re.search(r'SD_ROOM_COUNT (\d+)', hdr)[1]) == len(named)
assert int(re.search(r'static const SdMark sd_marks\[\]', hdr) is not None)
assert hdr.count('{') > 100

if problems:
    for p in problems[:40]: print(p)
    sys.exit(f'{len(problems)} SD layout problems')
print(f'SD layout ok: {len(named)} rooms x 2 views x 2 languages, no name on a key item, puzzle, event or save icon, the HUD or another name; {len(loose)} fallback names; atlas ok')
print('  loose:', loose)
print('  centred on their room (no free place):', forced)
