"""DisplayMode=Auto decision (user 2026-11-13): HD only with Classic REbirth loaded (ddraw.dll beside the exe), HDLoader=1, RetroMode=0
and LowResEnable=0; every other case, including no REbirth at all, is SD. Decision table through the exported function, then
the whole mod booted under each state (it must install and draw SD without REbirth).

Run: RE1_GAME_DIR=<game> .venv/bin/python tests/test_sd_auto.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from sd_emu import boot

emu = boot(HDLoader=1)
call, fn = emu.g['call'], emu.exports['AnnotatedMapTestSdAuto']
NONE = 0xFFFFFFFF   # HDLoader key missing (-1)
table = [((1, 1, 0, 0), 0)] + [(a, 1) for a in ((0, 1, 0, 0), (1, 0, 0, 0), (1, NONE, 0, 0), (1, 1, 1, 0), (1, 1, 0, 1), (1, 2, 0, 0), (0, 0, 0, 0), (0, NONE, 0, 0), (1, 1, 1, 1))]
for args, want in table:
    assert call(fn, *args) == want, (args, want)
print('decision table ok:', len(table), 'cases (HD only for REbirth + HDLoader=1 + RetroMode=0 + LowResEnable=0)')


def draws(**kw):
    e = boot(**kw)
    e.scene(0, visited=range(124)); e.poke('ov_fullscreen', 1)
    e.draw(); up, sp = e.draw()
    notice = any(s['wh'] == (256, 32) for s in sp)
    return 'notice' if notice else 'SD' if sp and len(sp) < 14 else 'HD' if len(sp) >= 14 else 'none', len(sp)

SYSTEM = 'C:\\Windows\\System32\\ddraw.dll'
cases = [('REbirth, HDLoader=1', dict(HDLoader=1), 'HD'),
         ('REbirth, HDLoader=0', dict(HDLoader=0), 'SD'),
         ('REbirth, HDLoader missing', dict(HDLoader=None), 'SD'),
         ('REbirth, RetroMode=1', dict(HDLoader=1, RetroMode=1), 'SD'),
         ('REbirth, LowResEnable=1', dict(HDLoader=1, LowResEnable=1), 'SD'),
         ('system ddraw, stale config HDLoader=1', dict(HDLoader=1, ddraw=SYSTEM), 'SD'),
         ('no ddraw at all, HDLoader=1', dict(HDLoader=1, ddraw=None), 'SD'),
         ('no REbirth, no config', dict(HDLoader=None, ddraw=None), 'SD'),
         ('DisplayMode=SD, REbirth HD on', dict(HDLoader=1, DisplayMode='SD'), 'SD'),
         ('DisplayMode=HD, no REbirth', dict(HDLoader=1, ddraw=None, DisplayMode='HD'), 'notice'),
         ('DisplayMode=HD, REbirth HD on', dict(HDLoader=1, DisplayMode='HD'), 'HD')]
for label, kw, want in cases:
    got, n = draws(**kw)
    assert got == want, (label, got, n)
    print('  ', label, '->', got, f'({n} sprites)')
print('SD auto ok: the mod installs and draws without Classic REbirth')
