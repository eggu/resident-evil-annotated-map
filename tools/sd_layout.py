"""SD room-name layout for every map page, view and language -> data/sd-layout.json (user decisions 2026-11-12, common/SD-MAP-PORTING.md).

Views: 1 = full-screen map (2 screen px per map cell, screen coordinates: names avoid the title, the four arrows, the legend band
and 6 px of screen edge), 2 = zoom canvas (4 px per map cell, map-space coordinates; the runtime pulls cut names inside the screen).
The status-screen map shows icons only. Inputs: build/sd-markers.json (tools/gen_assets.py), data/map_rooms.json, the game's MAP*.TIM
(RE1_GAME_DIR) and fonts/Galmuri9.ttf. Slow (minutes): run when names, rooms, icons or the rules change, then tools/build_sd.py.

    RE1_GAME_DIR=<game> .venv/bin/python tools/sd_layout.py [page ...]
"""
import json, os, struct, sys
from pathlib import Path
import numpy as np
from PIL import ImageFont
ROOT = Path(__file__).resolve().parents[1]
exec((ROOT / 'tools/sd_place.py').read_text())   # place(), abbr(), split(), Sat

FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
LINE_H = 11            # 10 px Galmuri9 + 1 px shadow
LEADER_INSET = 3       # leaders start this far inside their room
SCREEN_W, SCREEN_H = 320, 240
LEGEND_TOP = 204       # the legend band starts here on the full-screen map
VIEWS = {1: dict(z=2, W=SCREEN_W, H=SCREEN_H), 2: dict(z=4, W=512, H=400)}
# Screen furniture of the full-screen map in SD (x, y, w, h): page title, the four floor/area arrows (they appear only when the
# page has a neighbour, but names keep clear of them always), and 6 px screen edges. src/sd_draw.h draws them in the same places.
HUD = [(6, 6, 130, 26), (153, 1, 14, 11), (153, 193, 14, 11), (4, 113, 11, 14), (305, 113, 11, 14),
       (0, 0, 320, 6), (0, 0, 6, 240), (314, 0, 6, 240), (0, LEGEND_TOP, 320, 240 - LEGEND_TOP)]


def size_of(text):
    lines = text.split('\n')
    return max(int(FONT.getlength(l)) for l in lines) + 1, LINE_H * len(lines)


def edge_mids(own):
    """Middle pixel of every straight edge run (3 px or longer) of the room, with its outward direction. A side with no
    such run (a diamond-shaped room, a stair stub) still offers the middle of its longest run."""
    out = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        key = (lambda c: (c[1], c[0])) if dy else (lambda c: (c[0], c[1]))
        edge = sorted((c for c in own if (c[0] + dx, c[1] + dy) not in own), key=key)
        run, runs = [], []
        for c in edge + [None]:
            if c is not None and run and key(c)[0] == key(run[-1])[0] and key(c)[1] == key(run[-1])[1] + 1:
                run.append(c); continue
            if run: runs.append(run)
            run = [c] if c is not None else []
        long = [r for r in runs if len(r) >= 3] or ([max(runs, key=len)] if runs else [])
        for r in long:   # start a little inside the room (user 2026-11-12), as far as the room allows
            x, y = r[len(r) // 2]
            k = 0
            while k < LEADER_INSET and (x - dx * (k + 1), y - dy * (k + 1)) in own: k += 1
            out.append(((x - dx * k, y - dy * k), (dx, dy)))
    return out


def anchor_part(cells, ax, ay):
    """The connected piece of a room's map cells that holds its anchor (a name never goes to a detached stray piece)."""
    left, parts = set(cells), []
    while left:
        seed = left.pop(); part, stack = {seed}, [seed]
        while stack:
            x, y = stack.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in left:
                    left.remove(n); part.add(n); stack.append(n)
        parts.append(part)
    return min(parts, key=lambda q: min((x - ax) ** 2 + (y - ay) ** 2 for x, y in q))


def map_pixels(page_file):
    tim = (Path(os.environ['RE1_GAME_DIR']) / 'jpn/Item_m2' / page_file).read_bytes()
    at = 8 + struct.unpack_from('<I', tim, 8)[0]
    return tim[at + 12:at + 12 + 128 * 100]


def icon_spots(markers, page, view, origin):
    """Cells under the 9x9 icons that can appear on this page (enemies are exempt: names may cover them)."""
    z, (ox, oy) = VIEWS[view]['z'], origin
    out = set()
    for m in markers:
        if m['page'] != page or m['kind'] == 7 or (m['kind'] == 1 and m['centre']) or m['side'] in (1, 2): continue
        cx, cy = ox + round(m['x'] * z), oy + round(m['y'] * z)
        out |= {(cx + i, cy + j) for i in range(-4, 5) for j in range(-4, 5)}
    return out


def page_layout(page, view, lang, data):
    markers, rooms_json, page_file, origin = data['markers'], data['rooms'], data['file'], data['origin']
    z, W, H = VIEWS[view]['z'], VIEWS[view]['W'], VIEWS[view]['H']
    ox, oy = origin if view == 1 else (0, 0)
    px = map_pixels(page_file)
    global RUN, CROSS_LEADERS
    RUN = z + 1   # a wall is z cells thick: crossing it is fine, running along it for z + 1 is not
    def scaled(cs): return {(ox + x * z + i, oy + y * z + j) for x, y in cs for i in range(z) for j in range(z)}
    pix = scaled((i % 128, i // 128) for i, v in enumerate(px) if v == 7 or v >= 13)
    grey = scaled((i % 128, i // 128) for i, v in enumerate(px) if v == 7)
    cells_of = {r['slot']: scaled(map(tuple, r['mask'])) for r in rooms_json['rooms']}
    named = [m for m in markers if m['page'] == page and m['centre']]
    rows, text_of = [], {}
    for m in named:
        part = anchor_part(map(tuple, [c for r in rooms_json['rooms'] if r['slot'] == m['slot'] for c in r['mask']]), int(m['x']), int(m['y']))
        rows.append(dict(key=m['slot'], name=m['text'][lang], cells=scaled(part)))
        text_of[m['slot']] = m['text']['en']
    occ = {c: r['key'] for r in rows for c in r['cells']}
    other = {c for s, cs in cells_of.items() if s not in {r['key'] for r in rows} for c in cs}
    hud = {(x + i, y + j) for x, y, w, h in HUD for j in range(h) for i in range(w)} if view == 1 else set()
    bc = {(x + i, y + j) for x, y in pix | icon_spots(markers, page, view, (ox, oy)) for j in (-1, 0, 1) for i in (-1, 0, 1)
          if 0 <= x + i < W and 0 <= y + j < H} | hud
    blocked = Sat(bc, (H + 2, W + 2))
    def run(rows_, refine):
        return place(rows_, size_of, occ, grey, blocked, W, H, edge_mids, refine=refine, other=other)
    placed = run(rows, lang == 'en')
    forced = {k for k, o in placed.items() if o.get('forced')}
    if forced and lang == 'en':   # full names first; abbreviate only what found no place
        for r in rows:
            if r['key'] in forced: r['name'] = abbr(text_of[r['key']])
        placed = run(rows, True)
        if any(o.get('forced') for o in placed.values()):   # still crowded: every name abbreviated, keep the better result
            for r in rows: r['name'] = abbr(text_of[r['key']])
            again = run(rows, True)
            if sum(o.get('forced', False) for o in again.values()) < sum(o.get('forced', False) for o in placed.values()):
                placed = again
    def fallback(rows, placed):
        """Crowded page: fallback passes with the same leader rules except that a leader may run along walls and cross another
        leader. loose 1: the name may lie over another room's floor (never over icons, the HUD or a placed name); 2: also over
        common-item and file icons; 3: also over padlocks. Key items, puzzles, events and save points are never covered."""
        global RUN, CROSS_LEADERS
        for tier, skip in ((1, ()), (2, (4, 6)), (3, (2, 4, 6))):
            stuck = [r for r in rows if placed[r['key']].get('forced')]
            if not stuck: break
            if lang == 'en':
                for r in stuck: r['name'] = abbr2(text_of[r['key']])
            light = Sat({(x + i, y + j) for x, y in icon_spots([m for m in markers if m['kind'] not in skip], page, view, (ox, oy)) for j in (-1, 0, 1) for i in (-1, 0, 1)
                         if 0 <= x + i < W and 0 <= y + j < H} | hud, (H + 2, W + 2))
            fixed = [(o['box'], o['cells']) for o in placed.values() if o.get('box')]
            keys = {r['key'] for r in stuck}
            rest = other | {c for c, k in occ.items() if k not in keys}
            RUN, CROSS_LEADERS = 99, True
            again = place(stuck, size_of, {c: k for c, k in occ.items() if k in keys}, grey, light, W, H, edge_mids, refine=False, fixed=fixed, other=rest)
            RUN, CROSS_LEADERS = z + 1, False
            for k, o in again.items():
                if not o.get('forced'): o['loose'] = tier; placed[k] = o
        return placed
    placed = fallback(rows, placed)
    if lang == 'en' and any(o.get('forced') for o in placed.values()):   # still crowded: every name in its shortest form from the start
        for r in rows: r['name'] = abbr2(text_of[r['key']])
        again = fallback(rows, run(rows, True))
        if sum(bool(o.get('forced')) for o in again.values()) < sum(bool(o.get('forced')) for o in placed.values()): placed = again
    print(f'page {page} view {view} {lang}: {len(placed)} names, forced {[o["text"] for o in placed.values() if o.get("forced")]}', flush=True)
    out = {}
    for slot, o in placed.items():
        w, h = size_of(o['text'])
        out[str(slot)] = dict(
            text=o['text'], x=o['box'][0] if o.get('box') else round(o['x'] - w / 2), y=o['box'][1] if o.get('box') else round(o['y'] - h / 2),
            leader=[[x, y] for x, y in (o.get('poly') or [])], forced=bool(o.get('forced')), loose=o.get('loose', 0))
    return out


def _job(args):
    page, view, lang = args
    sd = json.loads((ROOT / 'build/sd-markers.json').read_text())
    rooms = json.loads((ROOT / 'data/map_rooms.json').read_text())
    pg = rooms['pages'][page]
    data = dict(markers=sd['markers'], rooms=pg, file=pg['file'], origin=sd['origin'][page])
    return page, view, lang, page_layout(page, view, lang, data)


def main():
    """Every (page, view, language) is independent: run them in parallel processes, English (the slow one) first."""
    from concurrent.futures import ProcessPoolExecutor
    pages = sorted({m['page'] for m in json.loads((ROOT / 'build/sd-markers.json').read_text())['markers'] if m['centre']})
    views = [int(a[7:]) for a in sys.argv[1:] if a.startswith('--view=')] or [2, 1]
    only = [int(a) for a in sys.argv[1:] if not a.startswith('--')]
    path = ROOT / 'data/sd-layout.json'
    result = json.loads(path.read_text()) if path.exists() and (only or views != [2, 1]) else {}
    jobs = [(p, v, l) for l in ('en', 'ko') for v in views for p in (only or pages)]
    for p in only or pages:
        for v in views: result.setdefault(str(p), {})[str(v)] = {}
    with ProcessPoolExecutor() as pool:
        for page, view, lang, out in pool.map(_job, jobs):
            for slot, by in out.items(): result[str(page)].setdefault(str(view), {}).setdefault(slot, {})[lang] = by
    path.write_text(json.dumps(result, ensure_ascii=False, indent=0, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
