"""Name map slots from evilresource highlight images.

Each evilresource floor image is the game's map upscaled. Align each floor image to the best game
page by bbox (then IoU check), map the red highlight of every location page into TIM space and
vote for the slot owning those pixels. Output data/slot_names.json.
"""
import json
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent.parent
ER = ROOT / 'refs/evilresource'
maps = json.loads((ROOT / 'data/map_rooms.json').read_text())
urls = dict(l.split() for l in (ER / 'highlight_urls.txt').read_text().splitlines())
names = {}
for e in json.loads((ROOT / 'data/evilresource.json').read_text()):
    names.setdefault(e['page'], e['location'].split(' - ')[0])


# evilresource floor image -> game page (exe area table 0x4b1bd8 lists each area's pages bottom floor first)
FLOOR_PAGE = dict(mansion2f=1, mansion1f=0, mansionb1=2, courtyard=3, underground=4, guardhouse1f=5, guardhouseb1=6,
                  laboratoryb1=7, laboratoryb2=8, laboratoryb3=9, laboratoryb4=10)


def owner_maps():
    out = []
    for pg in maps['pages']:
        own = {}
        for r in pg['rooms']:
            for x, y in r['mask']:
                own[(x, y)] = r['slot']
        xs = [x for x, _ in own]
        ys = [y for _, y in own]
        out.append((own, (min(xs), min(ys), max(xs), max(ys))))
    return out


def er_mask(img):
    """Non-black map pixels of an evilresource floor image."""
    im = img.convert('RGB')
    w, h = im.size
    px = im.load()
    pts = {(x, y) for y in range(h) for x in range(w) if sum(px[x, y]) > 60}
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return pts, (min(xs), min(ys), max(xs), max(ys))


def transform(src_box, dst_box):
    sx = (dst_box[2] - dst_box[0] + 1) / (src_box[2] - src_box[0] + 1)
    sy = (dst_box[3] - dst_box[1] + 1) / (src_box[3] - src_box[1] + 1)
    return lambda x, y: (int(dst_box[0] + (x - src_box[0]) * sx), int(dst_box[1] + (y - src_box[1]) * sy))


def main():
    owners = owner_maps()
    floor_page = {}
    for f in sorted((ER / 'img').glob('re1_*.png')):
        floor = f.stem[4:]
        pts, box = er_mask(Image.open(f))
        best = None
        for p, (own, obox) in enumerate(owners):
            if p != FLOOR_PAGE[floor]:
                continue
            t = transform(box, obox)
            hit = Counter(own.get(t(x, y)) is not None for x, y in pts)
            score = hit[True] / max(1, len(pts)) * min(len(own), len(pts) / 9) / max(len(own), len(pts) / 9)
            if not best or score > best[0]:
                best = (score, p, t)
        floor_page[floor] = best
        print(floor, '-> page', best[1], round(best[0], 3))
    result = {}
    for page, url in urls.items():
        floor = url.split('/')[-2][4:]
        hl = ER / 'img/hl' / f'{page}.png'
        if floor not in floor_page or not hl.exists():
            continue
        score, p, t = floor_page[floor]
        im = Image.open(hl).convert('RGB')
        px = im.load()
        w, h = im.size
        votes = Counter()
        for y in range(h):
            for x in range(w):
                r, g, b = px[x, y]
                if r > 150 and g < 60 and b < 60:
                    votes[owners[p][0].get(t(x, y))] += 1
        votes.pop(None, None)
        if votes:
            (slot, n), = votes.most_common(1)
            result.setdefault(str(p), {}).setdefault(str(slot), []).append(dict(page=page, name=names.get(page, page), votes=n, total=sum(votes.values())))
    (ROOT / 'data/slot_names.json').write_text(json.dumps(result, indent=1))
    for p in sorted(result, key=int):
        for s in sorted(result[p], key=int):
            print(p, s, [(v['name'], v['votes'], v['total']) for v in result[p][s]])


if __name__ == '__main__':
    main()
