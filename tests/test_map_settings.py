"""Run DLL initialization, map hotkeys and native alpha against the real EXE in memory."""
import re
import struct
import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'tests/test_native.py').read_text()
prefix = source.split('# 1) unvisited', 1)[0]

def load(settings):
    settings = {'UploadBudget': 200, 'HdIcons': 0, 'HDLoader': 1, **settings}
    if settings['HdIcons'] is None: del settings['HdIcons']   # None: leave the key out of the INI (code default)
    # the deferral budget is tested on its own below; other checks want one-frame uploads
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
press(g, ord('9'))
factory = dict(All='1', Rooms='1', Locks='0', KeyItems='0', Documents='0', Puzzles='0', CommonItems='0', Enemies='0',
               Language='en', NameSize='100', NameOpacity='70', IconSize='100', IconOpacity='80', ItemNames='0',
               Legend='1', KeySide='0', Version='5', Events='0')
assert all(saved(g, k) == v for k, v in factory.items())
config = configparser.ConfigParser()
config.optionxform = str
config.read(ROOT / 'packaging/RE1.AnnotatedMap.ini')
shipped = load({('Colors.' if section == 'Colors' else '') + key: int(value) if value.lstrip('-').isdigit() else value
                for section in config.sections() for key, value in config.items(section)})
press(shipped, ord('9'))
assert all(saved(shipped, k) == v for k, v in factory.items()), 'bundled defaults differ from DLL defaults'
press(g, 0xbb)
assert saved(g, 'NameSize') == '110'
g['draw'](); g['draw']()
assert saved(g, 'NameSize') == '110', 'held keys must not repeat'
press(g, 0xbd)
assert saved(g, 'NameSize') == '100'
# RE0 mapping: [ ] name opacity; Shift + - + icon size (not name opacity, as in 1.1.2 and older)
press(g, 0xdd)
assert saved(g, 'NameOpacity') == '80' and saved(g, 'NameSize') == '100'
press(g, 0xdb)
assert saved(g, 'NameOpacity') == '70'
press(g, 0x10, 0xbb)
assert saved(g, 'IconSize') == '110' and saved(g, 'NameOpacity') == '70' and saved(g, 'NameSize') == '100'
press(g, 0xa0, 0x6d)
assert saved(g, 'IconSize') == '100'
press(g, 0xa1, 0x6b)
assert saved(g, 'IconSize') == '110'
for settings, key, expected in [
    (dict(NameSize=150), (0x6b,), ('NameSize', '150')),
    (dict(NameSize=50), (0x6d,), ('NameSize', '50')),
    (dict(NameOpacity=100), (0xdd,), ('NameOpacity', '100')),
    (dict(NameOpacity=10), (0xdb,), ('NameOpacity', '10')),
]:
    h = load(settings); press(h, *key); assert saved(h, expected[0]) == expected[1]
for settings, expected in [
    (dict(NameSize=0,NameOpacity=0), (50,10)),
    (dict(NameSize=999,NameOpacity=999), (150,100)),
    (dict(NameSize=113,NameOpacity=74), (110,70)),
    (dict(NameSize=130,NameOpacity=40,Language='ko',Rooms=0,Locks=1), (130,40)),
]:
    h = load(settings); press(h, ord('9'))
    assert (int(saved(h,'NameSize')),int(saved(h,'NameOpacity'))) == expected
    if settings.get('Language') == 'ko':
        assert saved(h,'Language') == 'ko' and saved(h,'Rooms') == '0' and saved(h,'Locks') == '1'
print('Factory defaults / main and numpad keys / [ ] name opacity / Shift icon size / edge triggering / clamps / INI reload passed', flush=True)

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
    g['u'].mem_write(0x4b27f8,bytes(4)); g['commands'].clear(); g['state']['keys']={0xdd}; g['draw']()
    alphas={round(struct.unpack_from('<f',c,44)[0],3) for c in g['commands'][4:]}
    assert round(1-opacity/100,3) in alphas and 0 in alphas
    if opacity < 100: assert 0.3 not in alphas
# IconSize stretches each enemy sprite (own texture + CLUT) around its centre: the submit hook rewrites the quad.
def enemy_quads():
    g['state']['keys'] = set(); g['scene'](0, visited=list(range(32))); g['u'].mem_write(0x4b27f8, bytes(4))
    g['commands'].clear(); g['draw']()
    q = [struct.unpack_from('<4h', c, 8) for c in g['commands']]
    return [v for v in q if (v[2] - v[0], v[3] - v[1]) in ((3, 3), (5, 5))]
if g['state']['written'].get('Enemies') != '1': press(g, ord('8'))
assert g['state']['written'].get('Enemies') == '1'
assert any(v[2] - v[0] == 3 for v in enemy_quads()), 'enemy sprites are 4 PSX px at IconSize 100'
for _ in range(5): press(g, 0x10, 0xbb)
assert g['state']['written'].get('IconSize') == '150'
quads = enemy_quads()
assert quads and all(v[2] - v[0] == 5 and v[3] - v[1] == 5 for v in quads), ('enemy sprite not stretched to 6 PSX px', quads[:5])
for _ in range(5): press(g, 0x10, 0xbd)
print('Enemy sprites: 4 PSX px, stretched to 6 at IconSize 150 passed', flush=True)
# Legend colours: category colours snapped to RGB555 (nearest 5-bit value, so a [Colors] default typed in the INI equals the baked one);
# common items are the cool grey #B8BCC4, disabled rows #6A6A6A, hints a dimmer grey, leader lines a mid grey, events the RE0 purple #B070FF.
five = lambda v: round(v * 31 / 255)
def snapped(c): return 0x8000 | five(c[0]) | (five(c[1]) << 5) | (five(c[2]) << 10)
def floored(c): return 0x8000 | (c[0] * 31 // 255) | ((c[1] * 31 // 255) << 5) | ((c[2] * 31 // 255) << 10)
colours = {1: floored((16, 16, 16)), 2: snapped((240, 226, 190)), 3: snapped((90, 220, 255)), 4: snapped((255, 140, 210)), 5: snapped((255, 205, 70)),
           6: snapped((255, 150, 40)), 7: snapped((184, 188, 196)), 8: snapped((106, 106, 106)), 9: snapped((150, 156, 172)), 10: snapped((220, 60, 50)),
           12: floored((140, 140, 140)), 13: snapped((176, 112, 255)), 15: floored((255, 255, 255))}
palette = list(map(int, g['hdr'].split('ov_legend_palette[16]={', 1)[1].split('}', 1)[0].split(',')))
for index, want in colours.items():
    assert palette[index] == want, (index, hex(palette[index]), hex(want))
assert any(list(struct.unpack('<16H', t[20:52])) == palette for t in g['uploads'])
def shown(v): return tuple((f << 3) | (f >> 2) for f in (v & 31, (v >> 5) & 31, (v >> 10) & 31))
assert shown(palette[7]) == (181, 189, 198) and shown(palette[8]) == (107, 107, 107), (shown(palette[7]), shown(palette[8]))
assert palette[8] != palette[7] and sum(shown(palette[8])) < sum(shown(palette[7])) - 150, 'disabled grey must stay distinct from the common-item grey'
print('Native alpha 70/80/90/100 and isolated legend CLUT (cool grey common items, darker disabled rows, event purple) passed', flush=True)

# Settings save: every key goes to a copy of the INI, which then replaces the INI in one rename; failures keep the old INI.
INI, TMP = 'C:\\game\\RE1.AnnotatedMap.ini', 'C:\\game\\RE1.AnnotatedMap.ini.tmp'
h = load({'Version': 5}); h['state']['fs'] = []; h['state']['files'] = []; press(h, ord('9'))
assert h['state']['fs'] == [('copy', INI, TMP), ('move', TMP, INI, 1)], h['state']['fs']
assert set(h['state']['files']) == {TMP}, 'settings must not be written into the live INI'
for fail, kept in [('move_ok', [('copy', INI, TMP), ('move', TMP, INI, 1), ('delete', TMP)]), ('copy_ok', [('copy', INI, TMP)])]:
    h = load({'Version': 5}); h['state'].update({fail: 0, 'fs': [], 'files': []}); press(h, ord('9'))
    assert h['state']['fs'] == kept, (fail, h['state']['fs'])
h = load({'Version': 5}); h['state'].update(copy_ok=0, ini_exists=False, fs=[]); press(h, ord('9'))
assert h['state']['fs'] == [('copy', INI, TMP), ('move', TMP, INI, 1)], 'a missing INI is created through the temp file'
print('Settings save: temp copy + one replace, failures keep the previous INI passed', flush=True)

# Version: an INI without Version=5 (1.1.2 and older, or none) is rewritten once from the game loop, keeping its values;
# a current one is not rewritten until a key changes something.
h = load(dict(NameSize=130, Locks=1)); h['state']['fs'] = []; h['state']['keys'] = set(); h['draw']()
assert [f[0] for f in h['state']['fs']] == ['copy', 'move'] and saved(h, 'Version') == '5'
assert saved(h, 'NameSize') == '130' and saved(h, 'Locks') == '1' and saved(h, 'Enemies') == '0'
h['state']['fs'] = []; h['draw'](); assert h['state']['fs'] == [], 'migration repeated'
h = load({'Version': 5}); h['state']['fs'] = []; h['state']['keys'] = set(); h['draw'](); assert h['state']['fs'] == []
# New keys: 8 enemies, H item names, [ ] icon size (50..200), Shift + [ ] icon opacity, ~ legend fold.
h = load({'Version': 5})
for keys, key, value in [((ord('8'),), 'Enemies', '1'), ((ord('H'),), 'ItemNames', '1'), ((0x10, 0xbb), 'IconSize', '110'),
                         ((0x10, 0xbd), 'IconSize', '100'), ((0x10, 0xdb), 'IconOpacity', '70'), ((0xa1, 0xdd), 'IconOpacity', '80'),
                         ((0xc0,), 'Legend', '0'), ((0xc0,), 'Legend', '1')]:
    press(h, *keys); assert saved(h, key) == value, (keys, key, saved(h, key))
for settings, keys, expected in [(dict(IconSize=200), (0x10, 0xbb), ('IconSize', '200')), (dict(IconSize=50), (0x10, 0xbd), ('IconSize', '50')),
                                 (dict(IconSize=999, IconOpacity=0), (ord('9'),), ('IconSize', '200')),
                                 (dict(IconOpacity=0), (ord('9'),), ('IconOpacity', '10'))]:
    h = load(dict(settings, Version=5)); press(h, *keys); assert saved(h, expected[0]) == expected[1], (settings, saved(h, expected[0]))
# Modifier=CTRL: Ctrl selects the icon keys, Shift is then a plain name key.
h = load(dict(Version=5, Modifier='CTRL'))
press(h, 0x11, 0xbb); assert saved(h, 'IconSize') == '110' and saved(h, 'NameSize') == '100'
press(h, 0x10, 0xbb); assert saved(h, 'NameSize') == '110' and saved(h, 'IconSize') == '110'
press(h, 0xa3, 0xdb); assert saved(h, 'IconOpacity') == '70' and saved(h, 'NameOpacity') == '70'
# Debounce: the same key again within 350 ms is ignored; another key is not.
h = load({'Version': 5}); h['state']['raw_clock'] = True
press(h, ord('2')); assert saved(h, 'Locks') == '1'
press(h, ord('2')); assert saved(h, 'Locks') == '1', 'bounce within 350 ms toggled again'
press(h, ord('4')); assert saved(h, 'Documents') == '1'
h['state']['clock'] += 400; press(h, ord('2')); assert saved(h, 'Locks') == '0'
# Capture key (default F12): a temp file beside the INI, renamed over RE1.AnnotatedMap.capture.txt.
h = load({'Version': 5}); h['state']['opened'] = set(); press(h, 0x7b)
assert 'C:\\game\\RE1.AnnotatedMap.capture.txt.tmp' in h['state']['opened'], h['state']['opened']
h = load(dict(Version=5, CaptureKey='NONE')); h['state']['opened'] = set(); press(h, 0x7b)
assert 'C:\\game\\RE1.AnnotatedMap.capture.txt.tmp' not in h['state']['opened']
print('Version migration / enemies, item-name, icon size/opacity, legend keys / Ctrl modifier / debounce / capture passed', flush=True)

# Zoom is never persisted: an old Zoom=2 in the INI is ignored (1x), and saving removes the key.
for value in (1, 2, -1, 99):
    h = load(dict(Version=5, Zoom=value))
    exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], h)
    assert struct.unpack('<i', h['u'].mem_read(h['exports']['ov_zoom'], 4))[0] == 0, 'INI Zoom must be ignored'
    press(h, ord('2'))   # any setting change saves the INI
    assert h['state']['written'].get('Zoom', 'absent') is None, 'save must drop the Zoom key'
print('Zoom INI ignored / key dropped on save passed')

# UploadBudget (textures uploaded per frame): INI value clamps to 1..200, 0/missing fall back to 12, and the B key no longer zooms.
for value, expected in ((30, 30), (999, 200), (0, 12), (-5, 12)):
    h = load(dict(Version=5, UploadBudget=value))
    exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], h)
    assert struct.unpack('<i', h['u'].mem_read(h['exports']['ov_upload_budget'], 4))[0] == expected, (value, expected)
h = load(dict(Version=5))
exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], h)
h['u'].mem_write(h['exports']['ov_fullscreen'], struct.pack('<i', 1)); press(h, ord('B'))
assert struct.unpack('<i', h['u'].mem_read(h['exports']['ov_zoom'], 4))[0] == 0, 'B must not zoom'
print('UploadBudget INI clamp / B no longer zooms passed')

# HdIcons INI: default on (key absent), 0 turns the HD-style full-map icons off.
for value, expected in ((None, 1), (0, 0), (1, 1)):
    h = load(dict(Version=5, HdIcons=value))
    exec('exp_rv = ' + source.split('exp_rv = ', 1)[1].split('scale_var = exports', 1)[0], h)
    assert struct.unpack('<i', h['u'].mem_read(h['exports']['ov_hd_on'], 4))[0] == expected, (value, expected)
print('HdIcons INI passed')

# [H] item names cycle all -> all but common -> off; INI ItemNames (version 4) uses the RE1 HD / RE2 / RE3 meaning 0 off / 1 all / 2 all but common.
h = load({'Version': 5})
for expected in ('1', '2', '0', '1'):
    press(h, ord('H')); assert saved(h, 'ItemNames') == expected, (expected, saved(h, 'ItemNames'))
# loaded value -> value written by the next save: versions 1-2 were 0 off / 1 on, version 3 (candidate 14) 0 all / 1 no common / 2 off
for settings, expected in [(dict(Version=2, ItemNames=1), '1'), (dict(Version=2, ItemNames=0), '0'), (dict(Version=1), '0'),
                           (dict(Version=3, ItemNames=0), '1'), (dict(Version=3, ItemNames=1), '2'), (dict(Version=3, ItemNames=2), '0'),
                           (dict(Version=3, ItemNames=9), '0'),
                           (dict(Version=4, ItemNames=0), '0'), (dict(Version=4, ItemNames=1), '1'), (dict(Version=4, ItemNames=2), '2'),
                           (dict(Version=5, ItemNames=0), '0'), (dict(Version=5, ItemNames=1), '1'), (dict(Version=5, ItemNames=2), '2'),
                           (dict(Version=5, ItemNames=9), '0'), (dict(Version=5), '0')]:
    h = load(settings); h['state']['fs'] = []; h['state']['keys'] = set(); press(h, ord('9')); press(h, ord('9')); press(h, ord('9'))   # any save writes the loaded value
    assert saved(h, 'ItemNames') == expected, (settings, expected, saved(h, 'ItemNames'))
    assert saved(h, 'Version') == '5'
print('ItemNames 0 off / 1 all / 2 all but common, cycle, migration from versions 1-3 passed')


# Candidate 16: legend renumbering ([6] events; scope [9]; language on the backslash key), Version 5 migration, [Colors].
names = ['All', 'Rooms', 'Locks', 'KeyItems', 'Documents', 'Puzzles', 'Events', 'CommonItems', 'Enemies']
h = load({'Version': 5})
before = {n: saved(h, n) if n in h['state']['written'] else None for n in names}
press(h, ord('9')); before = {n: saved(h, n) for n in names}
assert before == dict(All='1', Rooms='1', Locks='0', KeyItems='0', Documents='0', Puzzles='0', Events='0', CommonItems='0', Enemies='0'), before
for key, name in zip('012345678', names):
    press(h, ord(key)); now = {n: saved(h, n) for n in names}
    assert {n for n in names if now[n] != before[n]} == {name}, (key, name, now)
    before = now
press(h, ord('9')); assert saved(h, 'Scope') == '3', 'key 9 cycles the scope (visited -> revealed -> all rooms)'
assert saved(h, 'Language') == 'en'
press(h, 0xdc); assert saved(h, 'Language') == 'ko', 'backslash (VK_OEM_5) switches the language'
press(h, 0xdc); assert saved(h, 'Language') == 'en'
press(h, ord('9')); assert all(saved(h, n) == before[n] for n in names), 'the scope key must not touch a category toggle'
print('Keys 0-8 toggle the categories in the new order, 9 scope, backslash language passed', flush=True)
# Version 4 -> 5: values are stored by name, so nothing moves; Events is added (default off), everything else is kept
h = load(dict(Version=4, Puzzles=1, CommonItems=1, Enemies=1, Scope=3, Language='ko', NameSize=120, ItemNames=1))
h['state']['fs'] = []; h['state']['keys'] = set(); h['draw']()
assert [f[0] for f in h['state']['fs']] == ['copy', 'move'], 'the old INI is rewritten once'
assert saved(h, 'Version') == '5' and saved(h, 'Events') == '0' and saved(h, 'Puzzles') == '1' and saved(h, 'CommonItems') == '1'
assert saved(h, 'Enemies') == '1' and saved(h, 'Scope') == '3' and saved(h, 'Language') == 'ko' and saved(h, 'NameSize') == '120' and saved(h, 'ItemNames') == '1'
print('Version 4 -> 5 migration passed', flush=True)
# [Colors]: #RRGGBB per category patches the legend CLUT before the first upload; bad values keep the default; black is never RGB zero
default = palette[:]
def clut_of(settings):
    h = load(dict(Version=5, All=1, **settings)); h['state']['keys'] = set(); h['draw']()
    return h, [list(struct.unpack('<16H', t[20:52])) for t in h['uploads'] if struct.unpack_from('<I', t, 0)[0] == 0x10]
def legend_clut(cluts):
    return next(c for c in cluts if c[1] == default[1] and c[15] == default[15])
def rgb555_round(rgb): return 0x8000 | five((rgb >> 16) & 255) | (five((rgb >> 8) & 255) << 5) | (five(rgb & 255) << 10)
h, cluts = clut_of({'Colors.Rooms': '#102030', 'Colors.CommonItems': '#FF8000 ; my note', 'Colors.Puzzles': 'oops', 'Colors.Events': '#000000',
                    'Colors.Enemies': '#12345', 'Colors.Locks': '#00FF00', 'Colors.KeyItems': '#ABCDEF', 'Colors.Files': '#FFFFFF'})
c = legend_clut(cluts)
assert c[2] == rgb555_round(0x102030) and c[7] == rgb555_round(0xFF8000) and c[5] == rgb555_round(0x00FF00) and c[3] == rgb555_round(0xABCDEF) and c[4] == rgb555_round(0xFFFFFF)
assert c[6] == default[6] and c[10] == default[10], 'invalid colour values keep the default'
assert c[13] == 0x8421, 'black is nudged off the colour key'
assert c[8] == default[8] and c[1] == default[1] and c[12] == default[12] and c[15] == default[15], 'disabled grey, outline, leader grey and white are not configurable'
h, cluts = clut_of({}); assert legend_clut(cluts) == default, 'no [Colors]: the baked colours'
# every shipped default equals the baked colour
shipped = configparser.ConfigParser(); shipped.optionxform = str; shipped.read(ROOT / 'packaging/RE1.AnnotatedMap.ini')
idx = dict(Rooms=2, Locks=5, KeyItems=3, Files=4, Puzzles=6, Events=13, CommonItems=7, Enemies=10)
assert set(shipped['Colors']) == set(idx), shipped['Colors']
h, cluts = clut_of({'Colors.' + k: v for k, v in shipped['Colors'].items()})
assert legend_clut(cluts) == default, 'the INI defaults must reproduce the baked colours exactly'
# saving keeps [Colors] and comments: a copy of the INI is edited (never rewritten), and no [Colors] key is ever written
h = load({'Version': 5, 'Colors.Rooms': '#102030'}); h['state']['fs'] = []; h['state']['written'].clear(); press(h, ord('1')); press(h, 0xdc)
assert [f[0] for f in h['state']['fs']][:2] == ['copy', 'move'] and not any(k.startswith('Colors.') for k in h['state']['written']), h['state']['written']
print('[Colors] patch / invalid values / defaults == baked / preserved on save passed', flush=True)
