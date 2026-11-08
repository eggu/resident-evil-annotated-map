"""Colour distinctness check for the legend/name colours (RGB555 as displayed): CIEDE2000 between categories and WCAG contrast
against the map floor / background / terrain colours. Usage: python tools/check_colours.py  (reads src/overlay_data.h)"""
import math, re, sys
from pathlib import Path
H = (Path(__file__).parent.parent / 'src/overlay_data.h').read_text()
def pal(name):
    body = H.split(f'{name}[16]={{', 1)[1].split('}', 1)[0]
    return [tuple(((f << 3) | (f >> 2)) for f in (v & 31, (v >> 5) & 31, (v >> 10) & 31)) if v else None for v in map(int, body.split(','))]
def lin(c): c /= 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def lum(rgb): r, g, b = map(lin, rgb); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def wcag(a, b): la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + 0.05) / (lb + 0.05)
def lab(rgb):
    r, g, b = map(lin, rgb)
    x, y, z = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b, (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))
def de2000(c1, c2):
    L1, a1, b1 = lab(c1); L2, a2, b2 = lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7))); a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1p)) % 360, math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2 - h1 + 540) % 360 - 180
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    hm = h1 + h2 if C1p * C2p == 0 else (h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    T = 1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm)) + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.2 * math.cos(math.radians(4 * hm - 63))
    Sl, Sc, Sh = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2), 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -2 * math.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-(((hm - 275) / 25) ** 2))))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))
if __name__ == '__main__':
    L = pal('ov_legend_palette')
    cats = {'room names (cream)': L[2], 'locks (gold)': L[5], 'key items (cyan)': L[3], 'documents (pink)': L[4], 'puzzles (orange)': L[6],
            'common items (lavender)': L[7], 'enemies (red)': L[10], 'hints (dim grey)': L[9], 'header/white': L[15], 'OFF rows': L[8]}
    print('displayed RGB:', {k: v for k, v in cats.items()})
    com = L[7]
    print('\nCIEDE2000 of common items (lavender) vs each other category (>= 20 is clearly distinct; 10 is "noticeable"):')
    for k, v in cats.items():
        if v is not com: print(f'  {k:24s} {de2000(com, v):5.1f}')
    old = (255, 120, 60)
    print(f'\nold common colour {old}: vs puzzles {de2000(old, L[6]):.1f}, vs cream rooms {de2000(old, L[2]):.1f}; new vs puzzles {de2000(com, L[6]):.1f}, vs cream {de2000(com, L[2]):.1f}')
    # what the names really sit on: the background grid (only the palette entries its pixels use) and the room fill, which the
    # game draws at 50 % over it (terrain quad alpha 0.5, see ov_scale_command); names also carry a black outline
    bgpix = [int(v) for v in H.split('ov_background_pixels[32768]={', 1)[1].split('}', 1)[0].split(',')]
    used = sorted({b & 15 for b in bgpix} | {b >> 4 for b in bgpix}); B = pal('ov_background_palette'); T = pal('ov_terrain_palette')
    grid = [B[i] for i in used if B[i]]
    print('\nbackground grid colours actually used:', grid)
    mix = lambda a, b: tuple((x + y) // 2 for x, y in zip(a, b))
    rows = {}
    for ti, tc in enumerate(T):
        if tc:
            for bc in grid: rows[(ti, bc)] = mix(tc, bc)
    print('contrast of each category colour against the grid and against every room fill (50 % over the grid), worst case:')
    for k, v in cats.items():
        if not v or k in ('OFF rows',): continue
        vs = [wcag(v, bc) for bc in grid] + [wcag(v, c) for c in rows.values()]
        print(f'  {k:24s} grid {min(wcag(v, bc) for bc in grid):5.2f}:1   worst floor {min(wcag(v, c) for c in rows.values()):5.2f}:1   (black outline {wcag(v, (16, 16, 16)):4.1f}:1)')
    worst = [(wcag(com, c), ti, bc, c) for (ti, bc), c in rows.items()]
    w = min(worst); print(f'lavender on its worst room fill: terrain[{w[1]}] over grid {w[2]} -> {w[3]}: {w[0]:.2f}:1')
    print('\nlightness ordering (L*): ' + ', '.join(f'{k.split(" (")[0]} {lab(v)[0]:.0f}' for k, v in cats.items() if v))
