"""Build from the committed extracted data: wiki -> assets -> DLL -> native test [-> release ZIP].

Usage: RE1_GAME_DIR=<game folder> .venv/bin/python build.py [--extract] [--package]
  --extract  re-run data extraction first (needs every ROOM*.RDT and refs/evilresource pages)
  --package  write dist/RE1-Annotated-Map-<VERSION>.zip
The build itself reads only Biohazard.exe (native test) and jpn/Item_m2 MAP*.TIM / Map_blue.tim.
"""
import argparse, os, subprocess, sys
from pathlib import Path
import ziglang

ROOT = Path(__file__).parent
PY = [sys.executable, '-I']
DATA_STEPS = ['extract.py', 'evilresource.py', 'map_shapes.py', 'match_rooms.py', 'match_highlights.py', 'fit.py', 'build_data.py']


def run(cmd):
    print('>', ' '.join(map(str, cmd)))
    subprocess.run(cmd, cwd=ROOT, check=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--extract', action='store_true')
parser.add_argument('--package', action='store_true')
for option in ('font', 'title-font-en', 'title-font-ko'):
    parser.add_argument('--' + option, type=Path, help='Custom font file (defaults to the bundled open-source font)')
args = parser.parse_args()
font_args = []
for option in ('font', 'title-font-en', 'title-font-ko'):
    path = getattr(args, option.replace('-', '_'))
    if path is not None:
        path = path.expanduser().resolve()
        if not path.is_file():
            parser.error(f'Font file not found: {path}')
        font_args += ['--' + option, str(path)]

if args.extract:
    for step in DATA_STEPS:
        run(PY + [ROOT / 'tools' / step])
run(PY + [ROOT / 'tools/gen_wiki.py'])
run(PY + [ROOT / 'tools/preview.py'])
run(PY + [ROOT / 'tools/gen_assets.py'] + font_args)
inc = Path(ziglang.__file__).parent / 'lib/libc/include/any-windows-any'
run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'x86-windows-gnu', '-shared', '-O2', '-fno-stack-protector',
     '-DWIN32_LEAN_AND_MEAN', '-nostdlib', f'-I{inc}', '-Wall', '-Wextra', '-Wl,--entry,DllMain@12',
     'src/re1_map.c', '-lkernel32', '-luser32', '-o', 'mod_annotated_map/RE1.AnnotatedMap.dll'])
run([sys.executable, 'tests/test_native.py'])
if args.package:
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
