"""Enemy icons, 32 x 32 source vs the build's 4bpp conversion (own CLUT per kind, tools/enemy_icons.py).
Each cell: source and converted at about 20 screen px (the in-game size at 1600 x 1200, IconSize 100) and at 5x nearest.

Usage: .venv/bin/python tools/enemy_comparison.py <out.png>
"""
import runpy, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
EI = runpy.run_path(str(ROOT / 'tools/enemy_icons.py'))
KINDS = dict(zombie='zombie', cerberus='cerberus', spider='web-spinner', black_tiger='black-tiger', crow='crow',
             hunter='hunter', wasp='wasp', plant42='plant-42', chimera='chimera', adder='adder', neptune='neptune',
             tyrant='tyrant', yawn='yawn', fountain_plant='fountain-plant')
BG = (24, 30, 82)   # close to the map's blue grid background
CW, CH, COLS = 380, 210, 4
sheet = Image.new('RGB', (CW * COLS, CH * ((len(KINDS) + COLS - 1) // COLS) + 30), (20, 22, 28))
dr = ImageDraw.Draw(sheet)
dr.text((10, 8), 'source | converted (own 16-colour CLUT, RGB555)   top: ~20 px in game size   bottom: 5x nearest', fill=(230, 230, 230))
for n, (k, f) in enumerate(KINDS.items()):
    src = Image.open(ROOT / f'assets/enemy-icons/enemy-{f}.png').convert('RGBA')
    idx, pal = EI['enemy_clut'](src)
    conv = Image.new('RGBA', src.size)
    conv.putdata([(0, 0, 0, 0) if v == 0 else pal[v] + (255,) for v in idx.get_flattened_data()])
    x0, y0 = (n % COLS) * CW + 10, (n // COLS) * CH + 34
    dr.text((x0, y0), k, fill=(230, 230, 230))
    for i, im in enumerate((src, conv)):
        tile = Image.new('RGB', (32, 32), BG); tile.paste(im, (0, 0), im)
        sheet.paste(tile.resize((20, 20), Image.Resampling.LANCZOS), (x0 + 10 + i * 40, y0 + 16))
        sheet.paste(tile.resize((160, 160), Image.Resampling.NEAREST), (x0 + i * 180, y0 + 44))
out = Path(sys.argv[1]); out.parent.mkdir(parents=True, exist_ok=True); sheet.save(out); print(out)
