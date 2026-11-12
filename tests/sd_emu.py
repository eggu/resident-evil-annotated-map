"""Unicorn harness for SD mode: boots the real Biohazard.exe image with the built ASI (tests/test_native.py prefix) under a chosen
INI / config state, then renders what the overlay submits (uploaded 4bpp textures + Add_sprt quads) into a 320x240 image.

    from sd_emu import boot
    emu = boot(HDLoader=0)           # Auto + HD loader off -> SD mode
    img, sprites = emu.render(page=0, view=1, lang='en')
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALL_ON = dict(All=1, Rooms=1, Locks=1, KeyItems=1, Documents=1, Puzzles=1, Events=1, CommonItems=1, Enemies=1, Scope=3)
LANG_KEY = 0xDC


class Emu:
    def __init__(self, ini, ddraw=0):   # ddraw: path of the loaded ddraw.dll, None = not loaded, 0 = REbirth beside the exe
        src = (ROOT / 'tests/test_native.py').read_text().split('# 1) unvisited', 1)[0]
        src = src.replace('ROOT = Path(__file__).resolve().parent.parent', f'ROOT = Path({str(ROOT)!r})')
        old = "ini=dict(Rooms=0, Locks=0, KeyItems=1, Documents=0, Puzzles=0, CommonItems=0, UploadBudget=200, HdIcons=0, HDLoader=1)"
        assert old in src
        src = src.replace(old, 'ini=' + repr(ini) + (', ddraw=' + repr(ddraw) if ddraw != 0 else ''))
        g = {'__name__': 'sd_emu_child', '__file__': str(ROOT / 'tests/test_native.py')}
        exec(compile(src, 'prefix', 'exec'), g)
        self.g = g
        di, o = g['di'], g['o']
        exp_rv = struct.unpack_from('<I', di, o + 96)[0]
        nnames, fn_rva, name_rva, ord_rva = struct.unpack_from('<I', di, exp_rv + 24)[0], *struct.unpack_from('<3I', di, exp_rv + 28)
        self.exports = {}
        for i in range(nnames):
            nm = di[struct.unpack_from('<I', di, name_rva + 4 * i)[0]:].split(b'\0', 1)[0].decode()
            self.exports[nm] = g['DBASE'] + struct.unpack_from('<I', di, fn_rva + 4 * struct.unpack_from('<H', di, ord_rva + 2 * i)[0])[0]
        g['u'].mem_write(0x47a9b0, b'\xc2\x08\x00')

    def poke(self, name, value):
        self.g['u'].mem_write(self.exports[name], struct.pack('<i', value))

    def scene(self, page, **kw):
        self.g['scene'](page, **kw)

    def press(self, vk):
        st = self.g['state']
        st['clock'] = st.get('clock', 0) + 1000   # past the 350 ms key debounce, whatever the harness clock did in between
        st['keys'] = {vk}
        self.draw()
        st['keys'] = set()

    def draw(self):
        return self.g['draw']()

    def textures(self):
        """Every texture ever uploaded: id -> (palette rgb, width, pixel bytes)."""
        out = {}
        for i, t in enumerate(self.g['uploads']):
            pal = [struct.unpack_from('<H', t, 20 + 2 * k)[0] for k in range(16)]
            out[0x5000 + i + 1] = (pal, struct.unpack_from('<H', t, 60)[0] * 4, t[64:])
        return out

    def render(self, page, view, lang='en', pan=(96, 0), visited=range(124), mapstate=None):
        """Overlay of the SD layers for `view` (0 status, 1 full, 2 zoom) as RGBA 320x240 rows of (r, g, b, a)."""
        self.poke('ov_fullscreen', 1 if view else 0)
        self.poke('ov_zoom', 1 if view == 2 else 0)
        self.poke('ov_pan_x', pan[0]); self.poke('ov_pan_y', pan[1])
        self.scene(page, visited=visited)
        for off, v in (mapstate or {}).items(): self.g['u'].mem_write(0xB38DE0 + off, bytes([v]))   # MAP_STATE +12 floors, +13 areas
        want_english = lang == 'en'
        if getattr(self, 'english', True) != want_english:
            self.press(LANG_KEY); self.english = want_english
        self.poke('ov_fullscreen', 1 if view else 0)
        self.poke('ov_zoom', 1 if view == 2 else 0)
        self.poke('ov_pan_x', pan[0]); self.poke('ov_pan_y', pan[1])
        for _ in range(3): up, sp = self.draw()   # uploads are spread over frames (UploadBudget)
        tex = self.textures()
        img = [[(0, 0, 0, 0)] * 320 for _ in range(240)]
        # the last frame's quads, in submit order
        for s in self.g['sprites_now'] if False else sp:
            if s['tex'] not in tex: continue
            pal, tw, px = tex[s['tex']]
            if s['flags'] == 0x40000000 or s['wh'] not in ((256, 240), (64, 240)) or (s['x'], s['y']) not in ((0, 0), (256, 0)): continue   # only the SD layers; terrain / walls / backdrop are the caller's
            u0, v0 = s['uv']
            for y in range(s['wh'][1]):
                for x in range(s['wh'][0]):
                    sx, sy = u0 + x, v0 + y
                    v = (px[sy * (tw // 2) + sx // 2] >> ((sx & 1) * 4)) & 15
                    c = pal[v]
                    X, Y = s['x'] + x, s['y'] + y
                    if v and c and 0 <= X < 320 and 0 <= Y < 240:
                        img[Y][X] = ((c & 31) << 3 | (c & 31) >> 2, (c >> 5 & 31) << 3 | (c >> 5 & 31) >> 2, (c >> 10 & 31) << 3 | (c >> 10 & 31) >> 2, 255)
        return img, sp


def boot(ddraw=0, **extra):
    ini = dict(ALL_ON, UploadBudget=200, HdIcons=0, **extra)
    ini.setdefault('HDLoader', 1)
    return Emu({k: v for k, v in ini.items() if v is not None}, ddraw)   # None removes a key (a missing HDLoader counts as SD)
