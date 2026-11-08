"""Offline renders of the built DLL: run it against the real EXE in the test harness (tests/test_native.py) and paint every
submitted sprite with its uploaded CLUT. Alpha blending, REbirth upscaling and the game's own HUD are not reproduced.

Usage: RE1_GAME_DIR=<game> .venv/bin/python tools/render_offline.py <out dir> [page ...]   (default pages 0 1: Mansion 1F/2F)
Every category (events included), item names, enemies and scope 'all rooms' are on; nothing picked up, nothing killed.
"""
import re, struct, sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'tests/test_native.py').read_text()
prefix = source.split('# 1) unvisited', 1)[0]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
pages = [int(p) for p in sys.argv[2:]] or [0, 1]
NAMES = ['mansion-1f', 'mansion-2f', 'mansion-b1', 'courtyard', 'caves', 'guardhouse-1f', 'guardhouse-b1', 'lab-b1', 'lab-b2', 'lab-b3', 'lab-b4']
for lang in ('en', 'ko'):
    ini = dict(Version=5, All=1, Rooms=1, Locks=1, KeyItems=1, Documents=1, Puzzles=1, Events=1, CommonItems=1, Enemies=1, ItemNames=1,
               Scope=3, Language=lang)
    g = dict(__file__=str(ROOT / 'tests/test_native.py'))
    code = re.sub(r'^state = dict\(keys=set\(\), ini=.*?, written=\{\}\)$', f'state = dict(keys=set(), ini={dict(ini, UploadBudget=200, HdIcons=0)!r}, written={{}})', prefix, flags=re.M)
    exec(compile(code, 'render', 'exec'), g)
    exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], g)
    u, S, W, H = g['u'], g['S'], g['WIDTH'], 240 * g['S']
    for page in pages:
        u.mem_write(g['exports']['ov_fullscreen'], struct.pack('<i', 1))
        g['scene'](page); g['state']['keys'] = set(); g['draw']()
        img = Image.new('RGB', (W, H)); p = img.load()
        by_tex = {0x5000 + i + 1: t for i, t in enumerate(g['uploads'])}
        for k, s in enumerate(g['sprites_now']):
            t = by_tex[s['tex']]
            pal = struct.unpack('<16H', t[20:52]); px = t[64:]; tw = struct.unpack_from('<H', t, 60)[0] * 4
            f = (2 if k == 2 else 1) if k in (2, 3) else 1
            for y in range(s['wh'][1] * S * f):
                for x in range(s['wh'][0] * S * f):
                    sx, sy = (s['uv'][0] + x // (S * f), s['uv'][1] + y // (S * f)) if k < 4 else (s['uv'][0] * S + x, s['uv'][1] * S + y)
                    v = (px[sy * (tw // 2) + sx // 2] >> ((sx & 1) * 4)) & 15
                    X, Y = s['x'] * S + x, s['y'] * S + y
                    if v and pal[v] & 0x7fff and 0 <= X < W and 0 <= Y < H:
                        c = pal[v]; p[X, Y] = ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
        out = OUT / f'{NAMES[page]}-{lang}.png'
        img.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out)
        print(out)
