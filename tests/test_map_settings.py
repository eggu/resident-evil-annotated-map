"""Run DLL initialization, map hotkeys and native alpha against the real EXE in memory."""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'tests/test_native.py').read_text()
prefix = source.split('# 1) unvisited', 1)[0]

def load(settings):
    code = re.sub(r'^state = dict\(keys=set\(\), ini=.*?, written=\{\}\)$',
                  f'state = dict(keys=set(), ini={settings!r}, written={{}})', prefix, flags=re.M)
    g = dict(__file__=str(ROOT / 'tests/test_native.py'))
    exec(compile(code, 'map-settings-init', 'exec'), g)
    g['scene'](0)
    return g

def press(g, *keys):
    g['state']['keys'] = set(); g['draw']()
    g['state']['keys'] = set(keys); g['draw']()

def saved(g, key):
    return g['state']['written'][key]

g = load({})
press(g, ord('8'))
factory = dict(All='1', Rooms='1', Locks='0', KeyItems='0', Documents='0', Puzzles='0', CommonItems='0',
               Language='en', NameSize='100', NameOpacity='70')
assert all(saved(g, k) == v for k, v in factory.items())
press(g, 0xbb)
assert saved(g, 'NameSize') == '110'
g['draw'](); g['draw']()
assert saved(g, 'NameSize') == '110', 'held keys must not repeat'
press(g, 0xbd)
assert saved(g, 'NameSize') == '100'
press(g, 0x10, 0xbb)
assert saved(g, 'NameOpacity') == '80' and saved(g, 'NameSize') == '100'
press(g, 0xa0, 0x6d)
assert saved(g, 'NameOpacity') == '70'
press(g, 0xa1, 0x6b)
assert saved(g, 'NameOpacity') == '80'
for settings, key, expected in [
    (dict(NameSize=150), (0x6b,), ('NameSize', '150')),
    (dict(NameSize=50), (0x6d,), ('NameSize', '50')),
    (dict(NameOpacity=100), (0x10,0x6b), ('NameOpacity', '100')),
    (dict(NameOpacity=10), (0x10,0x6d), ('NameOpacity', '10')),
]:
    h = load(settings); press(h, *key); assert saved(h, expected[0]) == expected[1]
for settings, expected in [
    (dict(NameSize=0,NameOpacity=0), (50,10)),
    (dict(NameSize=999,NameOpacity=999), (150,100)),
    (dict(NameSize=113,NameOpacity=74), (110,70)),
    (dict(NameSize=130,NameOpacity=40,Language='ko',Rooms=0,Locks=1), (130,40)),
]:
    h = load(settings); press(h, ord('8'))
    assert (int(saved(h,'NameSize')),int(saved(h,'NameOpacity'))) == expected
    if settings.get('Language') == 'ko':
        assert saved(h,'Language') == 'ko' and saved(h,'Rooms') == '0' and saved(h,'Locks') == '1'
print('Factory defaults / main and numpad keys / Shift / edge triggering / clamps / INI reload passed', flush=True)

# Keep the real Add_sprt and patched submit route; only stop at the renderer boundary.
g = load(dict(All=1, Rooms=1, Locks=1, KeyItems=1, Documents=1, Puzzles=1, CommonItems=1))
g['scene'](0, visited=[5,6]); g['draw']()
exports_code = 'exp_rv = ' + source.split('exp_rv = ',1)[1].split("scale_var = exports",1)[0]
exec(exports_code, g)
g['u'].mem_write(0x47a9b0, b'\xc2\x08\x00')
code = source.split('# 9) Run the real Add_sprt',1)[1].split('# Generated grid repeats',1)[0]
exec(compile(code[code.index('u.mem_write(0x441920'):], 'native-alpha', 'exec'), g)
for opacity in (80,90,100):
    g['u'].mem_write(0x4b27f8,bytes(4)); g['state']['keys']=set(); g['draw']()
    g['u'].mem_write(0x4b27f8,bytes(4)); g['commands'].clear(); g['state']['keys']={0x10,0xbb}; g['draw']()
    alphas={round(struct.unpack_from('<f',c,44)[0],3) for c in g['commands'][4:]}
    assert round(1-opacity/100,3) in alphas and 0 in alphas
    if opacity < 100: assert 0.3 not in alphas
# RE3 source colours, quantized through the existing RE1 RGB555 function.
colours={1:(16,16,16),2:(240,226,190),3:(90,220,255),4:(255,140,210),5:(255,205,70),
         6:(255,150,40),7:(255,120,60),8:(140,140,140),15:(255,255,255)}
palette=list(map(int,g['hdr'].split('ov_legend_palette[16]={',1)[1].split('}',1)[0].split(',')))
for index,(r,green,b) in colours.items():
    assert palette[index] == 0x8000 | (r*31//255) | ((green*31//255)<<5) | ((b*31//255)<<10)
assert any(list(struct.unpack('<16H',t[20:52]))==palette for t in g['uploads'])
print('Native alpha 70/80/90/100 and isolated RE3 legend CLUT passed', flush=True)
