"""Unicorn check: real Biohazard.exe image + built ASI. Install, draw, compose, visibility, caching.

Run: .venv/bin/python tests/test_native.py   (RE1_EXE overrides the game exe path)
"""
import json, os, re, struct, sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

ROOT = Path(__file__).resolve().parent.parent
LANG_KEY = 0xDC   # '\' (VK_OEM_5): language; the digits are 0 all, 1 rooms, 2 locks, 3 key items, 4 files, 5 puzzles, 6 events, 7 common, 8 enemies, 9 scope
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
state = dict(keys=set(), ini=dict(Rooms=0, Locks=0, KeyItems=1, Documents=0, Puzzles=0, CommonItems=0, UploadBudget=200, HdIcons=0), written={})
POP = dict(GetModuleFileNameA=12, GetModuleHandleA=4, GetPrivateProfileIntA=16, GetPrivateProfileStringA=24,
           WritePrivateProfileStringA=16, VirtualProtect=16, FlushInstructionCache=12, GetCurrentProcess=0, CreateFileA=28,
           WriteFile=20, CloseHandle=4, DisableThreadLibraryCalls=4, lstrlenA=4, GetForegroundWindow=0,
           GetWindowThreadProcessId=8, GetCurrentProcessId=0, GetAsyncKeyState=4, GetTickCount=0, wsprintfA=0,
           LoadLibraryA=4, GetProcAddress=8, lstrcmpiA=8, CopyFileA=12, GetFileAttributesA=4, MoveFileExA=12, DeleteFileA=4)


def arg(i):
    return struct.unpack('<I', u.mem_read(u.reg_read(UC_X86_REG_ESP) + 4 + 4 * i, 4))[0]


def cstr(a):
    b = bytes(u.mem_read(a, 260))
    return b[:b.index(0)].decode('latin1')


def imp_GetModuleFileNameA():
    u.mem_write(arg(1), b'C:\\game\\RE1.AnnotatedMap.asi\0'); return 28
def imp_GetModuleHandleA():
    return 0x400000 if arg(0) == 0 else 0x70000000
def ini_key():   # [Colors] keys share names with the category toggles ([AnnotatedMap] Rooms...): look them up as 'Colors.<key>'
    return ('Colors.' if cstr(arg(0)) == 'Colors' else '') + cstr(arg(1))
def imp_GetPrivateProfileIntA():
    return state['ini'].get(ini_key(), arg(2))
def imp_GetPrivateProfileStringA():
    v = str(state['ini'].get(ini_key(), cstr(arg(2)))).encode() + b'\0'; u.mem_write(arg(3), v); return len(v) - 1
def imp_WritePrivateProfileStringA():
    state['written'][ini_key()] = cstr(arg(2)) if arg(2) else None; state.setdefault('files', []).append(cstr(arg(3))); return 1
def imp_CopyFileA():   # settings save: INI -> temp copy -> MoveFileExA over the INI
    state.setdefault('fs', []).append(('copy', cstr(arg(0)), cstr(arg(1)))); return state.get('copy_ok', 1)
def imp_GetFileAttributesA():
    return 0x20 if state.get('ini_exists', True) else 0xffffffff
def imp_MoveFileExA():
    state.setdefault('fs', []).append(('move', cstr(arg(0)), cstr(arg(1)), arg(2))); return state.get('move_ok', 1)
def imp_DeleteFileA():
    state.setdefault('fs', []).append(('delete', cstr(arg(0)))); return 1
def imp_LoadLibraryA():
    return 0   # no XInput in the harness: pad open is disabled, keyboard / cancel paths are exercised
def imp_GetProcAddress():
    return 0
def imp_lstrcmpiA():
    a, b = cstr(arg(0)).lower(), cstr(arg(1)).lower()
    return (a > b) - (a < b)
def imp_lstrlenA():
    return len(cstr(arg(0)))
def imp_wsprintfA():
    fmt = cstr(arg(1))
    vals = tuple(cstr(arg(i + 2)) if c == 's' else arg(i + 2) for i, c in enumerate(re.findall(r'%0?\d*([dxs])', fmt)))
    text = (fmt % vals).encode() + b'\0'
    u.mem_write(arg(0), text)
    return len(text) - 1
def imp_CreateFileA():
    state.setdefault('opened', set()).add(cstr(arg(0))); return 0xffffffff
def imp_GetWindowThreadProcessId():
    if arg(1): u.mem_write(arg(1), struct.pack('<I', 1234 if state.get('foreground', True) else 9999))
    return 1
def imp_GetCurrentProcessId():
    return 1234
def imp_GetAsyncKeyState():
    return 0x8000 if arg(0) in state['keys'] else 0
def imp_GetTickCount():
    keys = frozenset(state['keys'])
    if keys and keys != state.get('clock_keys') and not state.get('raw_clock'):   # a new press: human pace, past the 350 ms debounce
        state['clock'] = state.get('clock', 0) + 1000
    state['clock_keys'] = keys
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
assert state['opened'] == {'C:\\game\\RE1.AnnotatedMap.log'}, state['opened']  # ASI: log/INI beside the module
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
                f = [int(v) for v in re.findall(r'-?\d+', cur)]
                # Existing fixtures use the status/full views; omit the third view from their flattened indices.
                if len(f) in (41, 42): f = f[:41]; f = f[:12] + f[14:26] + f[32:39] + f[40:]
                out.append(f)
                continue
        if depth >= 1:
            cur += ch + (' ' if ch == '}' else '')
    return out


# OvMarker: kind,page,stage,slot,flagtype,chars,flag,icon, ico[2][2], lab[view][lang]{bid,x,y}
# -> (kind,page,stage,slot,flagtype,chars,flag,icon, en,ko, ix,iy, lx,ly, side) for the status view (English label position)
markers = [tuple(f[:8] + [f[12], f[15], f[8], f[9], f[13], f[14], f[26]])
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
lock = next(m for m in markers if m[0] == 2 and m[14] in (0, 3) and m[5] & 1 and isolated(m, [x for x in markers if x[1] == m[1] and x[0] in (2, 3)]))
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
state['keys'] = {ord(k) for k in '13457'}   # rooms, key items, files, puzzles toggled; 7 common items
draw()
layout_sample = canvas()
for language in range(2):
    for page in range(11):
        scene(page, visited=list(range(124)))
        state['keys'] = {ord('9') if language == 0 else LANG_KEY} if page == 0 else set()
        draw()
        img = canvas()
        for y in range(256 * S):
            row = img[y * WIDTH:(y + 1) * WIDTH]
            if 185 * S <= y < 216 * S:   # legend in the empty band below the HUD (x8..312, y185..216)
                assert not any(row[:8 * S]) and not any(row[312 * S:]), (language, page, y, 'legend outside its box')
            elif not 24 * S <= y < 128 * S:
                assert not any(row), (language, page, y, 'outside map vertically')
            else:
                assert not any(row[:32 * S]) and not any(row[192 * S:]), (language, page, y, 'outside map horizontally')
print('all 11 pages / both languages stay inside the native map panel')

# Dedicated mode is foreground-only, leaves settings intact, and returns on map close.
scene(0, visited=[5, 6])
state['foreground'] = False
state['keys'] = {0x09}
draw()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
state['foreground'] = True
state['keys'] = set()
draw()
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))   # 7 now opens the direct viewer (tested below); render the full-screen composition directly
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
u.mem_write(exports['ov_fullscreen'], bytes(4))
draw()
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
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
state['keys'] = {0x09}
state['foreground'] = False
call(target(0x48d0aa), 0)
assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] == 0
state['foreground'] = True
u.mem_write(0xC3523E, b'\x01')
call(target(0x48d0aa), 0)
assert struct.unpack('<H', u.mem_read(0xC3F8E0, 2))[0] == 0
state['keys'] = set(); call(target(0x48d0aa), 0)
u.mem_write(0xC3523E, b'\x00')
state['keys'] = {0x09}; call(target(0x48d0aa), 0)
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
state['keys'] = {0x09}; call(target(0x40b96b))
assert u.mem_read(0xC2E931, 1) == b'\x07'
call(target(0x40b91b))
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
state['keys'] = set()
# Live game: the hook moves the menu to state 1 before case 0 (map init 0x43ca60) runs, so the
# direct viewer must initialise the map itself (opened in the laboratory, it showed the mansion).
u.mem_write(0xC2E931, b'\x00')
call(target(0x48d0aa), 0)
state['keys'] = {0x09}; call(target(0x48d0aa), 0)
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
state['keys'] = {0x09}; call(target(0x40b96b)); call(target(0x40b91b)); state['keys'] = set()
# The open key (Tab) on the status map switches to the direct viewer: map init runs; status menu, selector and small map are not drawn.
u.mem_write(exports['ov_fullscreen'], bytes(4))
u.mem_write(0xC2E931, b'\x03')
state['keys'] = set(); draw()   # key released since the previous Tab
state['keys'] = {0x09}; draw(); state['keys'] = set()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 1 and u.mem_read(0xC2E931, 1) == b'\x00'
seen = []
hs = [u.hook_add(UC_HOOK_CODE, lambda uc, a, sz, ud: seen.append(a), begin=x, end=x) for x in (0x43ca60, 0x488310, 0x43be40, 0x43c7c0, 0x40bb60)]
call(target(0x40b6d6)); call(target(0x40b96b)); call(target(0x40b6d6)); call(target(0x40b96b))
for x in hs: u.hook_del(x)
assert 0x43ca60 in seen, 'direct viewer from 7 must run map init'
assert not set(seen) & {0x488310, 0x43be40, 0x43c7c0, 0x40bb60}, ('status menu / selector / small map drawn', [hex(a) for a in seen])
state['keys'] = {0x09}; call(target(0x40b96b))
assert u.mem_read(0xC2E931, 1) == b'\x07'
call(target(0x40b91b)); state['keys'] = set()
assert struct.unpack('<i', u.mem_read(exports['ov_fullscreen'], 4))[0] == 0
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
assert {0, 0.3, 0.2} <= alphas <= {0, 0.3, 0.2, 0.15, 0.65}, ('legend/walls opaque, names 70% / icons 80% visible, arrows pulse', alphas)
# Generated grid repeats every 8 logical pixels in both axes, with no interpolation/resizing.
raw_bg = bytes(map(int, hdr.split('ov_background_pixels[32768]={', 1)[1].split('}', 1)[0].split(',')))
def background_pixel(x, y):
    return (raw_bg[(y%256)*128 + (x%256)//2] >> ((x&1)*4)) & 15
assert all(background_pixel(x,y) == background_pixel(x%8,y%8) for y in range(240) for x in range(320))
# Fullscreen steady frames must not recreate/upload texture data.
u.mem_write(0x4b27f8, bytes(4))
assert not draw()[0], 'fullscreen reuploads textures on an unchanged frame'
print('bounded commands / unchanged-frame cache / 8px grid repeat / native 0.5 map alpha / names 70% / icons 80% visible ok')

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
# KeySide=0 (default, RE0 rule): only the door-centre key (side 3) is drawn
centre = next(f for f in full if f[0] == 2 and f[26] == 3 and f[6] == a1[6] and (f[2], f[3]) == (a1[2], a1[3]) and f[5] == a1[5])
assert key_at(centre, [own_bit]) and not key_at(a1, [own_bit]) and not key_at(a2, [dst_bit]), 'door-centre key by default'
u.mem_write(exports['ov_key_side'], struct.pack('<i', 1))   # KeySide=1: RE1 HD rule
assert not key_at(centre, [own_bit]), 'door-centre key hidden with KeySide=1'
assert key_at(a1, [own_bit]) and not key_at(a2, [own_bit]), 'own room visited -> key on the destination side'
assert key_at(a2, [dst_bit]) and not key_at(a1, [dst_bit]), 'only the destination visited -> key in the unvisited own room'
assert key_at(a1, [own_bit, dst_bit]), 'both visited -> destination side'
u.mem_write(exports['ov_key_side'], bytes(4))
print('lock key: door centre by default, KeySide=1 follows the unvisited room ok')

# Scope: 1 visited / 2 revealed by the floor map (Flg_7 bit 0x7C + n) / 3 all; room names always include revealed rooms.
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
def set_bit(addr, bit, on):
    w = bytearray(u.mem_read(addr + (bit >> 5) * 4, 4)); v = struct.unpack('<I', w)[0]
    v = v | (0x80000000 >> (bit & 31)) if on else v & ~(0x80000000 >> (bit & 31))
    u.mem_write(addr + (bit >> 5) * 4, struct.pack('<I', v))
# Use an unobscured Dining Room label for scope assertions.
room = next(f for f in full if f[0] == 1 and f[1] == 0 and f[18] >= 0 and d['rooms'][f'{f[2]}-{f[3]:02X}']['name_en'] == 'Dining Room')
def drawn(f, scope_val, revealed):
    scene(0, visited=[])
    set_bit(0xC387A0, 0x7C, revealed)                      # Map of 1F picked up
    u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1)); state['keys'] = set(); draw()
    for _ in range(3):                                      # key 9 cycles visited -> revealed -> all
        if state['written'].get('Scope') == str(scope_val): break
        state['keys'] = {ord('9')}; draw(); state['keys'] = set(); draw()
    assert state['written'].get('Scope') == str(scope_val)
    img = canvas()
    return any(bitmap_present(img, f[b], f[b + 1], f[b + 2]) for b in (18, 21)) if f[0] == 1 else bitmap_present(img, f[7], f[10], f[11])
assert not drawn(room, 1, False) and drawn(room, 1, True), 'room names show for revealed rooms even in scope 1'
item = next(f for f in full if f[0] == 6 and f[1] == 0 and f[5] & 1 and f[3] != room[3] and f[24] == 0xFFFF
            and drawn(f, 3, False))   # unguarded pickup whose icon is not covered by a neighbour
assert not drawn(item, 1, True) and drawn(item, 2, True) and not drawn(item, 2, False) and drawn(item, 3, False), 'item scope levels'
print('scope visited / revealed / all ok')

# Fullscreen map keys: OpenKey (Tab) opens at the gameplay gate; CloseKey (Esc) and the cancel action (0xC38712 bit 0x8000) close.
u.mem_write(0xC33090, struct.pack('<I', 0x90800008)); u.mem_write(0xC330AC, b'\x02'); u.mem_write(0xC3523E, b'\x00')
u.mem_write(0xC3AB90, struct.pack('<H', 0xffff)); u.mem_write(0xC38712, bytes(2))
def open_direct():
    u.mem_write(0xC3F8E0, bytes(2)); state['keys'] = set(); call(target(0x48d0aa), 0)
    state['keys'] = {0x09}; call(target(0x48d0aa), 0)
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

# Enemies (key 8): drawn until Flg 0xC3874C[kill] is set (em_set 0x4191b0 skips the spawn then); revisit-era markers only
# while Stage_no >= 5. Item names: H. Cover: a common item / enemy under a key item waits until that key item is gone.
state['keys'] = {ord('8')}; draw(); state['keys'] = set(); draw()
assert state['written'].get('Enemies') == '1'
def shown(f, page, visited, kills=(), stage_no=0, picked=(), full=False, jill=False):
    u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 0))
    scene(page, jill=jill, visited=visited, picked=picked); setbits(0xC3874C, kills, 8); u.mem_write(0xC386F0, bytes([stage_no]))
    if full: u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
    state['keys'] = set(); draw(); img = canvas()
    u.mem_write(0xC386F0, b'\0'); setbits(0xC3874C, [], 8)
    if full: return any(bitmap_present(img, f[b], f[b + 1], f[b + 2]) for b in (18, 21) if f[b] >= 0)
    x, y = ORIGIN[0] + f[8], ORIGIN[1] + f[9]
    if f[0] == 7: x, y = (x + S // 2) // S * S, (y + S // 2) // S * S   # enemy sprites sit on whole PSX pixels
    return bitmap_present(img, f[7], x, y)
vb = lambda f: [0, 32, 63, 82, 100][f[2]] + f[3]
foes = [f for f in full if f[0] == 7 and f[5] & 1 and f[24] == 0xFFFF and f[29] < 0 and f[6] != 255]
foe = next(f for f in foes if f[31] == 0 and shown(f, f[1], [vb(f)]))
assert not shown(foe, foe[1], [vb(foe)], kills=[foe[6]]), 'killed enemy still drawn'
late = next(f for f in foes if f[31] == 2 and shown(f, f[1], [vb(f)], stage_no=5))
assert not shown(late, late[1], [vb(late)], stage_no=0), 'mansion-revisit enemy drawn on the first visit'
print('enemy markers: kill flag / revisit era ok')
state['keys'] = {ord('H')}; draw(); state['keys'] = set()
assert state['written'].get('ItemNames') == '1', 'first [H] press from the default (hidden) shows all names (INI 1 = all)'
named = next(f for f in full if f[0] == 3 and f[5] & 1 and f[24] == 0xFFFF and f[18] >= 0 and f[1] == 0
             and shown(f, 0, [vb(f)], full=True))   # a key item name nothing draws over
for _ in range(2): state['keys'] = {ord('H')}; draw(); state['keys'] = set(); draw()   # all -> all but common -> hidden
assert state['written'].get('ItemNames') == '0' and not shown(named, 0, [vb(named)], full=True), 'H hides item names (INI 0 = off)'
covered = [f for f in full if f[29] >= 0 and f[0] == 6 and f[5] & 1 and f[24] == 0xFFFF]
if state['written'].get('CommonItems') != '1':
    state['keys'] = {ord('7')}; draw(); state['keys'] = set()   # common items on
assert state['written'].get('CommonItems') == '1'
ok = 0
for f in covered:
    top = full[f[29]]
    if top[24] != 0xFFFF or not top[5] & 1 or not shown(f, f[1], [vb(f), vb(top)], picked=[top[6]]):
        continue   # (its icon may also sit under a third marker)
    assert not shown(f, f[1], [vb(f), vb(top)]), 'common item drawn under a key item'
    ok += 1
assert ok, 'no covered common item to test'
print('item names (H) / covered markers ok')
# [~] folds the legend to one line ([~] LEGEND where the title was) and back
fold = [int(v) for v in hdr.split('ov_hint_fold[2]={', 1)[1].split('}', 1)[0].split(',')]
title = [int(v) for v in hdr.split('ov_full_legend_title[2]={', 1)[1].split('}', 1)[0].split(',')]
def legend_line():
    u.mem_write(exports['ov_fullscreen'], bytes(4)); scene(0); state['keys'] = set(); draw(); img = canvas()
    at = lambda b: any(bitmap_present(img, x, 8 * S, 185 * S) for x in b)
    return at(title), at(fold)
assert legend_line() == (True, False)
state['keys'] = {0xc0}; draw(); state['keys'] = set()
assert state['written'].get('Legend') == '0' and legend_line() == (False, True), 'legend not folded'
state['keys'] = {0xc0}; draw(); state['keys'] = set()
assert legend_line() == (True, False)
print('legend fold ([~]) ok')
# Names share the legend's CLUT (RE0 rule 4: one colour per category for legend row and names); enemies have their own CLUT.
pal_of = lambda name: list(map(int, hdr.split(f'{name}[16]={{', 1)[1].split('}', 1)[0].split(',')))
legend_pal = pal_of('ov_legend_palette')
enemy_icons = [int(v) for v in hdr.split('ov_enemy_icons[OV_ENEMY_KINDS]={', 1)[1].split('}', 1)[0].split(',')]
enemy_pals = [list(map(int, re.findall(r'\d+', g))) for g in
              re.findall(r'\{([0-9,]+)\}', hdr.split('ov_enemy_palettes[OV_ENEMY_KINDS][16]={', 1)[1].split('};', 1)[0])]
assert len(enemy_pals) == len(enemy_icons) == 14 and len({tuple(p) for p in enemy_pals}) == 14, 'one CLUT per enemy kind'
clut = lambda t: list(struct.unpack('<16H', t[20:52]))
def legend_tiles(names_on):
    while (state['written'].get('ItemNames') == '1') != names_on:   # names_on: all (INI 1); cycle all -> no common -> off
        state['keys'] = {ord('H')}; draw(); state['keys'] = set(); draw()
    u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1)); scene(named[1], visited=[vb(named)]); draw()
    return sum(clut(t) == legend_pal for t in uploads_now)
assert legend_tiles(True) > legend_tiles(False), 'item names are not drawn with the legend CLUT'
shown(foe, foe[1], [vb(foe)])
own = enemy_pals[enemy_icons.index(foe[7])]
assert any(clut(t) == own for t in uploads), 'enemy icon not uploaded with its own CLUT'
assert not any(clut(t) == own for t in uploads_now), 'enemy textures are re-uploaded every compose'
print('names in legend colours / one CLUT per enemy kind ok')

# Candidate 8: the game's confirm/examine action (mapped input bit 0x40) toggles a persisted zoom; panning moves the window by
# offset only (no compose, no upload); names/icons live in map-space tiles clipped to the window.
CONFIRM = 0x40
def menu_frame(held=0):
    u.mem_write(0xC38710, struct.pack('<H', held)); u.mem_write(0xC38712, bytes(2)); commands.clear(); u.mem_write(0x4b27f8, bytes(4))   # per-frame Add_sprt budget
    ups0 = len(uploads); call(target(0x40b96b)); return len(uploads) - ups0
def log_lines():
    return state.get('log', [])
open_direct()
u.mem_write(exports['ov_zoom'], bytes(4)); menu_frame(0)
assert 'B' not in [chr(k) for k in state['keys']]
state['keys'] = {ord('B')}; menu_frame(0); state['keys'] = set()
assert struct.unpack('<i', u.mem_read(exports['ov_zoom'], 4))[0] == 0, 'the old B key must no longer zoom'
menu_frame(CONFIRM)
assert struct.unpack('<i', u.mem_read(exports['ov_zoom'], 4))[0] == 1 and state['written'].get('Zoom', 'absent') is None, 'confirm must zoom in; the Zoom key is dropped from the INI, never written'
menu_frame(CONFIRM)   # still held: no second toggle
assert struct.unpack('<i', u.mem_read(exports['ov_zoom'], 4))[0] == 1
menu_frame(0); menu_frame(CONFIRM)
assert struct.unpack('<i', u.mem_read(exports['ov_zoom'], 4))[0] == 0
menu_frame(0); menu_frame(CONFIRM); menu_frame(0)
assert struct.unpack('<i', u.mem_read(exports['ov_zoom'], 4))[0] == 1
print('zoom on the game confirm action (not B), not persisted, edge triggered ok')
for _ in range(8): menu_frame(0)   # settle uploads
assert struct.unpack_from('<4h', commands[2], 8) == (0, 0, 319, 203) and struct.unpack_from('<4h', commands[3], 8) == (0, 0, 319, 203), 'zoom viewport: top of screen down to the legend'
assert all(max(struct.unpack_from('<4H', c, 16)) < 256 for c in commands)
print('zoom cropped terrain and outline / 256 UV limit ok')
page_before = u.mem_read(0xB38DE6, 1)
def pan_hold(bit, frames, start=None, axis='x'):
    if start is not None: u.mem_write(exports['ov_pan_' + axis], struct.pack('<i', start))
    menu_frame(0); n = 0
    for _ in range(frames): n += menu_frame(bit)
    return n, struct.unpack('<i', u.mem_read(exports['ov_pan_' + axis], 4))[0]
for axis, bit, start, expected in (('x', 8, -80, -80), ('x', 2, 272, 272), ('y', 1, -48, -48), ('y', 4, 244, 244)):
    assert pan_hold(bit, 1, start, axis)[1] == expected
    assert u.mem_read(0xB38DE6, 1) == page_before
n, pan = pan_hold(2, 1, 64, 'x'); assert pan == 72, pan   # a tap: 8 px
# held: 250 ms delay, then 4 px per frame. The harness clock advances 34 ms per call.
n, pan = pan_hold(2, 20, 64, 'x'); assert 64 + 8 < pan <= 64 + 8 + 4 * 20, pan
assert (pan - 72) % 4 == 0 and pan % 4 == 0, 'terrain/outline UV units need a multiple of 4'
menu_frame(0)
# no recompose while panning: nothing but the few tiles entering the window may upload, and the log has no compose line
composes0 = state.get('composes', 0)
tot = 0
for x in range(100, 140, 4):
    u.mem_write(exports['ov_pan_x'], struct.pack('<i', x)); tot += menu_frame(0)
assert tot <= 12, f'panning 40 px uploaded {tot} textures (a recompose would upload dozens)'
u.mem_write(0xC38710, bytes(2)); u.mem_write(0xC38712, bytes(2))
print('zoom pan: bounds, 8 px tap / 4 px hold, multiples of 4, offset only (uploads for 40 px of pan: %d) ok' % tot)

# deferred uploads: with a small budget the first frame uploads at most budget + the fixed textures, later frames finish the rest.
for _ in range(10): menu_frame(0)
u.mem_write(exports['ov_zoom'], bytes(4)); u.mem_write(exports['ov_upload_budget'], struct.pack('<i', 12))
scene(1, visited=list(range(124))); open_direct()
def ensure(key, name, want):
    for _ in range(4):
        if state['written'].get(name) == want: return
        state['keys'] = {ord(key)}; menu_frame(0); state['keys'] = set(); menu_frame(0)
    assert state['written'].get(name) == want, (name, state['written'].get(name))
for key, name in (('1', 'Rooms'), ('2', 'Locks'), ('3', 'KeyItems'), ('4', 'Documents'), ('5', 'Puzzles'), ('6', 'Events'), ('7', 'CommonItems'), ('8', 'Enemies')):
    ensure(key, name, '1')
ensure('9', 'Scope', '3')
for _ in range(40): menu_frame(0)
state['keys'] = {LANG_KEY}   # language switch: every name tile changes, so a lot has to be uploaded
first = menu_frame(0); frames = 1; total = first; state['keys'] = set()
while frames < 40:
    more = menu_frame(0)
    if not more: break
    total += more; frames += 1
assert first <= 12 + 4 and total > first and frames > 1, (first, total, frames)
assert menu_frame(0) == 0
print('deferred uploads: first frame %d textures, %d in %d frames, then none ok' % (first, total, frames))
u.mem_write(exports['ov_upload_budget'], struct.pack('<i', 200))

# Candidate 9: the zoom viewport is the whole map area. Legend shown: screen top .. legend top (y 204); legend folded with [~]: ..
# screen bottom (240). Pan bounds follow, and the window never slices a name/icon box: such a marker is left out whole.
def terrain_rect():
    for _ in range(3): menu_frame(0)
    return struct.unpack_from('<4h', commands[2], 8)
def read_i32(addr): return struct.unpack('<i', u.mem_read(addr, 4))[0]
def pan_to(x, y):
    u.mem_write(exports['ov_pan_x'], struct.pack('<i', x)); u.mem_write(exports['ov_pan_y'], struct.pack('<i', y)); menu_frame(0)
    return read_i32(exports['ov_pan_x']), read_i32(exports['ov_pan_y'])
u.mem_write(exports['ov_zoom'], struct.pack('<i', 1))
# pan bounds: a quarter viewport past each canvas edge (x -80..272; y -48..244 with the legend shown, -60..220 folded)
assert pan_to(-999, -999) == (-80, -48) and pan_to(999, 999) == (272, 244), 'legend shown pan bounds'
pan_to(96, 96); assert terrain_rect() == (0, 0, 319, 203), 'legend shown: window 0..204'
state['keys'] = {0xC0}; menu_frame(0); state['keys'] = set()   # [~] folds the legend
pan_to(96, 96); assert terrain_rect() == (0, 0, 319, 239), 'legend folded: viewport reaches the screen bottom'
assert pan_to(-999, -999) == (-80, -60) and pan_to(999, 999) == (272, 220), 'legend folded pan bounds'
pan_to(96, 96); terrain_rect()
uvs = [struct.unpack_from('<4H', commands[i], 16) for i in (2, 3)]
assert uvs[0][3] - uvs[0][1] == 59 and uvs[1][3] - uvs[1][1] == 119, 'terrain/outline UV rows cover the taller window'
# margins: the canvas edge is drawn inside the window and terrain/outline quads shrink to the part of the map in view
pan_to(-80, 96); assert terrain_rect() == (80, 0, 319, 239) and struct.unpack_from('<4H', commands[2], 16)[0] == 0, 'left margin'
pan_to(272, 96); assert terrain_rect() == (0, 0, 239, 239), 'right margin'
pan_to(96, -60); assert terrain_rect() == (0, 60, 319, 239), 'top margin'
pan_to(96, 220); assert terrain_rect() == (0, 0, 319, 179), 'bottom margin'
for _ in range(30): menu_frame(0)
pan_to(96, 96)
state['keys'] = {0xC0}; state['clock'] = state.get('clock', 0) + 2000; menu_frame(0); state['keys'] = set()   # legend shown again
pan_to(96, 96); assert terrain_rect() == (0, 0, 319, 203)
pan_to(96, 244); u.mem_write(exports['ov_pan_y'], struct.pack('<i', 244))
state['keys'] = {0xC0}; state['clock'] = state.get('clock', 0) + 2000; menu_frame(0); state['keys'] = set()   # folded: 244 re-clamped to 220
assert read_i32(exports['ov_pan_y']) == 220, 'folding the legend re-clamps the pan'
state['keys'] = {0xC0}; state['clock'] = state.get('clock', 0) + 2000; menu_frame(0); state['keys'] = set(); menu_frame(0)
print('zoom viewport: legend shown 0..204 / folded 0..240, pan bounds with margins (x -80..272, y -48..244 / -60..220), UV rows ok')

def read_i32(addr): return struct.unpack('<i', u.mem_read(addr, 4))[0]
def zboxes():
    n = read_i32(exports['ov_zbox_n'])
    return [struct.unpack('<6h', u.mem_read(exports['ov_zbox'] + 12 * i, 12)) for i in range(n)]
def cuts():
    n = read_i32(exports['ov_cut_n'])
    return [struct.unpack('<5h', u.mem_read(exports['ov_cut'] + 10 * i, 10)) for i in range(n)]
ensure('H', 'ItemNames', '1'); u.mem_write(0xB38DE6, b'\x00')   # Mansion 1F, item names on (all)
menu_frame(CONFIRM); menu_frame(0); menu_frame(CONFIRM); menu_frame(0)   # zoom off and on: a fresh zoom compose records the boxes
assert read_i32(exports['ov_zoom']) == 1
for _ in range(40): menu_frame(0)
boxes = zboxes()
assert len(boxes) > 20, 'zoom names/icons/lines must be recorded as boxes'
LEGEND_CLUT = list(map(int, hdr.split('ov_legend_palette[16]={', 1)[1].split('}', 1)[0].split(',')))
def lit_pixels_in(rect_psx, sprites_now_, uploads_now_):
    """Texels of name-layer sprites (legend CLUT, above the legend) inside a screen rect; sprites include their UV crop."""
    x0, y0, x1, y1 = (v * S for v in rect_psx)
    hits = 0
    by_tex = {0x5000 + i + 1: t for i, t in enumerate(uploads)}
    for sp in sprites_now_:
        t = by_tex.get(sp['tex'])
        if t is None or sp['y'] >= 204 or sp['wh'][0] > TILE_PSX or sp['wh'][1] > TILE_PSX: continue
        if list(struct.unpack_from('<16H', t, 20)) != LEGEND_CLUT: continue   # name layer / legend only
        sx0, sy0 = sp['x'] * S, sp['y'] * S
        w, h = sp['wh'][0] * S, sp['wh'][1] * S
        ix0, iy0, ix1, iy1 = max(x0, sx0), max(y0, sy0), min(x1, sx0 + w), min(y1, sy0 + h)
        if ix0 >= ix1 or iy0 >= iy1: continue
        px = t[64:]; tw = struct.unpack_from('<H', t, 60)[0] * 4
        for yy in range(iy0, iy1):
            ty = sp['uv'][1] * S + (yy - sy0)
            for xx in range(ix0, ix1):
                tx = sp['uv'][0] * S + (xx - sx0)
                if (px[ty * (tw // 2) + tx // 2] >> ((tx & 1) * 4)) & 15: hits += 1
    return hits
# find pans where a box straddles each edge, then check nothing of the cut markers is drawn inside their boxes
seen = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}; checked = 0
for pan_x, pan_y in ((96, 60), (96, 61 // 4 * 4), (40, 100), (150, 120), (0, 0), (192, 196), (60, 24), (130, 80), (170, 150), (20, 180), (-60, 20), (250, 200)):
    u.mem_write(exports['ov_pan_x'], struct.pack('<i', pan_x)); u.mem_write(exports['ov_pan_y'], struct.pack('<i', pan_y))
    for _ in range(12): menu_frame(0)
    n0 = len(sprites); menu_frame(0)
    frame_sprites = sprites[-1:] and sprites[n0:]
    pan_x, pan_y = read_i32(exports['ov_pan_x']), read_i32(exports['ov_pan_y'])
    for x0, y0, x1, y1, layer_ in cuts():
        if layer_ == 0:
            checked += 1
            assert lit_pixels_in((x0, y0, x1, y1), frame_sprites, uploads) == 0, ('name box sliced instead of cut', (pan_x, pan_y), (x0, y0, x1, y1))
        seen['top'] += y0 < 0 + 0 < y1; seen['bottom'] += y0 < 204 < y1; seen['left'] += x0 < 0 < x1; seen['right'] += x0 < 320 < x1
assert checked > 0 and (seen['top'] or seen['bottom'] or seen['left'] or seen['right']), ('no pan produced a straddling box', seen)
print('zoom name clipping: %d name/line boxes cut whole (edges hit %s), no glyph drawn inside them ok' % (checked, seen))

# Candidate 10: every map open starts at 1x (zoom and pan reset, nothing persisted); the folded legend hint sits at the screen's
# bottom-left on its own box, in ko/en, legend shown/folded, 1x/2x.
open_direct()
if read_i32(exports['ov_zoom']) == 0: menu_frame(CONFIRM); menu_frame(0)
assert read_i32(exports['ov_zoom']) == 1
u.mem_write(exports['ov_pan_x'], struct.pack('<i', 40)); u.mem_write(exports['ov_pan_y'], struct.pack('<i', 40)); menu_frame(0)
open_direct()   # the map is closed and opened again
assert read_i32(exports['ov_zoom']) == 0, 'a new map open must start at 1x'
assert (read_i32(exports['ov_pan_x']), read_i32(exports['ov_pan_y'])) == (96, 96 if state['written'].get('Legend') == '1' else 80), 'pan returns to the middle of the zoom canvas (y 96 legend shown, 80 folded)'
menu_frame(0); assert read_i32(exports['ov_zoom']) == 0
print('map always opens at 1x (zoom and pan reset on open) ok')

LEGEND_CLUT = list(map(int, hdr.split('ov_legend_palette[16]={', 1)[1].split('}', 1)[0].split(',')))
def legend_bbox():
    """Bounding box (texels) of everything drawn with the legend CLUT this frame; with All off that is only the legend layer."""
    n0 = len(sprites); menu_frame(0); frame = sprites[n0:]
    by_tex = {0x5000 + i + 1: t for i, t in enumerate(uploads)}
    x0 = y0 = 10 ** 9; x1 = y1 = -1
    for sp in frame:
        t = by_tex.get(sp['tex'])
        if t is None or list(struct.unpack_from('<16H', t, 20)) != LEGEND_CLUT or sp['wh'][0] > TILE_PSX: continue
        px = t[64:]; tw = struct.unpack_from('<H', t, 60)[0] * 4
        for yy in range(sp['wh'][1] * S):
            ty = sp['uv'][1] * S + yy; row = px[ty * (tw // 2):(ty + 1) * (tw // 2)]
            for xx in range(sp['wh'][0] * S):
                tx = sp['uv'][0] * S + xx
                if (row[tx // 2] >> ((tx & 1) * 4)) & 15:
                    X, Y = sp['x'] * S + xx, sp['y'] * S + yy
                    x0, y0, x1, y1 = min(x0, X), min(y0, Y), max(x1, X), max(y1, Y)
    return x0, y0, x1, y1
def setting(key, name, want):
    for _ in range(4):
        if state['written'].get(name) == want: return
        state['clock'] = state.get('clock', 0) + 2000
        state['keys'] = {key}; menu_frame(0); state['keys'] = set(); menu_frame(0)
    assert state['written'].get(name) == want, (name, state['written'].get(name))
def set_zoom(want):
    if read_i32(exports['ov_zoom']) != want: menu_frame(CONFIRM); menu_frame(0)
    assert read_i32(exports['ov_zoom']) == want
setting(ord('0'), 'All', '0')   # markers off: only the legend layer uses the legend CLUT
checked = 0
for lang, name in (('en', 'English'), ('ko', 'Korean')):
    setting(LANG_KEY, 'Language', lang)
    for zoom in (0, 1):
        set_zoom(zoom)
        for legend in ('1', '0'):
            setting(0xC0, 'Legend', legend)
            for _ in range(12): menu_frame(0)
            x0, y0, x1, y1 = legend_bbox()
            if legend == '0':   # folded: one line at the bottom-left, its own box, nothing left at the old title position
                assert x0 == 8 * S and 238 * S <= y1 + 1 <= 240 * S and y1 + 1 - y0 <= 20 * S and y0 >= 220 * S, (lang, zoom, (x0, y0, x1, y1))
                assert x1 - x0 < 90 * S, 'the folded hint is a short single line'
            else:               # shown: the panel starts at 205 with its title
                assert 205 * S <= y0 <= 207 * S, (lang, zoom, y0)
            checked += 1
set_zoom(0); setting(0xC0, 'Legend', '1'); setting(ord('0'), 'All', '1')
print('folded legend hint at the screen bottom-left (ko/en, shown/folded, 1x/2x): %d cases ok' % checked)

# Candidate 12: HD-style icons on the FULL map only (INI HdIcons, default on); the status screen keeps the pixel icons.
HD_PALS = [[int(v) for v in g.split(',')] for g in re.findall(r'\{([0-9,]+)\}', hdr.split('ov_hd_palettes[OV_HD_KINDS][16]={', 1)[1].split('};', 1)[0])]
ENEMY_PALS = [[int(v) for v in g.split(',')] for g in re.findall(r'\{([0-9,]+)\}', hdr.split('ov_enemy_palettes[OV_ENEMY_KINDS][16]={', 1)[1].split('};', 1)[0])]
assert len(HD_PALS) >= 30 and not any(p in ENEMY_PALS for p in HD_PALS)
def frame_sprites(fn):
    n0, u0 = len(sprites), len(uploads); fn()
    return sprites[n0:], len(uploads) - u0
def hd_sprites_of(frame):
    by_tex = {0x5000 + i + 1: t for i, t in enumerate(uploads)}
    out = []
    for sp in frame:
        t = by_tex.get(sp['tex'])
        if t is not None and list(struct.unpack_from('<16H', t, 20)) in HD_PALS: out.append(sp)
    return out
def settle_frames(n=40):
    for _ in range(n): menu_frame(0)
def reopen_page(page, jill=False):
    u.mem_write(0xC33090, struct.pack('<I', (0x90800008 | 0x800000) if jill else 0x90800008)); u.mem_write(0xB38DE6, bytes([page]))
    state['clock'] = state.get('clock', 0) + 3000
    state['keys'] = {LANG_KEY}; menu_frame(0); state['keys'] = set(); settle_frames(4)
    state['clock'] = state.get('clock', 0) + 3000
    state['keys'] = {LANG_KEY}; menu_frame(0); state['keys'] = set(); settle_frames(30)
set_zoom(0)
setting(0xC0, 'Legend', '1'); setting(ord('0'), 'All', '1')
u.mem_write(exports['ov_hd_on'], struct.pack('<i', 1)); u.mem_write(exports['ov_upload_budget'], struct.pack('<i', 200))
worst = (0, None)
for page in (0, 1, 3, 5):
    for jill in (False, True):
        reopen_page(page, jill)
        frame, _ = frame_sprites(lambda: menu_frame(0))
        hd = hd_sprites_of(frame)
        worst = max(worst, (len(frame), (page, jill, len(hd))))
        assert len(frame) <= 300 - 5, ('sprite cap (Add_sprt 300 per frame)', page, jill, len(frame))
        assert page != 0 or len(hd) > 20, ('HD sprites on Mansion 1F', len(hd))
print('HD icons full map: worst frame %d sprites (page, jill, HD sprites) = %s of the 300 cap' % worst)
# each distinct HD icon is uploaded once (own texture + CLUT), not once per marker
reopen_page(0); hd_up = [t for t in uploads if list(struct.unpack_from('<16H', t, 20)) in HD_PALS]
assert len(hd_up) == len({bytes(t) for t in hd_up}) <= len(HD_PALS), ('HD textures uploaded more than once', len(hd_up))
# the status screen is unchanged: no HD sprite, pixel icons still drawn
u.mem_write(exports['ov_fullscreen'], bytes(4)); scene(0, visited=list(range(124)))
frame, _ = frame_sprites(draw)
assert frame and not hd_sprites_of(frame), 'status screen must not draw HD icons'
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
# HdIcons off: the full map falls back to the pixel icons
u.mem_write(exports['ov_hd_on'], bytes(4)); reopen_page(0)
frame, _ = frame_sprites(lambda: menu_frame(0)); assert not hd_sprites_of(frame), 'HdIcons=0 must draw no HD sprite'
u.mem_write(exports['ov_hd_on'], struct.pack('<i', 1))
# uploads stay inside the per-frame budget: with budget 12 the HD textures arrive over several frames
u.mem_write(exports['ov_upload_budget'], struct.pack('<i', 12))
state['clock'] = state.get('clock', 0) + 3000; state['keys'] = {LANG_KEY}
per_frame = []
for i in range(30):
    _, n = frame_sprites(lambda: menu_frame(0)); per_frame.append(n); state['keys'] = set()
assert max(per_frame) <= 12 + 4, ('uploads in one frame exceed the budget (12 + terrain/outline/background)', per_frame)
print('HD uploads per frame with budget 12:', per_frame[:12], 'max', max(per_frame))
u.mem_write(exports['ov_upload_budget'], struct.pack('<i', 200)); settle_frames(10)
# zoom: HD icons are map-space sprites; an HD icon the window edge would slice is skipped together with its name
set_zoom(1); pan_to(96, 60); settle_frames(20)
frame, _ = frame_sprites(lambda: menu_frame(0)); assert hd_sprites_of(frame), 'HD sprites in the zoomed view'
for x, y in ((-60, 20), (200, 120), (272, 244)):
    pan_to(x, y); settle_frames(6); frame, _ = frame_sprites(lambda: menu_frame(0))
    for sp in hd_sprites_of(frame):
        w, h = sp['wh']; assert sp['x'] >= 0 and sp['y'] >= 0 and sp['x'] + w <= 320 and sp['y'] + h <= 240, ('HD sprite sliced by the window edge', (x, y), sp['x'], sp['y'])
set_zoom(0)
print('HD icons: full map only, one texture per distinct icon, status screen unchanged, zoom clips whole sprites ok')

# Candidate 14: HD icon size (+20 % at 1x, +50 % over the zoom scale), [H] item names in three states.
def sprite_quads(fn):
    """[(sprite, quad (x0, y0, x1, y1))] of one frame; commands and sprites are recorded in the same order."""
    n0 = len(sprites); fn(); frame = sprites[n0:]
    assert len(frame) == len(commands), (len(frame), len(commands))
    return [(sp, struct.unpack_from('<4h', c, 8)) for sp, c in zip(frame, commands)]
set_zoom(0); setting(0xC0, 'Legend', '1'); setting(ord('0'), 'All', '1'); reopen_page(0)
u.mem_write(exports['ov_hd_on'], struct.pack('<i', 1)); settle_frames(12)
quads = sprite_quads(lambda: menu_frame(0))
hd_q = [q for sp, q in quads if sp in hd_sprites_of([s_ for s_, _ in quads])]
assert hd_q and {q[2] - q[0] + 1 for q in hd_q} == {5} and {q[3] - q[1] + 1 for q in hd_q} == {5}, ('HD icons 5 PSX px (4 x 1.2) at 1x', {q[2] - q[0] + 1 for q in hd_q})
set_zoom(1); pan_to(96, 96); settle_frames(20)
quads = sprite_quads(lambda: menu_frame(0))
hd_q = [q for sp, q in quads if sp in hd_sprites_of([s_ for s_, _ in quads])]
assert hd_q and {q[2] - q[0] + 1 for q in hd_q} == {9}, ('HD icons 9 PSX px (4 x 1.43 x 1.5) when zoomed', {q[2] - q[0] + 1 for q in hd_q})
set_zoom(0)
print('HD icon size: 5 PSX px at 1x (+20%%), 9 PSX px zoomed (+50%% over 1.43), %d HD sprites checked' % len(hd_q))

def name_texels():
    """Legend-CLUT texels above the legend (y < 204): the name layer (and leader lines); nothing else uses that CLUT there."""
    n0 = len(sprites); menu_frame(0); frame = sprites[n0:]
    by_tex = {0x5000 + i + 1: t for i, t in enumerate(uploads)}
    total = 0
    for sp in frame:
        t = by_tex.get(sp['tex'])
        if t is None or list(struct.unpack_from('<16H', t, 20)) != LEGEND_CLUT or sp['wh'][0] > TILE_PSX: continue
        px = t[64:]; tw = struct.unpack_from('<H', t, 60)[0] * 4
        for yy in range(min(sp['wh'][1] * S, 204 * S - sp['y'] * S)):
            ty = sp['uv'][1] * S + yy; row = px[ty * (tw // 2):(ty + 1) * (tw // 2)]
            for xx in range(sp['wh'][0] * S):
                tx = sp['uv'][0] * S + xx
                total += (row[tx // 2] >> ((tx & 1) * 4)) & 15 != 0
    return total
def names_mode(mode):
    ensure('H', 'ItemNames', {0: '1', 1: '2', 2: '0'}[mode]); settle_frames(6)   # mode: 0 all, 1 no common, 2 off -> INI 1 / 2 / 0
    return name_texels()
def only(**on):   # category toggles: Rooms, Locks, KeyItems, Documents, Puzzles, Enemies, CommonItems
    for key, name in (('1', 'Rooms'), ('2', 'Locks'), ('3', 'KeyItems'), ('4', 'Documents'), ('5', 'Puzzles'), ('6', 'Events'), ('7', 'CommonItems'), ('8', 'Enemies')):
        ensure(key, name, '1' if on.get(name) else '0')
    settle_frames(6)
only(CommonItems=True)
c0, c1, c2 = names_mode(0), names_mode(1), names_mode(2)
assert c0 > 0 and c1 == 0 and c2 == 0, ('common items only: names in mode all / no common / off', c0, c1, c2)
only(KeyItems=True)
k0, k1, k2 = names_mode(0), names_mode(1), names_mode(2)
assert k0 > 0 and k1 == k0 and k2 == 0, ('key items: names in mode all / no common / off', k0, k1, k2)
only(Rooms=True, CommonItems=True)
r0, r1, r2 = names_mode(0), names_mode(1), names_mode(2)
assert r2 > 0 and r0 > r2 and r1 == r2, ('room names stay in every mode; common names only in mode all', r0, r1, r2)
print('[H] item names: all / all but common / off: common-only %s, key-only %s, rooms+common %s texels ok' % ((c0, c1, c2), (k0, k1, k2), (r0, r1, r2)))
only(Rooms=True, Locks=True, KeyItems=True, Documents=True, Puzzles=True, CommonItems=True, Enemies=True); ensure('H', 'ItemNames', '0')

# ---- Candidate 16: legend order + [\] language pairing, events (flag hidden), names clear of their scaled icon at IconSize 100 / 150 / 200
def ints_in(text): return [int(v) for v in re.findall(r'-?\d+', text)]
cells = [tuple(ints_in(c)) for c in re.findall(r'\{(-?\d+,-?\d+,-?\d+)\}', hdr.split('ov_full_cells[', 1)[1].split('};', 1)[0])]
assert [c[0] for c in cells] == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 18, 10, 11, 16, 12, 13, 15], 'full legend order: [0]..[9], [H], [\\], then the hints'
h_cell, l_cell = cells[10], cells[11]
assert h_cell[1] == l_cell[1] and l_cell[2] > h_cell[2], '[\\] sits in the same column as [H], one row below'
assert l_cell[2] - h_cell[2] == cells[1][2] - cells[0][2], '[\\] uses the same row step as [H]'
def short_pairs(name): return [tuple(ints_in(c)) for c in re.findall(r'\{(-?\d+,-?\d+)\}', hdr.split(name, 1)[1].split('};', 1)[0])]
names_ids, lang_ids = short_pairs('ov_hint_names[3][2]={'), [tuple(ints_in(hdr.split('ov_hint_lang[2]={', 1)[1].split('}', 1)[0]))]
def texel_set(bid):
    w, h, off = bitmaps[bid]; row = (w + 1) // 2
    return {(PIXELS[off + j * row + i // 2] >> ((i & 1) * 4)) & 15 for j in range(h) for i in range(w)} - {0}
for lang in (0, 1):
    assert {bitmaps[b[lang]][1] for b in names_ids + lang_ids} == {bitmaps[names_ids[0][lang]][1]}, 'the [\\] label has the [H] label height'
    assert {frozenset(texel_set(b[lang])) for b in names_ids + lang_ids} == {frozenset({1, 15})}, 'same colour (white text, black outline) as [H]'
print('legend order [0]..[9] [H] [\\\\] and the [\\\\] / [H] pairing ok')

# events: kind 8 markers, hidden once their flag is set (group 0 / 1 in ov_conds), per character, era 2 only on a mansion revisit
conds_all = [tuple(ints_in(c)) for c in re.findall(r'\{(\d+,\d+,\d+)\}', hdr.split('ov_conds[][3]={', 1)[1].split('};', 1)[0])]
events = [f for f in full if f[0] == 8]
assert len(events) == len(d['events']) >= 3, (len(events), len(d['events']))
def press_draw(*keys, want=None, name=None):   # map-draw hook path (status screen / fullscreen flag as set), debounce-safe clock
    for _ in range(4 if name else 1):   # with a target: press until the saved value matches; without: exactly one press
        if name and state['written'].get(name) == want: return
        state['clock'] = state.get('clock', 0) + 2000; state['keys'] = set(keys); draw(); state['keys'] = set(); draw()
    assert not name or state['written'].get(name) == want, (name, state['written'].get(name))
u.mem_write(exports['ov_fullscreen'], bytes(4))
press_draw(ord('6'), want='1', name='Events'); press_draw(ord('0'), want='1', name='All'); press_draw(ord('9'), want='1', name='Scope')   # scope: visited rooms
def ev_shown(f, flag_on, visited=True, stage_no=0):
    grp, bit, _ = conds_all[f[6]]
    scene(f[1], jill=bool(f[5] & 2), visited=[vb(f)] if visited else [])
    setbits({0: 0xC38790, 1: 0xC38724}[grp], [bit] if flag_on else [], 8)
    u.mem_write(0xC386F0, bytes([stage_no])); state['keys'] = set(); draw(); img = canvas()
    u.mem_write(0xC386F0, b'\0'); setbits({0: 0xC38790, 1: 0xC38724}[grp], [], 8)
    return bitmap_present(img, f[7], ORIGIN[0] + f[8], ORIGIN[1] + f[9])
seen = 0
for f in events:
    stage_no = 5 if f[31] == 2 else 0
    if not ev_shown(f, False, stage_no=stage_no): continue   # an icon another marker covers cannot be asserted
    assert not ev_shown(f, True, stage_no=stage_no), ('event still shown after its flag', f[:8])
    assert not ev_shown(f, False, visited=False, stage_no=stage_no), 'event shown in an unvisited room'
    if f[31] == 2: assert not ev_shown(f, False, stage_no=0), 'revisit-era event shown on the first visit'
    seen += 1
assert seen >= 2, seen
press_draw(ord('6'), want='0', name='Events')
assert not any(ev_shown(f, False, stage_no=5 if f[31] == 2 else 0) for f in events), 'Events off hides every event marker'
press_draw(ord('6'), want='1', name='Events'); press_draw(ord('9'), want='3', name='Scope')
print('events: shown until their flag is set, visited rooms only, per character / era, key 6 toggles them: %d checked' % seen)

# candidate 17: every event / puzzle marker carries a completion flag and sits inside its own map room
masks = {(pg['stage'], r['slot']): {tuple(p) for p in r['mask']} for pg in json.loads((ROOT / 'data/map_rooms.json').read_text())['pages'] for r in pg['rooms']}
NO_FLAG = {'Flare'}   # no persistent flag in their rooms' scripts (docs/re0-alignment-review.md)
for e in d['events']:
    assert e['flag'][0] in (0, 1) and e['name_en'].startswith('Event: ') and e['name_ko'].startswith('이벤트: '), e
for kind, m, has_flag in [('event', e['map'], True) for e in d['events']] + [
        ('puzzle', p['map'], bool(p['solved_when'] or p['solved_by_char'])) for p in d['puzzles'] if p['map'] and p['name_en'] not in NO_FLAG]:
    assert has_flag, (kind, m)
    assert (int(m['px']), int(m['py'])) in masks[(m['stage'], m['slot'])], ('marker outside its room', kind, m)
assert sum(1 for f in full if f[0] == 5 and f[4] == 0) <= 2 * len(NO_FLAG), 'puzzle markers without a completion flag'
assert next(p for p in d['puzzles'] if p['name_en'] == 'Door code')['solved_when'] == [[0, 33, 1]], 'door code: Drug Storeroom door unlock flag'
boss = [e for e in d['enemies'] if e['kind'] == 'plant42']
assert len(boss) == 1 and boss[0]['kill'] == 96, ('Plant 42: one marker, hidden by its kill flag Flg_3[96]', boss)
print('events / puzzles: every marker has a flag and lies in its room (%d events)' % len(d['events']))

# names against the scaled icon: IconSize 100 / 150 / 200, HD sprites and pixel icons, both views and both languages
body = hdr.split('ov_markers[]={', 1)[1].split('};', 1)[0]
vals = ints_in(body); assert len(vals) % 42 == 0
M = [vals[i:i + 42] for i in range(0, len(vals), 42)]   # kind,page,stage,slot,flagtype,chars,flag,icon, ico[3][2], lab[3][2][3], guard[2], side,tstage,tslot, cover[3], era, hd
def hd_box_px(w, zoom): return ((w // S * (214 if zoom else 120) + 50) // 100) * S
def set_icon_size(pct):
    for _ in range(20):
        if state['written'].get('IconSize') == str(pct): return
        want_up = int(state['written'].get('IconSize', '100')) < pct
        press_draw(0x10, 0xbb if want_up else 0xbd)
    assert state['written'].get('IconSize') == str(pct)
def s32(v): return v - (1 << 32) if v >> 31 else v
def icon_box(m, view, hd_on):
    hd = hd_on and view > 0 and m[41] >= 0 and m[0] != 7
    w, h = bitmaps[m[41] if hd else m[7]][:2]
    bw, bh = (hd_box_px(w, view == 2), hd_box_px(h, view == 2)) if hd else ((w * 143 // 100, h * 143 // 100) if view == 2 else (w, h))
    return m[8 + 2 * view], m[9 + 2 * view], bw, bh
def area(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
report = {}
for hd_on in (0, 1):
    u.mem_write(exports['ov_hd_on'], struct.pack('<i', hd_on))
    for pct in (100, 150, 200):
        set_icon_size(pct); bad, checked, cache = [], 0, {}
        for m in M:
            if m[7] < 0 or m[0] in (1, 7, 8) and False: continue
            for view in (1, 2):
                ix, iy, bw, bh = icon_box(m, view, hd_on)
                for lang in (0, 1):
                    bid, lx, ly = m[14 + view * 6 + lang * 3: 17 + view * 6 + lang * 3]
                    if bid < 0 or m[0] == 1: continue
                    lw, lh = bitmaps[bid][:2]
                    key = (ix, iy, bw, bh, lx, ly, lw, lh)
                    if key not in cache:
                        cache[key] = (s32(call(exports['ov_name_offset'], 0, *key)), s32(call(exports['ov_name_offset'], 1, *key)))
                    dx, dy = cache[key]
                    cx, cy, k = ix + bw / 2, iy + bh / 2, pct / 100
                    icon = (cx - bw * k / 2, cy - bh * k / 2, cx + bw * k / 2, cy + bh * k / 2)
                    name = (lx + dx, ly + dy, lx + dx + lw, ly + dy + lh)
                    checked += 1
                    if area(icon, name) > 0.5 * S * S: bad.append((m[1], m[0], view, lang, round(area(icon, name) / S / S, 1)))
        report[(hd_on, pct)] = (checked, len(bad))
        assert not bad, ('names covered by their own icon', hd_on, pct, bad[:8], len(bad))
u.mem_write(exports['ov_hd_on'], bytes(4)); set_icon_size(100)
print('names clear of their own scaled icon at IconSize 100 / 150 / 200 (pixel + HD icons, fullscreen + zoom, ko + en):', {k: v[0] for k, v in report.items()})

# candidate 18: event markers carry no name (RE0 rule): every label slot of a kind-8 marker is empty in every view and language
ev_rows = [m for m in M if m[0] == 8]
assert ev_rows and all(m[14 + 3 * i] == -1 for m in ev_rows for i in range(6)), 'an event marker has a name label'
print('event markers: icon only, no name labels (%d)' % len(ev_rows))

# Candidate 19: Plant 42 (Flg_3[96]) is one boss marker; the DLL hides it once the kill flag is set, for both characters.
set_zoom(0)
for key, name in [(ord('0'), 'All'), (ord('8'), 'Enemies')]: setting(key, name, '1')
plants = [f for f in full if f[0] == 7 and f[6] == 96]
assert len(plants) == 1, ('Plant 42 must be one boss marker', len(plants))
for is_jill in (False, True):
    assert shown(plants[0], plants[0][1], [vb(plants[0])], jill=is_jill), ('Plant 42 hidden while alive', is_jill)
    assert not shown(plants[0], plants[0][1], [vb(plants[0])], kills=[96], jill=is_jill), ('Plant 42 drawn after kill', is_jill)
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
print('Plant 42: native kill transition hides one boss for Chris and Jill')

setting(ord('5'), 'Puzzles', '1')
u.mem_write(exports['ov_fullscreen'], bytes(4))
code_markers = [f for f in full if f[0] == 5 and f[4] == 3 and tuple(conds_all[f[6]]) == (0, 33, 1)]
assert code_markers, 'Door code marker missing'
for f in code_markers:
    assert ev_shown(f, False), 'locked Drug Storeroom must show code puzzle'
    assert not ev_shown(f, True), 'unlocked Drug Storeroom must hide code puzzle'
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
print('Door code: native marker follows Drug Storeroom door unlock, not room visit')

# Candidate 20: OR-groups (254) in event hide conditions, checked through native draws.
setting(ord('6'), 'Events', '1')
u.mem_write(exports['ov_fullscreen'], bytes(4))
def ev_vis(f, flg1):
    scene(f[1], jill=bool(f[5] & 2), visited=[vb(f)]); setbits(0xC38724, flg1, 8)
    state['keys'] = set(); draw(); img = canvas(); setbits(0xC38724, [], 8)
    return bitmap_present(img, f[7], ORIGIN[0] + f[8], ORIGIN[1] + f[9])
corridor = [f for f in full if f[0] == 8 and (f[2], f[3]) == (4, 8)]
assert sorted(f[5] for f in corridor) == [1, 2], corridor
for f, done in zip(sorted(corridor, key=lambda f: f[5]), (172, 179)):
    assert not ev_vis(f, []), 'Private Corridor scene shown before the partner is freed'
    assert ev_vis(f, [75]), 'Private Corridor scene hidden after the rescue'
    assert not ev_vis(f, [75, done]), 'Private Corridor scene shown after it played'
assert not [f for f in full if f[0] == 8 and (f[2], f[3]) == (4, 11)], 'Cell Entry still has an event marker'
room002 = [f for f in full if f[0] == 8 and (f[2], f[3]) == (3, 6)]
assert len(room002) == 1
assert ev_vis(room002[0], [174]) and not ev_vis(room002[0], [175]) and not ev_vis(room002[0], [174, 178]), 'Room 002 scene'
assert not [f for f in full if f[0] == 8 and (f[2], f[3]) == (0, 6) and f[5] == 3 and tuple(conds_all[f[6]]) == (1, 4, 1)], 'Main Hall movie marker'
u.mem_write(exports['ov_fullscreen'], struct.pack('<i', 1))
hall = sorted((conds_all[f[6]], f[5]) for f in full if f[0] == 8 and (f[2], f[3]) == (0, 6))
assert hall == [((1, 0, 1), 3), ((1, 3, 1), 3)], ('Main Hall 1F: game start + return from the Tea Room, both characters', hall)
print('events: Private Corridor after rescue, Room 002 gone once Room 005 took the other branch, Main Hall 1F start + Tea Room return')

# Terrain and outline share an affine map transform at every legal pan step on both axes.
# Checking every axis value plus the corner products covers their independent x/y transforms.
setting(ord('0'), 'All', '0')
checks = 0
wall_checks = 0
map_bytes = bytes(int(v) for v in raw_maps.replace("{", "").replace("}", "").split(","))
setbits(0xC387A0, range(160), 5)   # actual room fills, not an empty unvisited floor
for page in range(11):
    reopen_page(page)
    settle_frames(3)
    fill_tex = uploads[sprites[-len(commands) + 2]['tex'] - 0x5001][64:]
    pixels = map_bytes[page * 12800:(page + 1) * 12800]
    for yy in range(1, 99):
        for xx in range(1, 127):
            if pixels[yy * 128 + xx] != 7: continue
            # A wall with room only to its left/top must not leak fill to its right/bottom.
            if any(pixels[(yy + dy) * 128 + xx + dx] >= 13 for dx, dy in ((1, 0), (0, 1), (1, 1))): continue
            if not any(13 <= pixels[(yy + dy) * 128 + xx + dx] and (pixels[(yy + dy) * 128 + xx + dx] - 13) % 6 in (1, 2, 3, 4) for dx, dy in ((-1, 0), (0, -1))): continue
            value = (fill_tex[yy * 128 + xx // 2] >> (4 * (xx & 1))) & 15
            assert value == 0, ('fill leaks past right/bottom wall', page, xx, yy, value)
            wall_checks += 1
    for folded in (False, True):
        setting(0xC0, 'Legend', '0' if folded else '1')
        height = 240 if folded else 204
        for zoom in (0, 1):
            set_zoom(zoom)
            positions = [(96, 80)] if not zoom else (
                [(x, 80) for x in range(-80, 273, 4)] +
                [(96, y) for y in range(-60 if folded else -48, (220 if folded else 244) + 1, 4)] +
                [(x, y) for x in (-80, 272) for y in ((-60, 220) if folded else (-48, 244))])
            for x, y in positions:
                pan_to(x, y)
                quads = [struct.unpack_from('<4h', c, 8) for c in commands[2:4]]
                uv = [struct.unpack_from('<4H', c, 16) for c in commands[2:4]]
                assert quads[0] == quads[1], (page, zoom, x, y, quads)
                for q, t, unit in zip(quads, uv, (4 if zoom else 2, 2 if zoom else 1)):
                    assert q[2] - q[0] + 1 == (t[2] - t[0] + 1) * unit
                    assert q[3] - q[1] + 1 == (t[3] - t[1] + 1) * unit
                    if zoom:
                        assert q[0] - t[0] * unit == -x and q[1] - t[1] * unit == -y
                        assert 0 <= q[0] <= q[2] < 320 and 0 <= q[1] <= q[3] < height
                checks += 1
print('terrain/outline native affine alignment: all 11 pages, 1x/2x, both legends, all 4px axis pan steps and corners:', checks)

assert wall_checks > 100, wall_checks
print('native wall fill does not extend beyond right/bottom outline:', wall_checks)
