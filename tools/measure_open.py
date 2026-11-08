"""Open-map cost per ASI build, in the Unicorn harness (tests/test_native.py prefix, real Biohazard.exe).

Usage: RE1_GAME_DIR=<game> .venv/bin/python tools/measure_open.py <asi> [label]
Counts what the game's REbirth HD path pays for: TIM uploads (each one creates an HD texture) and their bytes, Add_sprt
submissions, emulated bytes of mod code executed (UC_HOOK_BLOCK, a CPU proxy). Prints one JSON line.
"""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
asi = Path(sys.argv[1]).resolve()
src = (ROOT / 'tests/test_native.py').read_text().split('# 1) unvisited', 1)[0]
src = src.replace("DLL = ROOT / 'mod_annotated_map/RE1.AnnotatedMap.dll'", f"DLL = Path({str(asi)!r})").replace("Path(__file__).resolve().parent.parent", f"Path({str(ROOT)!r})")
import re
src = re.sub(r'ini=dict\(Rooms=0.*?CommonItems=0[^)]*\)', 'ini=dict(Rooms=1, Locks=1, KeyItems=1, Documents=1, Puzzles=1, CommonItems=1, Enemies=1, ItemNames=1, Scope=3)', src)
g = {'__name__': 'measure', '__file__': str(ROOT / 'tests/test_native.py')}
exec(compile(src, 'test_native_prefix', 'exec'), g)
from unicorn import UC_HOOK_BLOCK
import struct
u = g['u']; DBASE = g['DBASE']; di = g['di']; o = g['o']
cost = [0]
u.hook_add(UC_HOOK_BLOCK, lambda uc, a, s, _: cost.__setitem__(0, cost[0] + s), begin=DBASE, end=DBASE + len(di))
exp_rv = struct.unpack_from('<I', di, o + 96)[0]
nnames, fn_rva, name_rva, ord_rva = struct.unpack_from('<I', di, exp_rv + 24)[0], *struct.unpack_from('<3I', di, exp_rv + 28)
ex = {}
for i in range(nnames):
    nm = di[struct.unpack_from('<I', di, name_rva + 4 * i)[0]:].split(b'\0', 1)[0].decode()
    ex[nm] = DBASE + struct.unpack_from('<I', di, fn_rva + 4 * struct.unpack_from('<H', di, ord_rva + 2 * i)[0])[0]
scene, draw, uploads, sprites = g['scene'], g['draw'], g['uploads'], g['sprites']
state = g['state']
u.mem_write(ex['ov_fullscreen'], struct.pack('<i', 1))

def step(name, fn):
    n_up0, n_sp0, c0 = len(uploads), len(sprites), cost[0]
    fn()
    ups = uploads[n_up0:]
    return dict(step=name, uploads=len(ups), upload_kb=sum(len(x) for x in ups) // 1024, sprites=len(sprites) - n_sp0, cpu_kb=(cost[0] - c0) // 1024)

def settle(fn):
    """Run one frame (fn), then more frames until a frame uploads nothing; report first-frame and total cost."""
    n_up0, c0 = len(uploads), cost[0]
    fn(); first = len(uploads) - n_up0; first_cpu = cost[0] - c0; frames = 1
    while frames < 60:
        before = len(uploads); draw(); frames += 1
        if len(uploads) == before: frames -= 1; break
    return dict(first_frame_uploads=first, first_frame_cpu_kb=first_cpu // 1024, total_uploads=len(uploads) - n_up0,
                upload_kb=sum(len(x) for x in uploads[n_up0:]) // 1024, frames_to_settle=frames)
def pans(fn, n=8):
    n_up0, c0 = len(uploads), cost[0]
    for _ in range(n): fn()
    return dict(uploads=len(uploads) - n_up0, cpu_kb_per_step=(cost[0] - c0) // 1024 // n)

out = []
scene(0, visited=list(range(124)))
out.append(dict(step='open (all rooms visited, everything on)', **settle(draw)))
def reopen():
    u.mem_write(ex['ov_fullscreen'], struct.pack('<i', 0)); draw(); u.mem_write(ex['ov_fullscreen'], struct.pack('<i', 1)); scene(0, visited=list(range(124))); draw()
out.append(dict(step='close + reopen', **settle(reopen)))
if 'ov_zoom' in ex:
    def zoom_on():
        u.mem_write(ex['ov_zoom'], struct.pack('<i', 1)); u.mem_write(g['exports'] if False else ex['ov_pan_x'], struct.pack('<i', 96)); u.mem_write(ex['ov_pan_y'], struct.pack('<i', 112)); g['state']['clock'] = g['state'].get('clock', 0) + 5000
        g['state']['keys'] = {ord('1')}; draw(); g['state']['keys'] = set(); draw()
    out.append(dict(step='zoom 2x on (settings key toggled)', **settle(zoom_on)))
    cur = [96]
    def pan_step():
        cur[0] = (cur[0] + 4) % 190; u.mem_write(ex['ov_pan_x'], struct.pack('<i', cur[0])); draw()
    out.append(dict(step='pan 8 x 4 px (offset only)', **pans(pan_step)))
    out.append(dict(step='pan 8 x 4 px, settled', **settle(lambda: None)))
def crop_estimate():
    """Bytes the first open would upload if every 256x256 tile TIM were cropped to its content bbox in a power-of-two square."""
    tot = full = 0; hist = {}
    for t in uploads[:81]:
        w = struct.unpack_from('<H', t, 60)[0] * 4; h = struct.unpack_from('<H', t, 62)[0]; px = t[64:]; row = w // 2
        xs = [x for y in range(h) for x in range(w) if (px[y * row + x // 2] >> ((x & 1) * 4)) & 15] if False else None
        ys, x0, x1 = [], 255, 0
        for y in range(h):
            r = px[y * row:(y + 1) * row]
            if any(r):
                ys.append(y)
                nz = [i for i, b in enumerate(r) if b]
                x0 = min(x0, nz[0] * 2); x1 = max(x1, nz[-1] * 2 + 1)
        full += len(t)
        if not ys: tot += 64; continue
        side = max(x1 - x0 + 1, ys[-1] - ys[0] + 1)
        side = next(v for v in (32, 64, 128, 256) if v >= side)
        hist[side] = hist.get(side, 0) + 1
        tot += 64 + side * side // 2
    return dict(full_kb=full // 1024, cropped_kb=tot // 1024, sizes=hist)
print(json.dumps(dict(crop=crop_estimate())))
print(json.dumps(dict(label=sys.argv[2] if len(sys.argv) > 2 else asi.name, steps=out)))
