"""Enemy icon reduction shared by tools/gen_assets.py and tools/enemy_comparison.py: each icon gets its own 4bpp CLUT."""
import colorsys, math
from PIL import Image


def _rgb5(c):   # what the game shows: RGB555, and never RGB zero (the native colour key)
    q = tuple(v * 31 // 255 * 255 // 31 for v in c)
    return q if any(v * 31 // 255 for v in q) else (8, 8, 8)


def enemy_clut(im):
    """-> (index image 'L', 16-entry palette): the icon's own median cut, alpha < 128 transparent."""
    px = list(im.get_flattened_data())
    opaque = [p[:3] for p in px if p[3] >= 128]
    strip = Image.new('RGB', (len(opaque), 1)); strip.putdata(opaque)
    q = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT, kmeans=10, dither=Image.Dither.NONE)
    flat = q.getpalette()
    pal = [None] + [_rgb5(tuple(flat[3 * i:3 * i + 3])) for i in range(15)]
    it = iter(q.get_flattened_data())
    out = Image.new('L', im.size); out.putdata([0 if p[3] < 128 else next(it) + 1 for p in px])
    return out, pal


def hue_of(cols, min_n=20):
    """Dominant hue (degrees) of the saturated colours, or None for a grey icon."""
    xs = ys = n = 0
    for r, g, b in cols:
        h, l, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if sat > .25 and .12 < l < .9:
            xs += math.cos(2 * math.pi * h); ys += math.sin(2 * math.pi * h); n += 1
    return None if n < min_n else math.degrees(math.atan2(ys, xs)) % 360
