"""Render actual native submit quads and uploaded palettes; does not emulate Marni blending/HD filtering."""
import re, struct, sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'tests/test_native.py').read_text()
prefix = source.split('# 1) unvisited', 1)[0]
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for lang in ('en', 'ko'):
    ini = dict(Version=2, All=1, Rooms=1, Locks=1, KeyItems=1, Documents=1, Puzzles=1, CommonItems=1, Enemies=1, ItemNames=1, Scope=3, Language=lang, UploadBudget=200, HdIcons=1)
    code = re.sub(r'^state = dict\(keys=set\(\), ini=.*?, written=\{\}\)$', f'state = dict(keys=set(), ini={ini!r}, written={{}})', prefix, flags=re.M)
    g = dict(__file__=str(ROOT / 'tests/test_native.py')); exec(compile(code, 'zoom-render', 'exec'), g)
    exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], g)
    u, S = g['u'], g['S']
    u.mem_write(0x47a9b0, b'\xc2\x08\x00')
    u.mem_write(0x441920, bytes(g['gi'][0x41920:0x41de5])); u.ctl_remove_cache(0x441920, 0x441e10)
    commands = []
    def record(uc, addr, size, data): commands.append(bytes(uc.mem_read(g['arg'](0), 52)))
    u.hook_add(g['UC_HOOK_CODE'], record, begin=0x47a9b0, end=0x47a9b0)
    for zoom in (0, 1):
        u.mem_write(g['exports']['ov_zoom'], struct.pack('<i', zoom))
        u.mem_write(g['exports']['ov_fullscreen'], struct.pack('<i', 1))
        for page in (0, 1):
            g['scene'](page); u.mem_write(0x4b27f8, bytes(4)); commands.clear(); g['draw']()
            assert len(commands) == len(g['sprites_now'])
            textures = {}
            for i, t in enumerate(g['uploads']):
                pal = struct.unpack('<16H', t[20:52]); tw, th = struct.unpack_from('<HH', t, 60); tw *= 4
                px = bytes(c for b in t[64:] for c in (b & 15, b >> 4))
                im = Image.frombytes('P', (tw, th), px)
                im.putpalette([c for v in pal for c in ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)] + [0] * (768 - 48))
                im.info['transparency'] = 0
                textures[0x5001 + i] = im.convert('RGBA')
            image = Image.new('RGBA', (320*S, 240*S), (0,0,0,255))
            for sp, cmd in zip(g['sprites_now'], commands):
                x0,y0,x1,y1 = struct.unpack_from('<4h',cmd,8); a,b,c,d = struct.unpack_from('<4H',cmd,16)
                assert 0 <= a <= c < 256 and 0 <= b <= d < 256
                part = textures[sp['tex']].crop((a,b,c+1,d+1)).resize(((x1-x0+1)*S,(y1-y0+1)*S), Image.Resampling.NEAREST)
                image.paste(part,(x0*S,y0*S),part)
            path=out / f'mansion-{page+1}f-{lang}-{zoom+1}x.png'
            image.convert('RGB').resize((1280,960),Image.Resampling.LANCZOS).save(path); print(path)
