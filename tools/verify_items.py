"""Cross-check RDT item pickups against evilresource room contents (original Chris/Jill modes).

An RDT item_aot_set only says the engine *can* place an item; swap states (Broken Shotgun back on the rack),
cutscene hand-overs (Barry, Rebecca) and unused records also live there. Only items evilresource lists in
that room for that character as found there (not "given to you") are shown on the map.
"""
import json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
# our item names (data/items.json) -> evilresource names
ALIAS = {'beretta': 'beretta m92fs', 'comm. radio': 'radio', 'grenade gun': 'bazooka', 'hand gun bullets': 'clip',
         'hexagonal crank': 'hex crank', 'key for room 002': '002 key', 'key for room 003': '003 key', 'mo-disk': 'mo disk',
         'map of 1f': 'map of the first floor', 'map of 2f': 'map of the second floor', 'music score': 'music notes',
         'plant-42 report': 'plant 42 report', 'shotgun': 'remington m870', 'shotgun shells': 'shell', 'v-jolt report': '"v-jolt" report'}
PLURAL = ('clip', 'shell', 'green herb', 'red herb', 'blue herb', 'empty bottle')
GIVEN = re.compile(r'given to you|give (these|this|it) to you|gives you|hands? you', re.I)
MODE = {'Chris': 0, 'Jill': 1}


def norm(name):
    n = re.sub(r'\s*\(.*?\)', '', name).strip().lower()
    n = re.sub(r'^\d\s+', '', n)                     # "2 Green Herbs" (but not "002 Key")
    return n[:-1] if n.endswith('s') and n[:-1] in PLURAL else n


def load_pages():
    """evilresource page -> [(name, char, desc)] for original modes; plus location name -> pages."""
    contents, by_name = defaultdict(list), defaultdict(set)
    for x in json.loads((ROOT / 'data/evilresource.json').read_text()):
        by_name[x['location'].split(' - ')[0].strip()].add(x['page'])
        if x['mode'] in MODE and x['category'] != 'enemies':
            contents[x['page']].append((norm(x['name']), MODE[x['mode']], x['desc']))
    return contents, by_name


def verdict(name_en, char, pages, contents):
    """'pickup' / 'given' / 'unlisted' and the evilresource description used."""
    want = ALIAS.get(name_en.lower(), norm(name_en))
    hits = [(p, desc) for p in sorted(pages) for n, c, desc in contents.get(p, []) if n == want and c == char]
    for p, desc in hits:
        if not GIVEN.search(desc.split('. ')[0]):   # "Next to Forest. If Barry is with you, he will hand you..." is a pickup
            return 'pickup', p, desc
    return ('given', *hits[0]) if hits else ('unlisted', None, None)
