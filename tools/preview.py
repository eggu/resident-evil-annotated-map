"""Render each map page with all annotations (4x) -> docs/wiki/img/page-NN.png. Debug/wiki aid only."""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
import tim

ROOT = Path(__file__).parent.parent
ITEM_M2 = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn/Item_m2'
S = 5
d = json.loads((ROOT / 'data/annotated.json').read_text())
font = ImageFont.truetype(str(Path(__file__).resolve().parents[1] / 'fonts/Pretendard-Medium.otf'), 11)
COL = dict(key=(60, 220, 255), document=(240, 240, 240), common=(150, 150, 150), lock=(255, 205, 70), puzzle=(255, 150, 30), save=(170, 200, 120))
out = ROOT / 'docs/wiki/img'
out.mkdir(parents=True, exist_ok=True)
for pg in d['pages']:
    img, _ = tim.load(ITEM_M2 / pg['file'])
    img = img.resize((img.width * S, img.height * S), Image.NEAREST)
    bg = Image.new('RGBA', img.size, (20, 20, 28, 255))
    bg.alpha_composite(img)
    g = ImageDraw.Draw(bg)
    here = lambda m: m and m['stage'] == pg['stage'] and d['rooms'][f"{m['stage']}-{m['slot']:02X}"]['page'] == pg['page']
    for r in d['rooms'].values():
        if r['page'] == pg['page']:
            x, y = (r['anchor'][0] + .5) * S, (r['anchor'][1] + .5) * S
            g.text((x, y), r['name_ko'] or '?', fill=(255, 240, 210), font=font, anchor='mm', stroke_width=2, stroke_fill=(0, 0, 0))

    def dot(m, col, label=None, shape='o'):
        x, y = m['px'] * S, m['py'] * S
        if shape == 'd':
            g.polygon([(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)], fill=col, outline=(0, 0, 0))
        else:
            g.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col, outline=(0, 0, 0))
        if label:
            g.text((x, y - 6), label, fill=col, font=font, anchor='mb', stroke_width=2, stroke_fill=(0, 0, 0))
    for i in d['items']:
        if here(i['map']) and i['category'] != 'common':
            dot(i['map'], COL[i['category']], i['name_ko'] + ('' if i['exact_position'] else '*'))
        elif here(i['map']):
            dot(i['map'], COL['common'])
    for L in d['locks']:
        for sd in L['sides']:
            if here(sd['map']):
                dot(sd['map'], COL['lock'], '🔒' + (L['key_ko'] or ''), 'd')
    for p in d['puzzles']:
        if here(p['map']):
            dot(p['map'], COL['puzzle'], None, 'd')
    for s in d['saves']:
        if here(s['map']):
            dot(s['map'], COL['save'], '타자기' if s['kind'] == 'typewriter' else '상자')
    bg.save(out / f"page-{pg['page']:02d}.png")
    print(pg['page'], pg['file'])
