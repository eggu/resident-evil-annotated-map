"""assets/hd-icons-new/badge-event.png: the HD puzzle badge (orange diamond with '!') recoloured to the event purple with a '?'.
Run once; the PNG is committed art, the build only reads it."""
import colorsys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
src = Image.open(ROOT / 'assets/hd-icons/badge-puzzle.png').convert('RGBA')
px = src.load()
body = px[10, 16][:3]   # plain orange body left of the glyph
for y in range(32):
    for x in range(32):
        r, g, b, a = px[x, y]
        if a < 128:
            continue
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if 9 <= x <= 22 and 4 <= y <= 27 and s < 0.35 and v > 0.5:   # the '!' glyph (white/grey): back to body colour
            r, g, b = body
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s > 0.3:   # orange family -> purple #B070FF family
            h = 270 / 360
        r, g, b = (round(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
        px[x, y] = (r, g, b, a)
font = ImageFont.truetype(str(ROOT / 'fonts/Pretendard-Medium.otf'), 22, index=0)
d = ImageDraw.Draw(src)
d.text((16, 16), '?', font=font, fill=(255, 255, 255, 255), anchor='mm', stroke_width=1, stroke_fill=(45, 29, 40, 255))
src.save(ROOT / 'assets/hd-icons-new/badge-event.png')
bg = Image.new('RGBA', (32, 32), (40, 40, 90, 255)); bg.alpha_composite(src)
bg.resize((256, 256), Image.NEAREST).save('/private/tmp/claude-501/-Users-kurt-Projects-02----biohazard/cbf1ac52-509d-40a6-9594-e0dbe7aaa3f2/scratchpad/be.png')
