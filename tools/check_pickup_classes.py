"""Full-data check of how item pickups can leave a map icon behind (every RDT item_aot_set of every stage/room/character).

The mod draws one icon per item_aot_set record while its pickup flag (0xC3876C bit) is set; the game's pickup handler
(0x414240) clears the flag of the one AOT that was taken, and the script op that creates an item AOT (0x418c00) places it only
while that flag is set. So an icon can legitimately remain after a pickup only when another AOT is still unpicked. This check
enumerates, from data/rdt.json (extracted from the game's RDTs), the classes where that happens or can be mistaken for a bug:
  stack    several AOTs with different flags at the same point (two clips on Kenneth's body): one icon each, drawn on top of each other
  event    an item AOT overlapping an `event` / useitem / typewriter AOT (scripted pickups)
  shared   the same flag on two AOTs with different items in one room/scenario: taking either clears the shared bit, so the map
           hides both icons although the other AOT stays takable until the room reloads (the opposite of an icon that stays)
  range    pickup flag outside the 13-dword table (cannot be tracked)
Exit status is non-zero only for `range` (a flag the mod cannot read); stack/event/shared are reported, not errors. Usage: python tools/check_pickup_classes.py [--list]
"""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
rdt = json.loads((ROOT / 'data/rdt.json').read_text())
rooms = json.loads((ROOT / 'data/annotated.json').read_text())['rooms']
items = json.loads((ROOT / 'data/items.json').read_text())
name = lambda i: items.get(str(i), {}).get('en', f'item {i}') if isinstance(items.get(str(i)), dict) else str(items.get(str(i), f'item {i}'))
STAGE = {1: 'Mansion 1F', 2: 'Mansion 2F', 3: 'Courtyard/Caves', 4: 'Guardhouse/Lab', 5: 'Lab', 6: 'Mansion revisit', 7: 'Courtyard revisit'}
def room_name(stage, room):
    r = rooms.get(f'{(stage - 1) % 5}-{room:02X}')
    return f"{r['name_en']} / {r['name_ko']}" if r else f'room {room:02X} (no map name)'
stacks, events, shared, rng = collections.defaultdict(set), collections.defaultdict(set), [], []
for key, v in sorted(rdt.items()):
    recs = v['records']; ch = 'Chris' if v['player'] == 0 else 'Jill'
    its = [x for x in recs if x['op'] == 'item']
    byflag = collections.defaultdict(set)
    for it in its:
        byflag[it['flag']].add(it['item'])
        if it['flag'] >= 13 * 32: rng.append((key, it['flag']))
    for f, s in byflag.items():
        if len(s) > 1: shared.append((key, f, sorted(s)))
    pos = collections.defaultdict(list)
    for it in its: pos[(it['x'], it['z'])].append(it)
    for p, l in pos.items():
        if len({i['flag'] for i in l}) > 1:
            stacks[(v['stage'], v['room'], tuple(sorted((i['item'], i['flag']) for i in l if True)))].add(ch)
    for it in its:
        for o in recs:
            if o['op'] == 'aot' and o['sce'] in ('event', 'useitem', 'typewriter') and abs(o['x'] - it['x']) <= 300 and abs(o['z'] - it['z']) <= 300:
                events[(v['stage'], v['room'], it['item'], it['flag'], o['sce'])].add(ch)
if '--list' in sys.argv:
    print('STACKS (one icon per flag, same point):')
    for (st, rm, fl), who in sorted(stacks.items()):
        print(f"  {STAGE.get(st, st)} {room_name(st, rm)}: " + ', '.join(f'{name(i)}[flag {f}]' for i, f in fl) + f' ({"+".join(sorted(who))})')
    print('EVENT-OVERLAPPED item AOTs:')
    for (st, rm, it, fl, sce), who in sorted(events.items()):
        print(f"  {STAGE.get(st, st)} {room_name(st, rm)}: {name(it)}[flag {fl}] under a {sce} AOT ({'+'.join(sorted(who))})")
kenneth = [k for k in stacks if k[0] == 1 and k[1] == 4]
assert kenneth and sorted(f for _, f in kenneth[0][2]) == [41, 47] and all(i == 11 for i, _ in kenneth[0][2]), 'Kenneth: two Hand Gun Bullets AOTs, flags 41 and 47'
print(f'{len(stacks)} stacked groups, {len(events)} event-overlapped item AOTs, {len(shared)} shared-flag conflicts, {len(rng)} out-of-range flags')
for k, f, its in shared: print('SHARED', k, f'flag {f}', [name(i) for i in its])
for r in rng: print('RANGE', r)
sys.exit(1 if rng else 0)
