"""PSX TIM -> PNG (4/8/16 bpp). Usage: tim.py in.tim out.png [clut_index]"""
import struct, sys
from PIL import Image


def rgb555(c):
    return ((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31, 0 if c == 0 else 255)


def load(path, clut_index=0):
    d = open(path, 'rb').read()
    flags = struct.unpack_from('<I', d, 4)[0]
    bpp, p = flags & 3, 8
    cluts = []
    if flags & 8:
        blen, _, _, cw, ch = struct.unpack_from('<IHHHH', d, p)
        cluts = [[rgb555(struct.unpack_from('<H', d, p + 12 + (r * cw + i) * 2)[0]) for i in range(cw)] for r in range(ch)]
        p += blen
    blen, x, y, w, h = struct.unpack_from('<IHHHH', d, p)
    px = d[p + 12:p + blen]
    width = w * (4 if bpp == 0 else 2 if bpp == 1 else 1)
    img = Image.new('RGBA', (width, h))
    pal = cluts[clut_index] if cluts else None
    out = []
    for i in range(width * h):
        if bpp == 0:
            out.append(pal[(px[i // 2] >> ((i & 1) * 4)) & 15])
        elif bpp == 1:
            out.append(pal[px[i]])
        else:
            out.append(rgb555(struct.unpack_from('<H', px, i * 2)[0]))
    img.putdata(out)
    return img, dict(bpp=bpp, vram=(x, y), cluts=len(cluts))


if __name__ == '__main__':
    img, info = load(sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    img.save(sys.argv[2])
    print(sys.argv[1], img.size, info)
