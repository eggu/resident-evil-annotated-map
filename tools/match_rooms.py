"""Match evilresource location pages to RE1 (stage, room) by item contents + door adjacency.

Writes data/room_match.json: {"1-05": {"page": ..., "name": ..., "score": ...}} for map stages 1..5 (folder numbers).
Heuristic; review the printed low-confidence rows by hand.
"""
import html, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
rdt = json.loads((ROOT / 'data/rdt.json').read_text())
items = {int(k): v['en'].lower() for k, v in json.loads((ROOT / 'data/items.json').read_text()).items()}
er = json.loads((ROOT / 'data/evilresource.json').read_text())

ALIAS = {'clip': 'hand gun bullets', 'shells': 'shotgun shells', 'emblem': 'emblem', 'lockpick': 'lockpick',
         'first aid spray': 'first aid spray', 'mo disk': 'mo-disk', 'music notes': 'music score', 'hex crank': 'hexagonal crank',
         'square crank': 'square crank', 'fuel canteen': 'fuel', 'flamethrower fuel': 'fuel', '002 key': 'key for room 002',
         '003 key': 'key for room 003', 'yellow-6': 'yellow-6', 'v-jolt': 'v-jolt', 'empty bottle': 'empty bottle',
         'blank book': 'blank book', 'mixed herbs': 'mixed herbs', 'umb no. 2': 'umb no.2', 'umb no. 4': 'umb no.4',
         'umb no. 7': 'umb no.7', 'umb no. 13': 'umb no.13'}


def norm(n):
    n = re.sub(r'\s*\(.*?\)', '', n.lower()).strip()
    return ALIAS.get(n, n)


# --- evilresource pages: original-version (Jill/Chris) contents and links
pages = defaultdict(lambda: dict(items=Counter(), links=set(), name=''))
for e in er:
    if e['mode'] not in ('Jill', 'Chris'):
        continue
    p = pages[e['page']]
    p['name'] = e['location'].split(' - ')[0]
    p['items'][norm(e['name'])] += 1
for f in (ROOT / 'refs/evilresource/pages').glob('*.html'):
    h = f.read_text(errors='replace')
    m = re.search(r'linked to the following locations:</p>\s*<ul>(.*?)</ul>', h, re.S)
    p = pages[f.stem]
    if not p['name']:
        t = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        p['name'] = html.unescape(re.sub(r'<[^>]+>', '', t.group(1))).split('(')[0].split(' - ')[0].strip()
    if m:
        for href in re.findall(r'href="/resident-evil/maps/([^"]+)"', m.group(1)):
            p['links'].add(href.replace('/', '_'))

# --- rdt rooms (folder stages 1..5; 6/7 are mansion revisits of 1/2)
rooms = defaultdict(lambda: dict(items=Counter(), links=set()))
for key, v in rdt.items():
    s, r = v['stage'], v['room']
    base = (s - 1) % 5 + 1
    node = (base, r)
    seen = set()
    for x in v['records']:
        if x['op'] == 'item' and (x['flag'], x['item']) not in seen:
            seen.add((x['flag'], x['item']))
            rooms[node]['items'][items.get(x['item'], str(x['item']))] += 1
        if x['op'] == 'door':
            ts = x['target_stage'] or s
            rooms[node]['links'].add(((ts - 1) % 5 + 1, x['target_room']))
    rooms[node]  # ensure exists


def item_score(pi, ri):
    common = set(pi) & set(ri)
    return sum(3 if n not in ('hand gun bullets', 'shotgun shells', 'green herb', 'ink ribbon', 'red herb', 'blue herb') else 1 for n in common)


page_ids = sorted(pages)
node_ids = sorted(rooms)
assign = {}
for it in range(6):
    inv = {p: n for n, p in assign.items()}
    scored = []
    for n in node_ids:
        for p in page_ids:
            s = item_score(pages[p]['items'], rooms[n]['items'])
            # neighbour agreement with current assignment
            s += 2 * sum(1 for ln in rooms[n]['links'] if assign.get(ln) in pages[p]['links'])
            s -= abs(len(pages[p]['links']) - len(rooms[n]['links'])) * 0.3
            if s > 0:
                scored.append((s, n, p))
    scored.sort(reverse=True)
    new, used = {}, set()
    for s, n, p in scored:
        if n in new or p in used:
            continue
        new[n] = p
        used.add(p)
    assign = new

out = {}
for n in node_ids:
    p = assign.get(n)
    out[f'{n[0]}-{n[1]:02X}'] = dict(page=p, name=pages[p]['name'] if p else None,
                                     rdt_items=sorted(rooms[n]['items']), links=sorted(f'{a}-{b:02X}' for a, b in rooms[n]['links']))
(ROOT / 'data/room_match.json').write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(k, v['name'], '|', ','.join(v['rdt_items'])[:70], '|', ' '.join(v['links']))
