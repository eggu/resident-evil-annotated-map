"""Rebuild everything from the installed game files: data -> wiki -> assets -> ASI -> native test.

Usage: RE1_GAME_DIR=<game folder> .venv/bin/python build.py [--skip-data] [--package]
"""
import os, subprocess, sys
from pathlib import Path
import ziglang

ROOT = Path(__file__).parent
PY = [sys.executable, '-I']
DATA_STEPS = ['extract.py', 'evilresource.py', 'map_shapes.py', 'match_rooms.py', 'match_highlights.py', 'fit.py', 'build_data.py']


def run(cmd):
    print('>', ' '.join(map(str, cmd)))
    subprocess.run(cmd, cwd=ROOT, check=True)


if '--skip-data' not in sys.argv:
    for step in DATA_STEPS:
        run(PY + [ROOT / 'tools' / step])
run(PY + [ROOT / 'tools/gen_wiki.py'])
run(PY + [ROOT / 'tools/preview.py'])
run(PY + [ROOT / 'tools/gen_assets.py'])
inc = Path(ziglang.__file__).parent / 'lib/libc/include/any-windows-any'
run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'x86-windows-gnu', '-shared', '-O2', '-fno-stack-protector',
     '-DWIN32_LEAN_AND_MEAN', '-nostdlib', f'-I{inc}', '-Wall', '-Wextra', '-Wl,--entry,DllMain@12',
     'src/re1_map.c', '-lkernel32', '-luser32', '-o', 'mod_annotated_map/RE1.AnnotatedMap.dll'])
run([sys.executable, 'tests/test_native.py'])
if '--package' in sys.argv:
    # release ZIP: copy-into-game-folder layout (the DLL also sits in the game root, like other REbirth mods)
    import zipfile
    ver = (ROOT / 'VERSION').read_text().strip()
    out = ROOT / f'dist/RE1-Annotated-Map-{ver}.zip'
    out.parent.mkdir(exist_ok=True)
    mod = ROOT / 'mod_annotated_map'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ('manifest.txt', 'description.txt', 'RE1.AnnotatedMap.dll'):
            z.write(mod / name, f'mod_annotated_map/{name}')
        z.write(mod / 'RE1.AnnotatedMap.dll', 'RE1.AnnotatedMap.dll')
        z.write(ROOT / 'packaging/README.txt', 'RE1-Annotated-Map-README.txt')
    print('package', out, out.stat().st_size)
