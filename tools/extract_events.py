"""Story-scene (event) triggers from the RDT scripts -> data/events.json.

Every scene runs an event script (RDT offset 8, read with rdt1.event_ops) started either by an `event` AOT (aot_set sce 9,
data[2] = script index) or by `evt_exec` (op 0x14, raw[3] = script index) in the room's init/main SCD. A trigger is a
story scene when its script closure (plus scripts it starts with evt_exec) plays a movie (movie_on) or at least two voice
streams (xa_on) with a camera cut. Its done-flag is a persistent flag (group 0/1) the scene sets ON (in the script closure
or in the trigger's own SCD region) that the trigger's guard requires OFF; failing that, the single persistent flag the
scene sets. A flag that other rooms also set (e.g. Flg_1[192], set by 11 rooms) is used only when nothing room-specific
remains. Scenes without one are listed in `undetermined` and get no marker. Rooms in BOSS_ROOMS (entering starts a boss
fight; the boss keeps its enemy marker) and scenes that are a puzzle's own animation (PUZZLE_SCENES) are left out.
Position: the AOT centre for AOT triggers; init/main triggers (on entry or by camera) use the room anchor (null).
Output keys follow norm_room_key: map stage = (folder - 1) % 5.
"""
import collections, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import rdt1

GAME = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn'
OUT = Path(__file__).parent.parent / 'data' / 'events.json'
RDT = json.loads((Path(__file__).parent.parent / 'data' / 'rdt.json').read_text())
PERSISTENT = (0, 1)
# (folder stage, room): entering starts the boss fight (Plant 42 room intro, Main Lab Wesker/Tyrant, Heliport)
BOSS_ROOMS = {(4, 0x0C): 'Plant 42 boss', (5, 0x13): 'Tyrant boss (Main Lab)', (3, 0x03): 'Tyrant boss (Heliport)'}
# scenes that animate a puzzle's result (the puzzle marker carries the same flag): Water Gate drain, Fountain drain
PUZZLE_SCENES = {(3, 0x01): 'Water Gate drain movie (puzzle)', (3, 0x05): 'Fountain drain movie (puzzle)'}


def script_info(path):
    data, o, init, main = rdt1.load(path)
    info = []
    for code in rdt1.event_scripts(data, o):
        ops = [x for x in rdt1.event_ops(code) if x[0] != 'evt']
        info.append(dict(cnt=collections.Counter(rdt1.NAMES[x[1]] for x in ops),
                         sets=[(x[2][1], x[2][2]) for x in ops if x[1] == 5 and x[2][3] == 0 and x[2][1] in PERSISTENT],
                         sub=[x[2][3] for x in ops if x[1] == 0x14]))
    return info


def closure(info, k, seen=None):
    seen = set() if seen is None else seen
    if k not in seen and k < len(info):
        seen.add(k)
        for s in info[k]['sub']:
            closure(info, s, seen)
    return seen


def guard_cks(guards):
    """[(group, bit, is_set)] of plain (non-negated) guard regions."""
    return [(c['group'], c['bit'], c['is_set']) for g in guards if not g['negated'] for c in g['conds'] if c['kind'] == 'ck']


def main():
    events, undetermined, skipped = [], [], []
    infos = {key: script_info(GAME / f'Stage{key[0]}' / f'ROOM{key}.RDT') for key in RDT}
    setters = collections.defaultdict(set)   # persistent flag -> map rooms whose scripts set it
    for key, v in RDT.items():
        here = ((v['stage'] - 1) % 5, v['room'])
        for x in v['records']:
            if x.get('op') == 'set' and x['value'] == 0 and x['group'] in PERSISTENT:
                setters[(x['group'], x['bit'])].add(here)
        for i in infos[key]:
            for f in i['sets']:
                setters[f].add(here)
    for key, v in sorted(RDT.items()):
        info = infos[key]
        recs = v['records']
        for r in recs:
            if r.get('op') == 'aot' and r.get('sce') == 'event':
                idx, at = r['data'][2], [r['x'] + r['w'] // 2, r['z'] + r['h'] // 2]
            elif r.get('op') == 'evt_exec':
                idx, at = r['event'], None
            else:
                continue
            cl = closure(info, idx)
            cnt = sum((info[i]['cnt'] for i in cl), collections.Counter())
            if not (cnt['movie_on'] or (cnt['xa_on'] >= 2 and cnt['cutnext'] + cnt['cut_auto'])):
                continue
            region = [(x['group'], x['bit']) for x in recs if x.get('op') == 'set' and x['block'] == r['block']
                      and x['guards'] == r['guards'] and x['value'] == 0 and x['group'] in PERSISTENT]
            sets = list(dict.fromkeys([s for i in sorted(cl) for s in info[i]['sets']] + region))
            need_off = {(g, b) for g, b, on in guard_cks(r['guards']) if not on}
            here = ((v['stage'] - 1) % 5, v['room'])
            own = [s for s in sets if setters[s] == {here}] or sets
            flag = next((s for s in own if s in need_off), own[0] if len(own) == 1 else None)
            rec = dict(key=key, stage=v['stage'], room=v['room'], player=v['player'], trigger=r['op'], block=r['block'],
                       pos=r['pos'], script=idx, scripts=sorted(cl), xa=cnt['xa_on'], movie=cnt['movie_on'], sets=sets,
                       guard=guard_cks(r['guards']))
            why = BOSS_ROOMS.get((v['stage'] - (5 if v['stage'] >= 6 else 0), v['room'])) or \
                PUZZLE_SCENES.get((v['stage'] - (5 if v['stage'] >= 6 else 0), v['room']))
            if why:
                skipped.append(dict(rec, reason=why))
            elif flag is None:
                undetermined.append(dict(rec, reason='no persistent flag set by the scene' if not sets else 'several flags, none tested by the trigger'))
            else:
                events.append(dict(rec, flag=list(flag), at=at))
    OUT.write_text(json.dumps(dict(events=events, undetermined=undetermined, skipped=skipped), indent=1))
    print(len(events), 'events,', len(undetermined), 'undetermined,', len(skipped), 'skipped')


if __name__ == '__main__':
    main()
