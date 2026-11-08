"""HD-off notice: with config.ini [DLL] HDLoader=0 or RetroMode=1 the overlay draws only a 1:1 English notice (REbirth's HD
texture path is what the x8 overlay textures need). Runs the test_native.py install prefix once per config.ini state.

Run: RE1_GAME_DIR=<game> .venv/bin/python tests/test_hd_off.py
"""
import struct, subprocess, sys, textwrap
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CHILD = textwrap.dedent('''
    import json, struct, sys
    from pathlib import Path
    ROOT = Path(%r)
    src = (ROOT / 'tests/test_native.py').read_text().split('# 1) unvisited', 1)[0]
    src = src.replace("Path(__file__).resolve().parent.parent", "Path(%r)")
    src = src.replace("UploadBudget=200, HdIcons=0)", "UploadBudget=200, HdIcons=0, %s)")
    g = {'__name__': 'child', '__file__': str(ROOT / 'tests/test_native.py')}
    exec(compile(src, 'prefix', 'exec'), g)
    scene, draw = g['scene'], g['draw']
    scene(0, visited=list(range(124)))
    up, sp = draw()
    notice = [s for s in sp if s['wh'] == (256, 32)]
    tex = g['uploads'][-1] if up else b''
    rows_lit = [y for y in range(256) if any(tex[64 + y * 128:64 + (y + 1) * 128])] if up else []
    print(json.dumps(dict(sprites=len(sp), uploads=len(up), notice=len(notice), uv=[s['uv'] for s in notice], rows_lit=[min(rows_lit), max(rows_lit)] if rows_lit else None)))
''')
def run(ini):
    code = CHILD % (str(ROOT), str(ROOT), ini)
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr[-1500:]
    import json
    return json.loads(out.stdout.strip().splitlines()[-1])
for ini in ('HDLoader=0', 'RetroMode=1'):
    r = run(ini)
    assert r['notice'] == 1 and r['sprites'] == 1 and r['uploads'] == 1, (ini, r)
    assert r['uv'] == [[0, 0]] and r['rows_lit'] and r['rows_lit'][1] < 32, (ini, r)
ok = run('HDLoader=1, RetroMode=0')
assert ok['notice'] == 0 and ok['sprites'] > 5, ok
print('HD-off notice: HDLoader=0 and RetroMode=1 draw only the 1:1 notice (1 texture, 1 sprite, text in rows 0..31); HD on draws the overlay ok')
