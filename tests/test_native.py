"""Unicorn check: real Biohazard.exe image + built ASI. Install, draw, compose, visibility, caching.

Run: .venv/bin/python tests/test_native.py   (RE1_EXE overrides the game exe path)
"""
import json, os, re, struct, sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

ROOT = Path(__file__).resolve().parent.parent
EXE = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'Biohazard.exe'
DLL = ROOT / 'mod_annotated_map/RE1.AnnotatedMap.dll'
STUB, STACK, HEAP = 0x25000000, 0x20000000, 0x21000000


def load_pe(blob, base):
    pe = struct.unpack_from('<I', blob, 60)[0]
    o = pe + 24
    preferred, size = struct.unpack_from('<I', blob, o + 28)[0], struct.unpack_from('<I', blob, o + 56)[0]
    hdr = struct.unpack_from('<I', blob, o + 60)[0]
    im = bytearray(size)
    im[:hdr] = blob[:hdr]
    for i in range(struct.unpack_from('<H', blob, pe + 6)[0]):
        h = o + struct.unpack_from('<H', blob, pe + 20)[0] + i * 40
        vs, rv, rs, raw = struct.unpack_from('<IIII', blob, h + 8)
        im[rv:rv + rs] = blob[raw:raw + rs]
    rv, z = struct.unpack_from('<II', blob, o + 96 + 5 * 8)
    p = rv
    while z and p < rv + z:
        page, ln = struct.unpack_from('<II', im, p)
        for j in range(p + 8, p + ln, 2):
            e = struct.unpack_from('<H', im, j)[0]
            if e >> 12 == 3:
                t = page + (e & 4095)
                struct.pack_into('<I', im, t, (struct.unpack_from('<I', im, t)[0] + base - preferred) & 0xffffffff)
        p += ln
    return im, o


u = Uc(UC_ARCH_X86, UC_MODE_32)
gi, _ = load_pe(EXE.read_bytes(), 0x400000)
u.mem_map(0x400000, (len(gi) + 4095) // 4096 * 4096)
u.mem_write(0x400000, bytes(gi))
DBASE = 0x10000000
di, o = load_pe(DLL.read_bytes(), DBASE)
u.mem_map(DBASE, (len(di) + 4095) // 4096 * 4096)
u.mem_map(STUB, 0x10000)
u.mem_map(STACK, 0x20000)
u.mem_map(HEAP, 0x100000)

# ---- imports -> stubs (python side effects + correct stdcall pop)
state = dict(keys=set(), ini=dict(Rooms=0, Locks=0, Documents=0, Puzzles=0, CommonItems=0), written={})
POP = dict(GetModuleFileNameA=12, GetModuleHandleA=4, GetPrivateProfileIntA=16, GetPrivateProfileStringA=24,
           WritePrivateProfileStringA=16, VirtualProtect=16, FlushInstructionCache=12, GetCurrentProcess=0, CreateFileA=28,
           WriteFile=20, CloseHandle=4, DisableThreadLibraryCalls=4, lstrlenA=4, GetForegroundWindow=0,
           GetWindowThreadProcessId=8, GetCurrentProcessId=0, GetAsyncKeyState=4, GetTickCount=0, wsprintfA=0,
           LoadLibraryA=4, GetProcAddress=8, lstrcmpiA=8)


def arg(i):
    return struct.unpack('<I', u.mem_read(u.reg_read(UC_X86_REG_ESP) + 4 + 4 * i, 4))[0]


def cstr(a):
    b = bytes(u.mem_read(a, 260))
    return b[:b.index(0)].decode('latin1')


def imp_GetModuleFileNameA():
    u.mem_write(arg(1), b'C:\\game\\RE1.AnnotatedMap.asi\0'); return 28
def imp_GetModuleHandleA():
    return 0x400000 if arg(0) == 0 else 0x70000000
def imp_GetPrivateProfileIntA():
    return state['ini'].get(cstr(arg(1)), arg(2))
def imp_GetPrivateProfileStringA():
    v = state['ini'].get(cstr(arg(1)), cstr(arg(2))).encode() + b'\0'; u.mem_write(arg(3), v); return len(v) - 1
def imp_WritePrivateProfileStringA():
    state['written'][cstr(arg(1))] = cstr(arg(2)); return 1
def imp_LoadLibraryA():
    return 0   # no XInput in the harness: pad open is disabled, keyboard / cancel paths are exercised
def imp_GetProcAddress():
    return 0
def imp_lstrcmpiA():
    a, b = cstr(arg(0)).lower(), cstr(arg(1)).lower()
    return (a > b) - (a < b)
def imp_lstrlenA():
    return len(cstr(arg(0)))
def imp_CreateFileA():
    return 0xffffffff
def imp_GetWindowThreadProcessId():
    if arg(1): u.mem_write(arg(1), struct.pack('<I', 1234 if state.get('foreground', True) else 9999))
    return 1
def imp_GetCurrentProcessId():
    return 1234
def imp_GetAsyncKeyState():
    return 0x8000 if arg(0) in state['keys'] else 0
def imp_GetTickCount():
    state['clock'] = state.get('clock', 0) + 34
    return state['clock']
def imp_GetForegroundWindow():
    return 0x77


handlers = {}
imp_dir = struct.unpack_from('<I', di, o + 96 + 8)[0]
p, slot = imp_dir, 0
while struct.unpack_from('<I', di, p + 12)[0]:
    lookup, _, _, _, iat = struct.unpack_from('<5I', di, p)
    lookup = lookup or iat
    i = 0
    while (ent := struct.unpack_from('<I', di, lookup + i * 4)[0]):
        name = di[ent + 2:di.index(0, ent + 2)].decode()
        a = STUB + slot * 8
        n = POP[name]
        u.mem_write(a, bytes([0xc2, n, 0]) if n else b'\xc3')
        handlers[a] = globals().get('imp_' + name, lambda: 1)
        struct.pack_into('<I', di, iat + i * 4, a)
        i += 1
        slot += 1
    p += 20
u.mem_write(DBASE, bytes(di))


def on_stub(uc, addr, size, _):
    if addr in handlers:
        uc.reg_write(UC_X86_REG_EAX, handlers[addr]() & 0xffffffff)


u.hook_add(UC_HOOK_CODE, on_stub, begin=STUB, end=STUB + 0x1000)

# ---- native functions the overlay calls: stub with recording
uploads, sprites = [], []
TEX_SLOT = 0x6977a8 + 13 * 0x21c
NATIVE = {0x43c7c0: b'\xc3', 0x441920: b'\xb8\x01\x00\x00\x00\xc3', 0x43f700: b'\xc3', 0x4983f0: b'\xc3', 0x498040: b'\xc3',
          0x43f2e0: b'\xc3', 0x4172c0: b'\xc3', 0x43f950: b'\xc3'}
for a, code in NATIVE.items():
    u.mem_write(a, code)
tex_ids = [0x5000]


def on_native(uc, addr, size, _):
    if addr == 0x43f700:
        tim, tpage, clut, idx = (arg(i) for i in range(4))
        assert (tpage, clut, idx) == (0, 0, 1)
        w, h = struct.unpack('<HH', uc.mem_read(tim + 60, 4)); w *= 4   # TIM pixel block: words x rows
        uploads.append(bytes(uc.mem_read(tim, 64 + w * h // 2)))
        tex_ids[0] += 1
        uc.mem_write(TEX_SLOT + 0x1e0, struct.pack('<I', 1))
        uc.mem_write(TEX_SLOT + 0x1e8, struct.pack('<I', tex_ids[0]))
    elif addr == 0x441920:
        sp = bytes(uc.mem_read(arg(0), 24))
        sprites.append(dict(x=struct.unpack_from('<h', sp, 4)[0], y=struct.unpack_from('<h', sp, 6)[0],
                            wh=struct.unpack_from('<HH', sp, 8), tpage=struct.unpack_from('<H', sp, 12)[0],
                            cy=struct.unpack_from('<H', sp, 18)[0], z=arg(1), n=arg(2), count=arg(3),
                            tex=struct.unpack('<I', uc.mem_read(TEX_SLOT + 0x1e8, 4))[0],
                            slot=bytes(uc.mem_read(TEX_SLOT, 0x21c)), flags=struct.unpack_from('<I', sp)[0], uv=(sp[14], sp[15])))


u.hook_add(UC_HOOK_CODE, on_native, begin=0x43f700, end=0x43f700)
u.hook_add(UC_HOOK_CODE, on_native, begin=0x441920, end=0x441920)


def call(addr, *args):
    u.mem_write(STACK + 0x8000, struct.pack('<' + 'I' * (len(args) + 1), STACK + 0x100, *args))
    u.reg_write(UC_X86_REG_ESP, STACK + 0x8000)
    u.emu_start(addr, STACK + 0x100, count=400_000_000)
    return u.reg_read(UC_X86_REG_EAX)


# ---- install
entry = DBASE + struct.unpack_from('<I', di, o + 16)[0]
u.mem_write(TEX_SLOT, b'\x5a' * 0x21c)          # game-owned slot content must survive
assert call(entry, DBASE, 1, 0) == 1
target = lambda a: (a + 5 + struct.unpack('<i', u.mem_read(a + 1, 4))[0]) & 0xffffffff
hook = target(0x43c491)
assert DBASE <= hook < DBASE + len(di), 'map draw site not patched'
for a in (0x43c4f3, 0x43c53f, 0x43c5f5, 0x43c620, 0x43c645, 0x43c704, 0x43c773, 0x43c784):
    assert target(a) == hook
assert DBASE <= target(0x43c158) < DBASE + len(di) and DBASE <= target(0x43c2bc) < DBASE + len(di)
assert DBASE <= target(0x441de5) < DBASE + len(di)

# ---- data model
d = json.loads((ROOT / 'data/annotated.json').read_text())
hdr = (ROOT / 'src/overlay_data.h').read_text()
def top_level(text):
    """Top-level {...} groups of a C initializer, flattened to ints."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch == '{':
            depth += 1
            if depth == 1:
                cur = ''
                continue
        elif ch == '}':
            depth -= 1
            if depth == 0:
                out.append([int(v) for v in re.findall(r'-?\d+', cur)])
                continue
        if depth >= 1:
            cur += ch + (' ' if ch == '}' else '')
    return out


# OvMarker: kind,page,stage,slot,flagtype,chars,flag,icon, ico[2][2], lab[view][lang]{bid,x,y}
# -> (kind,page,stage,slot,flagtype,chars,flag,icon, en,ko, ix,iy, lx,ly) for the status view (English label position)
markers = [tuple(f[:8] + [f[12], f[15], f[8], f[9], f[13], f[14]])
           for f in top_level(hdr.split('ov_markers[]={', 1)[1].split('};', 1)[0])]
bitmaps = [tuple(int(x) for x in m.split(',')) for m in re.findall(r'\{([0-9,]+)\}', hdr.split('ov_bitmaps[]=', 1)[1].split('};', 1)[0])]
S = int(re.search(r'#define OV_SCALE (\d+)', hdr)[1])
WIDTH, HEIGHT = 320 * S, 256 * S
TILE_TEX = int(re.search(r'#define OV_TILE_TEX (\d+)', hdr)[1])
TILE_PSX = TILE_TEX // S


def setbits(addr, bits, n=32):
    buf = bytearray(n * 4)
    for b in bits:
        struct.pack_into('>I', buf, (b >> 5) * 4, struct.unpack_from('>I', buf, (b >> 5) * 4)[0] | (0x80000000 >> (b & 31)))
    # game stores dwords little-endian; bit order is MSB-first within the dword value
    out = bytearray(n * 4)
    for i in range(n):
        struct.pack_into('<I', out, i * 4, struct.unpack_from('>I', buf, i * 4)[0])
    u.mem_write(addr, bytes(out))


def scene(page, jill=False, visited=(), picked=(), doors=()):
    u.mem_write(0xC33090, struct.pack('<I', 0x800000 if jill else 0))
    st = bytearray(0x20)
    st[5], st[6], st[7] = d['pages'][page]['stage'], page, 0
    u.mem_write(0xB38DE0, bytes(st))
    sp = bytearray(u.mem_read(0x4B1D58, 36))
    struct.pack_into('<hh', sp, 4, 0x80, 0x4e)
    struct.pack_into('<hhhh', sp, 0x18, 80, 50, 0x1000, 0x1000)
    u.mem_write(0x4B1D58, bytes(sp))
    setbits(0xC38744, doors, 2)
    # pickup bits mean 'still there' (new game sets them, Flg_off 0x414fe0 clears on pickup)
    setbits(0xC3876C, [f for f in range(256) if f not in picked], 13)
    setbits(0xC387A0, visited, 5)
    call(target(0x40b5ac), 0, 1)  # simulate reopening the map after gameplay changes


def canvas():
    """Reconstruct the actual cropped sprite parts, including a fixed fullscreen backdrop."""
    full = 'exports' in globals() and struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0]
    img = bytearray([0]) * (WIDTH * HEIGHT)
    by_tex = {0x5000 + i + 1: t for i, t in enumerate(uploads)}
    for k, s in enumerate(sprites_now):
        t = by_tex[s['tex']]
        px = t[64:]
        f = (2 if k == 2 else 1) if full and k in (2, 3) else 1   # fullscreen: 2 terrain fill (2x), 3 walls/doors (1 texel = 1 PSX)
        for y in range(s['wh'][1] * S * f):
            for x in range(s['wh'][0] * S * f):
                sx, sy = (s['uv'][0] + x // (S * f), s['uv'][1] + y // (S * f)) if full and k < 4 else (s['uv'][0] * S + x, s['uv'][1] * S + y)
                tw = struct.unpack_from('<H', t, 60)[0] * 4
                v = (px[sy * (tw // 2) + sx // 2] >> ((sx & 1) * 4)) & 15
                if v:
                    img[(s['y'] * S + y) * WIDTH + s['x'] * S + x] = v
    return img


def draw():
    global uploads_now, sprites_now, base_upload
    base_upload = len(uploads)
    n0 = len(sprites)
    call(hook, 0xB38DE0)
    uploads_now, sprites_now = uploads[base_upload:], sprites[n0:]
    return uploads_now, sprites_now


PIXELS = bytes(int(x) for x in hdr.split('ov_pixels[', 1)[1].split('{', 1)[1].split('}', 1)[0].split(','))


def bitmap_present(img, bid, x, y):
    """Every opaque texel of bitmap `bid` is on the canvas at (x, y) with the same palette index."""
    w, h, off = bitmaps[bid]
    row = (w + 1) // 2
    for j in range(h):
        for i in range(w):
            v = (PIXELS[off + j * row + i // 2] >> ((i & 1) * 4)) & 15
            if v and img[(y + j) * WIDTH + x + i] != v:
                return False
    return True


ORIGIN = ((0x80 - 80) * S, (0x4e - 50) * S)
page0 = [m for m in markers if m[1] == 0]
def isolated(m, pool):
    w, h, _ = bitmaps[m[7]]
    box = (m[10], m[11], m[10] + w, m[11] + h)
    for o in pool:
        if o is m:
            continue
        for bid, x, y in ((o[7], o[10], o[11]), (o[8], o[12], o[13]), (o[9], o[12], o[13])):
            if bid < 0:
                continue
            ow, oh, _ = bitmaps[bid]
            if x < box[2] and box[0] < x + ow and y < box[3] and box[1] < y + oh:
                return False
    return True


key_item = next(m for m in page0 if m[0] == 3 and m[5] & 1 and isolated(m, [x for x in page0 if x[0] == 3]))   # Chris key item on mansion 1F
stage, slot, flag = key_item[2], key_item[3], key_item[6]
vbit = [0, 32, 63, 82, 100][stage] + slot

# 1) unvisited, scope 1: only the legend is drawn
scene(0)
up, sp = draw()
assert up and sp and all(s['tpage'] == 0 and s['cy'] == 0x1e0 and s['n'] == 0xfffffffe and s['count'] == 1 and s['z'] == 0x10
                         and s['wh'] == (TILE_PSX, TILE_PSX) and s['x'] % TILE_PSX == 0 and s['y'] % TILE_PSX == 0 for s in sp), sp
img = canvas()
assert not bitmap_present(img, key_item[7], ORIGIN[0] + key_item[10], ORIGIN[1] + key_item[11]), 'marker in unvisited room'
assert bytes(u.mem_read(TEX_SLOT, 0x21c)) == b'\x5a' * 0x21c, 'game texture slot not restored'

# 2) same state again: cached, no new upload, same sprites re-submitted
up2, sp2 = draw()
assert not up2 and len(sp2) == len(sp)

# 3) visited -> marker appears; picked -> disappears
scene(0, visited=[vbit])
draw()
img = canvas()
assert bitmap_present(img, key_item[7], ORIGIN[0] + key_item[10], ORIGIN[1] + key_item[11]), 'visited key item missing'
assert not bitmap_present(img, key_item[8], ORIGIN[0] + key_item[12], ORIGIN[1] + key_item[13]), 'item name clutters small map'
scene(0, visited=[vbit], picked=[flag])
draw()
img = canvas()
assert not bitmap_present(img, key_item[7], ORIGIN[0] + key_item[10], ORIGIN[1] + key_item[11]), 'picked item still drawn'

# 4) character filter: a Chris-only marker hides for Jill
chris_only = next((m for m in page0 if m[5] == 1 and m[0] == 3 and isolated(m, [x for x in page0 if x[0] == 3])), None)
if chris_only:
    vb = [0, 32, 63, 82, 100][chris_only[2]] + chris_only[3]
    scene(0, jill=True, visited=[vb])
    draw()
    img = canvas()
    assert not bitmap_present(img, chris_only[7], ORIGIN[0] + chris_only[10], ORIGIN[1] + chris_only[11]), 'Chris-only marker shown for Jill'

# 5) door unlocked hides its lock marker (enable locks with key 2)
state['keys'] = {ord('2')}
draw()
state['keys'] = set()
lock = next(m for m in markers if m[0] == 2 and m[5] & 1 and isolated(m, [x for x in markers if x[1] == m[1] and x[0] in (2, 3)]))
lpage = lock[1]
lvb = [0, 32, 63, 82, 100][lock[2]] + lock[3]
scene(lpage, visited=[lvb])
draw()
img = canvas()
assert bitmap_present(img, lock[7], ORIGIN[0] + lock[10], ORIGIN[1] + lock[11]), 'lock marker missing'
scene(lpage, visited=[lvb], doors=[lock[6]])
draw()
img = canvas()
assert not bitmap_present(img, lock[7], ORIGIN[0] + lock[10], ORIGIN[1] + lock[11]), 'unlocked door still marked'

# 6) key '3' toggles key items off and persists
scene(0, visited=[vbit])
state['keys'] = {ord('3')}
draw()
state['keys'] = set()
img = canvas()
assert not bitmap_present(img, key_item[7], ORIGIN[0] + key_item[10], ORIGIN[1] + key_item[11]), 'toggle 3 ignored'
assert state['written'].get('KeyItems') == '0'
state['keys'] = {ord('3')}
draw()
state['keys'] = set()

# 7) zoom animation (scale != 1.0): nothing drawn
sp_bytes = bytearray(u.mem_read(0x4B1D58, 36))
struct.pack_into('<h', sp_bytes, 0x1c, 0x1400)
u.mem_write(0x4B1D58, bytes(sp_bytes))
_, sp7 = draw()
assert not sp7
print(json.dumps(dict(passed=True, uploads=len(uploads), sprites=len(sprites), dll=str(DLL.name)), indent=1))

# 8) Add_sprt submit hook scales our UVs only while ov_uv_scale is set (exported for this check)
exp_rv = struct.unpack_from('<I', di, o + 96)[0]
nnames, fn_rva, name_rva, ord_rva = struct.unpack_from('<I', di, exp_rv + 24)[0], *struct.unpack_from('<3I', di, exp_rv + 28)
exports = {}
for i in range(nnames):
    nm = di[struct.unpack_from('<I', di, name_rva + 4 * i)[0]:].split(b'\0', 1)[0].decode()
    exports[nm] = DBASE + struct.unpack_from('<I', di, fn_rva + 4 * struct.unpack_from('<H', di, ord_rva + 2 * i)[0])[0]
scale_var = exports['ov_uv_scale']
u.mem_write(0x47a9b0, b'\xc2\x08\x00')            # Marni submit: thiscall, 2 stack args
cmd = HEAP + 0x1000
for scale, want in ((0, (3, 5, 10, 12)), (4, (12, 20, 43, 51))):
    u.mem_write(cmd + 16, struct.pack('<4H', 3, 5, 10, 12))
    u.mem_write(scale_var, struct.pack('<i', scale))
    call(target(0x441de5), cmd, 7)
    assert struct.unpack('<4H', u.mem_read(cmd + 16, 8)) == want, (scale, struct.unpack('<4H', u.mem_read(cmd + 16, 8)))
u.mem_write(scale_var, struct.pack('<i', 0))
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
u.mem_write(scale_var, struct.pack('<i', S))
u.mem_write(cmd + 24, struct.pack('<I', 756))
call(target(0x441de5), cmd, 16)
assert struct.unpack('<I', u.mem_read(cmd + 24, 4))[0] == 400
u.mem_write(scale_var, bytes(4))
u.mem_write(exports['ov_fullscreen'], bytes(4))
print('submit scaling / dedicated foreground depth ok')

# Keep every annotation inside the existing map panel, in both languages/all pages.
scene(0, visited=[5, 6])
state['keys'] = set()
draw()
state['keys'] = {ord(k) for k in '13456'}
draw()
layout_sample = canvas()
for language in range(2):
    for page in range(11):
        scene(page, visited=list(range(124)))
        state['keys'] = {ord('8' if language == 0 else '9')} if page == 0 else set()
        draw()
        img = canvas()
        for y in range(256 * S):
            row = img[y * WIDTH:(y + 1) * WIDTH]
            if 128 * S <= y < 134 * S:   # legend box inside the map panel, below the floor drawing (x 32..138)
                assert not any(row[:32 * S]) and not any(row[138 * S:]), (language, page, y, 'legend outside its box')
            elif not 24 * S <= y < 128 * S:
                assert not any(row), (language, page, y, 'outside map vertically')
            else:
                assert not any(row[:32 * S]) and not any(row[192 * S:]), (language, page, y, 'outside map horizontally')
print('all 11 pages / both languages stay inside the native map panel')

# Dedicated mode is foreground-only, leaves settings intact, and returns on map close.
scene(0, visited=[5, 6])
state['foreground'] = False
state['keys'] = {ord('7')}
draw()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
state['foreground'] = True
state['keys'] = set()
draw()
state['keys'] = {ord('7')}
draw()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 1
assert 1 < len(sprites_now) <= 3 * (320 // TILE_PSX) * (256 // TILE_PSX) + 5   # icon / name / arrow layers + background, terrain, outline, player
full_sample = canvas()
state['keys'] = {ord('0')}
draw()
terrain_sample = canvas()
state['keys'] = set()
draw()
state['keys'] = {ord('0')}
draw()
full_sample = canvas()
full_layers = (list(uploads), list(sprites_now), 0)
titles = [int(v) for v in re.findall(r'\d+', hdr.split('ov_page_titles[11][2]={', 1)[1].split('};', 1)[0])]
lang_now = 0 if state['written'].get('Language', 'en') == 'en' else 1
assert any(bitmap_present(full_sample, titles[2 * 0 + l], 10 * S, 8 * S) for l in (0, 1)), 'area title missing at top-left'
assert full_sample[0] in (2, 3, 4) and full_sample[(240*S-1)*WIDTH] in (2, 3, 4)
state['keys'] = set()
draw()
positions = [(v['x'], v['y'], v['uv'], v['wh']) for v in sprites_now]
state['keys'] = {0x27, 0x28}  # right / down
pan_uploads, _ = draw()
assert not pan_uploads, 'panning rebuilt textures'
assert positions == [(v['x'], v['y'], v['uv'], v['wh']) for v in sprites_now], 'fullscreen map must remain fixed'
assert all(v['x'] >= 0 and v['y'] >= 0 for v in sprites_now)
state['keys'] = {0x24}       # Home resets pan
assert not draw()[0]
assert positions == [(v['x'], v['y'], v['uv'], v['wh']) for v in sprites_now]

# Unknown room fill stays hidden; shared walls remain like the original map.
raw_maps = hdr.split('ov_map_pixels[11][12800]={', 1)[1].split('};', 1)[0]
FULL_ORIGIN = [tuple(f) for f in top_level(hdr.split('ov_full_origin[11][2]={', 1)[1].split('};', 1)[0])]
terrain = bytes(int(v) for v in raw_maps.replace('{','').replace('}','').split(','))[:12800]
for slot, visible in ((5, True), (6, True), (7, False)):
    pos = next(i for i, v in enumerate(terrain) if v == 13 + slot * 6 + 3)
    x, y = pos % 128, pos // 128
    fx, fy = FULL_ORIGIN[0]
    v = terrain_sample[(fy+2*y)*S*WIDTH + (fx+2*x)*S]
    assert v in (4, 7, 8) if visible else v in (2, 3, 4), (slot, v)   # native fill / current red / remaining amber
for page in range(1, 11):
    scene(page, visited=list(range(124)))
    state['keys'] = set()
    draw()
    assert 1 < len(sprites_now) <= 3 * (320 // TILE_PSX) * (256 // TILE_PSX) + 5   # icon / name / arrow layers + background, terrain, outline, player
state['keys'] = set()
draw()
state['keys'] = {ord('7')}
draw()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
state['keys'] = set()
draw()
state['keys'] = {ord('7')}
draw()
sp_bytes = bytearray(u.mem_read(0x4B1D58, 36))
struct.pack_into('<h', sp_bytes, 0x1c, 0x1400)
u.mem_write(0x4B1D58, bytes(sp_bytes))
draw()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
print('dedicated mode toggle / terrain visibility / close reset ok')

# Static preview uses the actual compiled DLL composition for the screenshot's visited rooms.
from PIL import Image, ImageDraw
# Match the generated palette by decoding its native RGB555 entries.
colors = [int(v) for v in hdr.split('ov_palette[16]={', 1)[1].split('}', 1)[0].split(',')]
preview = Image.new('RGB', (WIDTH, 240 * S), (8, 8, 12))
g = ImageDraw.Draw(preview)
g.rectangle((32*S, 24*S, 192*S-1, 128*S-1), fill=(8, 10, 32), outline=(120, 120, 110), width=2)
for y in range(240 * S):
    for x in range(WIDTH):
        v = layout_sample[y * WIDTH + x]
        if v:
            c = colors[v]
            preview.putpixel((x, y), ((c & 31)*255//31, ((c>>5)&31)*255//31, ((c>>10)&31)*255//31))
(ROOT / 'build').mkdir(exist_ok=True)
preview.save(ROOT / 'build/native-layout-preview.png')
from PIL import Image
preview = Image.new('RGB', (WIDTH, 240*S), (8, 8, 12))
layer_uploads, layer_sprites, layer_base = full_layers
by_tex = {0x5000+layer_base+i+1: t for i,t in enumerate(layer_uploads)}
for k, sp in enumerate(layer_sprites):
    tim = by_tex[sp['tex']]
    pal = struct.unpack('<16H', tim[20:52])
    rgba = bytes(v for c in pal for v in ((c&31)*255//31, ((c>>5)&31)*255//31, ((c>>10)&31)*255//31, 0 if c == 0 else 128 if k < 3 else 255))   # 3 opaque
    indices = bytes(v for b in tim[64:] for v in (b&15,b>>4))
    tw = struct.unpack_from('<H', tim, 60)[0] * 4
    layer = Image.frombytes('P', (tw, len(indices) // tw), indices)
    layer.putpalette(rgba, rawmode='RGBA')
    scale = S * (2 if k == 2 else 1) if k < 4 else 1   # 0/1 background, 2 fill (2x), 3 walls/doors (1:1 PSX)
    w,h = sp['wh']; u0,v0 = sp['uv']
    if k >= 4: w,h,u0,v0 = w*S,h*S,u0*S,v0*S
    layer = layer.crop((u0,v0,u0+w,v0+h)).convert('RGBA')
    if scale != 1: layer = layer.resize((w*scale,h*scale),Image.Resampling.NEAREST)
    preview.paste(layer,(sp['x']*S,sp['y']*S),layer)
preview.save(ROOT / 'build/dedicated-map-preview.png')

# M uses the original gameplay inventory gate and native task initialization/cleanup.
for addr in (0x468310, 0x43e970, 0x414dd0, 0x414e60, 0x4172c0, 0x43ca60, 0x42c6b0, 0x40ba50, 0x40bb60, 0x40b9e0):
    u.mem_write(addr, b'\xc3')
    u.ctl_remove_cache(addr, addr + 16)
u.mem_write(0x40b9e0, b'\xc6\x05\x31\xe9\xc2\x00\x07\xc3')
u.ctl_remove_cache(0x40b9e0, 0x40b9f0)
scene(0, visited=[5, 6])
u.mem_write(0xC33090, struct.pack('<I', 0x90800008))
u.mem_write(0xC330AC, b'\x02')
u.mem_write(0xC3523E, b'\x00')
u.mem_write(0xC3AB90, struct.pack('<H', 0xffff))
u.mem_write(0xC384EB, b'\x00')  # actual live gameplay snapshot, 2026-10-19
u.mem_write(0xC3F8E0, bytes(2))
state['keys'] = {ord('M')}
state['foreground'] = False
call(target(0x48d0aa), 0)
assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] == 0
state['foreground'] = True
u.mem_write(0xC3523E, b'\x01')
call(target(0x48d0aa), 0)
assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] == 0
state['keys'] = set(); call(target(0x48d0aa), 0)
u.mem_write(0xC3523E, b'\x00')
state['keys'] = {ord('M')}; call(target(0x48d0aa), 0)
assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] == 0x800
# Run the unchanged native gameplay gate: it must enter the original menu state.
u.emu_start(0x48d0b2, 0x48d126, count=100)
assert u.mem_read(0xC384EB, 1) == b'\x01'
# Native task scheduling can run another gameplay startup frame before menu initialization.
u.mem_write(0xC384EB, b'\x02')
call(target(0x48d0aa), 0)  # held M; pending request must survive
call(target(0x40b5ac), 0, 1)
assert u.mem_read(0xC2E930, 2) == b'\x00\x00'
# Run the original menu's first-frame map branch, rather than calling its loaders early.
u.emu_start(0x40b62c, 0x40b643, count=100)
assert u.mem_read(0xC2E931, 1) == b'\x01'
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 1
u.mem_write(0xC38712, bytes(2))
call(target(0x40b96b))  # held M must not immediately close
assert u.mem_read(0xC2E931, 1) == b'\x01'
state['keys'] = set(); call(target(0x40b96b))
# The fixed map consumes original movement action bits directly, without a selector screen.
u.mem_write(0xB38DE4, b'\x00')
u.mem_write(0xB38DE6, b'\x00')   # init is stubbed here; the first frame's selector refresh (0x43bd30) ran on test state
u.mem_write(0xB38DE8, b'\x01\x01')
u.mem_write(0xB38DED, b'\x03')  # mansion + courtyard
u.mem_write(0xB38DF6, struct.pack('<H', 31))  # mansion/courtyard floors eligible
u.mem_write(0xB38DEF, bytes(1))
u.mem_write(0xC3F8E0, bytes(2))
call(target(0x40b96b))
assert u.mem_read(0xB38DE6, 1) == b'\x00'
u.mem_write(0xC38710, struct.pack('<H', 1))
u.mem_write(0xC38712, struct.pack('<H', 1))
call(target(0x40b96b))
assert u.mem_read(0xB38DE6, 1) == b'\x01', 'forward action did not select 2F'
u.mem_write(0xC38710, struct.pack('<H', 4))
u.mem_write(0xC38712, struct.pack('<H', 4))
call(target(0x40b96b))
assert u.mem_read(0xB38DE6, 1) == b'\x00', 'backward action did not select 1F'
u.mem_write(0xC38710, struct.pack('<H', 8))
u.mem_write(0xC38712, struct.pack('<H', 8))
call(target(0x40b96b))
assert u.mem_read(0xB38DE4, 1) == b'\x01' and u.mem_read(0xB38DE6, 1) == b'\x03', 'right action did not select courtyard'
u.mem_write(0xC38710, struct.pack('<H', 2))
u.mem_write(0xC38712, struct.pack('<H', 2))
call(target(0x40b96b))
assert u.mem_read(0xB38DE4, 1) == b'\x00' and u.mem_read(0xB38DE6, 1) == b'\x00', 'left action did not return to mansion'
assert u.mem_read(0xC3F8E0, 2) == bytes(2), 'temporary map direction mapping leaked to game input'
u.mem_write(0xC38710, struct.pack('<H', 4))
u.mem_write(0xC38712, struct.pack('<H', 4))
call(target(0x40b96b))  # 1F -> B1
assert u.mem_read(0xB38DE6, 1) == b'\x02'
u.mem_write(0xC38712, bytes(2))
call(target(0x40b96b))  # held below repeat delay; stays B1
assert u.mem_read(0xB38DE6, 1) == b'\x02'
u.mem_write(0xC38710, struct.pack('<H', 1))
call(target(0x40b96b))  # B1 -> 1F
assert u.mem_read(0xB38DE6, 1) == b'\x00'
state['clock'] += 400
call(target(0x40b96b))  # held repeat -> 2F
assert u.mem_read(0xB38DE6, 1) == b'\x01'
u.mem_write(0xC3F8E0, bytes(2))
u.mem_write(0xC38710, bytes(2))
u.mem_write(0xC38712, bytes(2))
state['keys'] = {ord('M')}; call(target(0x40b96b))
assert u.mem_read(0xC2E931, 1) == b'\x07'
call(target(0x40b91b))
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
state['keys'] = set()
# Live game: the hook moves the menu to state 1 before case 0 (map init 0x43ca60) runs, so the
# direct viewer must initialise the map itself (opened in the laboratory, it showed the mansion).
u.mem_write(0xC2E931, b'\x00')
call(target(0x48d0aa), 0)
state['keys'] = {ord('M')}; call(target(0x48d0aa), 0)
u.emu_start(0x48d0b2, 0x48d126, count=100)
u.mem_write(0xC384EB, b'\x02')
call(target(0x40b5ac), 0, 1)
state['keys'] = set()
inits = []
h = u.hook_add(UC_HOOK_CODE, lambda uc, a, sz, ud: inits.append(a), begin=0x43ca60, end=0x43ca60)  # native init (stubbed here)
h2 = u.hook_add(UC_HOOK_CODE, lambda uc, a, sz, ud: inits.append(a), begin=0x43bd30, end=0x43bd30)  # eligibility refresh
call(target(0x40b96b)); call(target(0x40b96b))
u.hook_del(h); u.hook_del(h2)
assert inits[:2] == [0x43ca60, 0x43bd30], ('direct map must run map init, then the floor/area eligibility refresh', inits)
state['keys'] = {ord('M')}; call(target(0x40b96b)); call(target(0x40b91b)); state['keys'] = set()
print('direct M / original forward-backward floor selection / confirm / close / cleanup ok')

# 9) Run the real Add_sprt UV calculation, not the recording stub.
# Upload_tim sets the slot's PSX origin from tpage; sprite UV bytes must address it.
u.mem_write(0x441920, bytes(gi[0x41920:0x41de5]))
u.ctl_remove_cache(0x441920, 0x441e10)
# Keep original blend/opacity functions, so fullscreen alpha is checked natively.
s = sprites[0]
tpage = s['tpage']
slot = s['slot']
assert struct.unpack_from('<9h', slot, 0x208) == (0, 0, TILE_TEX // 4, TILE_TEX, 0, 480, 0, 1, 0)
u.mem_write(TEX_SLOT, bytes(slot))
sp = bytearray(36)
struct.pack_into('<HHH', sp, 8, TILE_PSX, TILE_PSX, tpage)
struct.pack_into('<H', sp, 18, 480)
sp[20:23] = b'\x80' * 3
u.mem_write(HEAP + 0x3000, bytes(sp))
u.mem_write(0x4b27f8, bytes(4))
u.mem_write(0x4b32a8, bytes(4))
u.mem_write(0x4ac440, bytes(1))
u.mem_write(0x4b2e0c, bytes(4))
result = call(0x441920, HEAP + 0x3000, 16, 0xfffffffe, 1)
assert result == 1
# The live REbirth HD slot had zero bounds: it must reproduce the missing draw.
u.mem_write(TEX_SLOT + 0x20c, bytes(4))
assert call(0x441920, HEAP + 0x3000, 16, 0xfffffffe, 1) == 0
u.mem_write(TEX_SLOT, bytes(slot))
uv = struct.unpack('<4H', u.mem_read(0x68f610, 8))
assert uv == (0, 0, TILE_PSX - 1, TILE_PSX - 1), f'Native Add_sprt samples outside the tile: {uv}'
print('native Add_sprt UV origin ok')

# Exercise a complete fullscreen draw through real Add_sprt + our submit hook.
commands = []
def record_submit(uc, addr, size, _):
    commands.append(bytes(uc.mem_read(arg(0), 52)))
u.hook_add(UC_HOOK_CODE, record_submit, begin=0x47a9b0, end=0x47a9b0)
scene(0, visited=[5, 6])
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
u.mem_write(0x4b27f8, bytes(4))
state['keys'] = set()
draw()
assert struct.unpack_from('<4h', commands[0], 8) == (0, 0, 255, 239)
assert struct.unpack_from('<4h', commands[1], 8) == (256, 0, 319, 239)
assert struct.unpack_from('<I', commands[0], 24)[0] == 416
assert struct.unpack_from('<I', commands[1], 24)[0] == 416
assert struct.unpack_from('<I', commands[2], 24)[0] == 408
assert struct.unpack_from('<I', commands[3], 24)[0] == 404 and struct.unpack_from('<4h', commands[3], 8) == struct.unpack_from('<4h', commands[2], 8)
assert all(struct.unpack_from('<I', c, 24)[0] == 400 for c in commands[4:])
assert all(all(v < TILE_TEX for v in struct.unpack_from('<4H', c, 16)) for c in commands)   # UVs stay inside the (512) texture
print('real fullscreen background / positive depths / clipped UVs ok:', len(commands), 'commands')


assert len(commands) <= 5 + 3 * (320 // TILE_PSX) * (256 // TILE_PSX) and len(commands) < 150, f'fullscreen submits too many commands (Add_sprt cap 300/frame): {len(commands)}'
assert struct.unpack_from('<4H', commands[0], 16) == (0, 0, 255, 239), 'background must sample at 1:1, not stretch'
assert struct.unpack_from('<I', commands[0], 28)[0] & 8
assert all(struct.unpack_from('<f', c, 44)[0] == 0.5 for c in commands[:3]), 'native map/background alpha differs'
assert struct.unpack_from('<f', commands[3], 44)[0] == 0, 'walls/doors opaque'
alphas = {round(struct.unpack_from('<f', c, 44)[0], 3) for c in commands[4:]}
assert {0, 0.3} <= alphas <= {0, 0.3, 0.15, 0.65}, ('icons/walls opaque, names 70% visible, arrows pulse', alphas)
# Generated grid repeats every 8 logical pixels in both axes, with no interpolation/resizing.
raw_bg = bytes(map(int, hdr.split('ov_background_pixels[32768]={', 1)[1].split('}', 1)[0].split(',')))
def background_pixel(x, y):
    return (raw_bg[(y%256)*128 + (x%256)//2] >> ((x&1)*4)) & 15
assert all(background_pixel(x,y) == background_pixel(x%8,y%8) for y in range(240) for x in range(320))
# Fullscreen steady frames must not recreate/upload texture data.
u.mem_write(0x4b27f8, bytes(4))
assert not draw()[0], 'fullscreen reuploads textures on an unchanged frame'
print('bounded commands / unchanged-frame cache / 8px grid repeat / native 0.5 map alpha / names 70% visible ok')

# No visited/pickup/door condition reads on steady frames: cache is event-driven.
flag_reads = []
def record_flag_read(uc, access, address, size, value, user):
    flag_reads.append((address,size))
watch = u.hook_add(UC_HOOK_MEM_READ, record_flag_read, begin=0xC38744, end=0xC387B4)
for _ in range(3):
    u.mem_write(0x4b27f8, bytes(4))
    assert not draw()[0]
u.hook_del(watch)
assert not flag_reads, f'steady frame still checks marker eligibility: {flag_reads[:8]}'
print('3 steady frames: zero eligibility flag reads and zero texture uploads')

# Player arrow (fullscreen): Pl_work Pos_x 0xC351E8 / Pos_z 0xC351F0 / Cdir_y 0xC35228, room 0xC386F1, map stage MAP_STATE[5].
xf = json.loads((ROOT / 'data/room_xform.json').read_text())
cell = int(re.search(r'#define OV_ARROW_CELL (\d+)', hdr)[1])
full_origin = FULL_ORIGIN[0]
r = xf['rooms']['0-06']                      # Main Hall 1F, page 0
o = xf['orient'][r['o']]
for wx, wz, heading, k in ((20000, 10000, 0, 4), (12000, 6000, 1024, 8), (12000, 6000, 3072, 0)):   # 0 -> +x (right), 1024 -> -z (down), 3072 -> +z (up)
    u.mem_write(0xC386F0, bytes([0, 6]))
    u.mem_write(0xC351E8, struct.pack('<i', wx)); u.mem_write(0xC351F0, struct.pack('<i', wz))
    u.mem_write(0xC35228, struct.pack('<h', heading))
    state['clock'] = 400                     # blink phase on
    u.mem_write(0x4b27f8, bytes(4))
    draw()
    arrow = [sp for sp in sprites_now if sp['wh'] == (cell, cell)]
    assert len(arrow) == 1, ('player arrow not drawn', [sp['wh'] for sp in sprites_now])
    px = r['tx'] + r.get('sx', r['s']) * (o[0] * wx + o[1] * wz); py = r['ty'] + r.get('sy', r['s']) * (o[2] * wx + o[3] * wz)
    ex, ey = full_origin[0] + 2 * px - cell / 2, full_origin[1] + 2 * py - cell / 2
    assert abs(arrow[0]['x'] - ex) <= 1 and abs(arrow[0]['y'] - ey) <= 1, (arrow[0], ex, ey)
    assert arrow[0]['uv'][:2] == ((k % 4) * cell, (k // 4) * cell), ('heading', heading, arrow[0]['uv'])
state['clock'] = 0                           # dim phase: still drawn, fainter
n_cmd = len(commands)
u.mem_write(0x4b27f8, bytes(4))
draw()
assert [sp for sp in sprites_now if sp['wh'] == (cell, cell)], 'player arrow must stay visible while dim'
assert round(struct.unpack_from('<f', commands[-1], 44)[0], 2) == 0.65, 'dim phase = 35 % visible'
print('player arrow position / heading / blink ok')

# Floor/area arrows: only where the native selector allows a move, and blinking.
def nav_sprites(clock):
    state['clock'] = clock
    u.mem_write(0x4b27f8, bytes(4))
    draw()
    return [sp for sp in sprites_now if sp['wh'] == (TILE_PSX, TILE_PSX)]
ms = bytearray(u.mem_read(0xB38DE0, 16))
ms[4], ms[12], ms[13] = 0, 1, 0b0011      # mansion area, floor up possible, courtyard (area 1) reachable
u.mem_write(0xB38DE0, bytes(ms))
call(target(0x40b5ac), 0, 1)              # recompose
base = len(commands)
on = nav_sprites(400); on_alpha = {round(struct.unpack_from('<f', c, 44)[0], 2) for c in commands[base:]}
base = len(commands)
off = nav_sprites(0); off_alpha = {round(struct.unpack_from('<f', c, 44)[0], 2) for c in commands[base:]}
assert len(on) == len(off) and 0.15 in on_alpha and 0.65 in off_alpha, ('arrows pulse bright/dim', on_alpha, off_alpha)
ms[12], ms[13] = 0, 1
u.mem_write(0xB38DE0, bytes(ms)); call(target(0x40b5ac), 0, 1)
none = nav_sprites(400)
ms[12], ms[13] = 1, 0b0011
u.mem_write(0xB38DE0, bytes(ms)); call(target(0x40b5ac), 0, 1)
on = nav_sprites(400)
blink_tiles = {(sp['x'], sp['y']) for sp in on} - {(sp['x'], sp['y']) for sp in none}
assert any(y == 0 for x, y in blink_tiles), ('up arrow missing at the top', blink_tiles)
# LEFT (KEY_LEFT = action 8) raises the area index: mansion (0) -> courtyard (1) is a LEFT move in RE1
assert any(x == 0 and 0 < y < 200 for x, y in blink_tiles), ('left (area) arrow missing', blink_tiles)
assert not any(x == 320 - TILE_PSX for x, y in blink_tiles), ('no right move from the mansion', blink_tiles)
print('floor/area arrows follow native availability and blink ok')

# Placement guards: Jill's Master Key (Lab B4 Main Lab, flag 95) is only placed while Flg_1[91] is clear (RDT 5131 init SCD).
u.mem_write(exports['ov_fullscreen'], bytes(4))
mk = next(m for m in markers if m[0] == 3 and m[6] == 95)
vis = [0, 32, 63, 82, 100][mk[2]] + mk[3]
def master_key_drawn(flag91):
    words = bytearray(u.mem_read(0xC38724, 32))
    w = struct.unpack_from('<I', words, (91 >> 5) * 4)[0]
    w = w | (0x80000000 >> (91 & 31)) if flag91 else w & ~(0x80000000 >> (91 & 31))
    struct.pack_into('<I', words, (91 >> 5) * 4, w); u.mem_write(0xC38724, bytes(words))
    scene(mk[1], jill=True, visited=[vis])
    state['keys'] = set()
    draw()
    return bitmap_present(canvas(), mk[7], ORIGIN[0] + mk[10], ORIGIN[1] + mk[11])
assert master_key_drawn(False), 'Master Key must show while Barry has not been rescued (Flg_1[91] clear)'
assert not master_key_drawn(True), 'Master Key must hide once Flg_1[91] is set (Jill)'
print('item placement guards (Master Key / Jill) ok')

# Solved puzzles disappear: Piano (bar) is solved once its reward, the Gold Emblem (pickup flag 21), is taken.
pz = next(m for m in markers if m[0] == 5 and m[4] == 3 and m[1] == 0 and bitmaps[m[7]] and
          d['rooms'][f"{m[2]}-{m[3]:02X}"]['name_en'] == 'Bar')
pvis = [0, 32, 63, 82, 100][pz[2]] + pz[3]
scene(0, visited=[pvis]); state['keys'] = set(); draw()
assert bitmap_present(canvas(), pz[7], ORIGIN[0] + pz[10], ORIGIN[1] + pz[11]), 'unsolved puzzle must show'
scene(0, visited=[pvis], picked=[21]); draw()
assert not bitmap_present(canvas(), pz[7], ORIGIN[0] + pz[10], ORIGIN[1] + pz[11]), 'solved puzzle (reward taken) must hide'
print('solved puzzles hide ok')

# Page change cost: texture uploads for a full fullscreen page (all rooms visited).
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
scene(0, visited=list(range(124)))
up, _ = draw()
print('fullscreen page compose uploads:', len(up))
assert len(up) <= 80, len(up)   # Full-page budget: 80 TIMs (~2.5 MiB); roomy labels touch more tiles.

# Lock keys: both sides are generated; the runtime labels the room not visited yet, else the destination.
u.mem_write(exports['ov_fullscreen'], bytes(4))
full = top_level(hdr.split('ov_markers[]={', 1)[1].split('};', 1)[0])
pairs = {}
for f in full:
    if f[0] == 2 and f[26]:
        pairs.setdefault((f[1], f[2], f[3], f[6], f[5]), {})[f[26]] = f
lk = next(v for v in pairs.values() if 1 in v and 2 in v and (v[1][27], v[1][28]) != (v[1][2], v[1][3]))
a1, a2 = lk[1], lk[2]
own_bit = [0, 32, 63, 82, 100][a1[2]] + a1[3]; dst_bit = [0, 32, 63, 82, 100][a1[27]] + a1[28]
def key_at(f, visited):
    scene(f[1], jill=bool(f[5] & 2 and not f[5] & 1), visited=visited); state['keys'] = set(); draw()
    return bitmap_present(canvas(), f[7], ORIGIN[0] + f[8], ORIGIN[1] + f[9])
assert key_at(a1, [own_bit]) and not key_at(a2, [own_bit]), 'own room visited -> key on the destination side'
assert key_at(a2, [dst_bit]) and not key_at(a1, [dst_bit]), 'only the destination visited -> key in the unvisited own room'
assert key_at(a1, [own_bit, dst_bit]), 'both visited -> destination side'
print('lock key side follows the unvisited room ok')

# Scope: 1 visited / 2 revealed by the floor map (Flg_7 bit 0x7C + n) / 3 all; room names always include revealed rooms.
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
def set_bit(addr, bit, on):
    w = bytearray(u.mem_read(addr + (bit >> 5) * 4, 4)); v = struct.unpack('<I', w)[0]
    v = v | (0x80000000 >> (bit & 31)) if on else v & ~(0x80000000 >> (bit & 31))
    u.mem_write(addr + (bit >> 5) * 4, struct.pack('<I', v))
room = next(f for f in full if f[0] == 1 and f[1] == 0 and f[18] >= 0)
def drawn(f, scope_val, revealed):
    scene(0, visited=[])
    set_bit(0xC387A0, 0x7C, revealed)                      # Map of 1F picked up
    u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1)); state['keys'] = set(); draw()
    for _ in range(3):                                      # key 8 cycles visited -> revealed -> all
        if state['written'].get('Scope') == str(scope_val): break
        state['keys'] = {ord('8')}; draw(); state['keys'] = set(); draw()
    assert state['written'].get('Scope') == str(scope_val)
    img = canvas()
    return any(bitmap_present(img, f[b], f[b + 1], f[b + 2]) for b in (18, 21)) if f[0] == 1 else bitmap_present(img, f[7], f[10], f[11])
assert not drawn(room, 1, False) and drawn(room, 1, True), 'room names show for revealed rooms even in scope 1'
item = next(f for f in full if f[0] == 6 and f[1] == 0 and f[5] & 1 and f[3] != room[3] and f[24] == 0xFFFF
            and drawn(f, 3, False))   # unguarded pickup whose icon is not covered by a neighbour
assert not drawn(item, 1, True) and drawn(item, 2, True) and not drawn(item, 2, False) and drawn(item, 3, False), 'item scope levels'
print('scope visited / revealed / all ok')

# Fullscreen map keys: OpenKey (M) opens at the gameplay gate; CloseKey (Esc) and the cancel action (0xC38712 bit 0x8000) close.
u.mem_write(0xC33090, struct.pack('<I', 0x90800008)); u.mem_write(0xC330AC, b'\x02'); u.mem_write(0xC3523E, b'\x00')
u.mem_write(0xC3AB90, struct.pack('<H', 0xffff)); u.mem_write(0xC38712, bytes(2))
def open_direct():
    u.mem_write(0xC3F8E0, bytes(2)); state['keys'] = set(); call(target(0x48d0aa), 0)
    state['keys'] = {ord('M')}; call(target(0x48d0aa), 0)
    assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] & 0x800, 'open key did not request the map'
    u.emu_start(0x48d0b2, 0x48d126, count=100); u.mem_write(0xC384EB, b'\x02'); call(target(0x40b5ac), 0, 1)
    state['keys'] = set(); call(target(0x40b96b))
    assert u.mem_read(0xC2E931, 1) == b'\x01'
for how in ('esc', 'cancel'):
    open_direct()
    if how == 'esc': state['keys'] = {0x1B}
    else: u.mem_write(0xC38712, struct.pack('<H', 0x8000))
    call(target(0x40b96b))
    assert u.mem_read(0xC2E931, 1) == b'\x07', ('map did not close via', how)
    call(target(0x40b91b)); state['keys'] = set(); u.mem_write(0xC38712, bytes(2))
print('fullscreen map closes with Esc and the cancel action ok')
