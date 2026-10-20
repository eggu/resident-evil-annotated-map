"""Extract doors, item pickups and interaction AOTs (with SCD guard conditions) from every RE1 RDT.

Output: data/rdt.json  {"<stage><room><player>": {...}}
Stage digit is the folder number (1..7); map stage = (stage-1) % 5.
"""
import json, os, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import rdt1

GAME = Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'jpn'
OUT = Path(__file__).parent.parent / 'data' / 'rdt.json'
SCE = {1: 'door', 2: 'message', 7: 'useitem', 8: 'itembox', 9: 'event', 10: 'save', 13: 'document', 14: 'drawer', 16: 'typewriter'}


def cond_text(raw):
    op = raw[0]
    if op == 4:  # ck group bit value
        # handler 0x417f50 returns flag XOR raw[3]: raw[3]=0 passes when the flag is set
        return dict(kind='ck', group=raw[1], bit=raw[2], is_set=int(raw[3] == 0))
    if op == 6:
        return dict(kind='cmpb', a=raw[1], b=raw[2], c=raw[3])
    if op == 7:
        return dict(kind='cmpw', raw=raw[1:].hex())
    if op == 0x10:
        return dict(kind='testitem', item=raw[1])
    if op == 0x11:
        return dict(kind='testpickup', item=raw[1])
    if op == 0x1a:
        return dict(kind='item_ck', item=raw[1])
    return dict(kind=rdt1.NAMES[op] if op < len(rdt1.NAMES) else hex(op), raw=raw.hex())


def walk(code, sink, block):
    """Linear walk tracking if/else nesting. Conditions following an `if` belong to it until the next non-condition op."""
    stack = []  # (end_pos, conds, negated)
    pending = None
    closed = None   # the if-block that ended exactly here: a following `else` belongs to it
    for pos, op, raw, bad in rdt1.ops(code):
        closed = None
        while stack and pos >= stack[-1][0]:
            closed = stack.pop()
        if bad:
            sink.append(dict(block=block, pos=pos, op='invalid', raw=raw.hex()))
            return
        if op == 1:  # if: u8 pad?, u8 len -> raw[1] is skip length from after header
            pending = dict(end=pos + raw[1], conds=[])   # block ends at op start + len (else/endif there: 2770/2774)
            stack.append([pending['end'], pending['conds'], False])
            continue
        if op == 2:  # else: belongs to the if that just closed at this position (not the enclosing one)
            if closed is not None and closed[0] == pos:
                stack.append([pos + raw[1], closed[1], True])
            elif stack:
                end, conds, _ = stack.pop()
                stack.append([pos + raw[1], conds, True])
            pending = None
            continue
        if op == 3:
            pending = None
            continue
        if pending is not None and op in (4, 6, 7, 0x10, 0x11, 0x1a):
            pending['conds'].append(cond_text(raw))
            continue
        pending = None
        guards = [dict(conds=c, negated=n) for _, c, n in stack]
        rec = dict(block=block, pos=pos, guards=guards)
        if op == 0x0c:
            (aid, x, z, w, d, special, unkb, anim, unkc, lock_id, target, nx, ny, nz, nd, lock_type, free) = struct.unpack_from('<BhhHHBBBBBBhhhhBB', raw, 1)
            stage = target >> 5
            rec.update(op='door', id=aid, x=x, z=z, w=w, d=d, lock_flag=lock_id, key=lock_type,
                       target_stage=stage, target_room=target & 31, free=free, special=special)
        elif op == 0x18:
            aid, x, z, w, h, item, amount = struct.unpack_from('<BhhhhBB', raw, 1)
            flag = raw[0x16]
            rec.update(op='item', id=aid, x=x, z=z, w=w, h=h, item=item, amount=amount, flag=flag, extra=raw[12:].hex())
        elif op == 0x0d:
            aid, x, z, w, h, sce, sat = struct.unpack_from('<BhhhhBB', raw, 1)
            rec.update(op='aot', id=aid, x=x, z=z, w=w, h=h, sce=SCE.get(sce, sce), sat=sat, data=list(raw[12:18]))
        elif op == 0x12:
            rec.update(op='aot_reset', id=raw[1], sce=SCE.get(raw[2], raw[2]), data=list(raw[4:10]))
        elif op == 0x13:
            rec.update(op='aot_delete', id=raw[1], raw=raw.hex())
        elif op in (5, 8):
            rec.update(op='set' if op == 5 else 'setb', group=raw[1], bit=raw[2], value=raw[3])
        elif op == 0x2c:
            rec.update(op='remove_item', item=raw[1])
        elif op == 0x2d:
            rec.update(op='give_item', raw=raw.hex())
        else:
            continue
        sink.append(rec)


def main():
    out = {}
    for path in sorted(GAME.glob('Stage*/*')):
        name = path.name.upper()
        if not (name.startswith('ROOM') and name.endswith('.RDT')):
            continue
        key = name[4:8]
        if path.stat().st_size < 0x94:  # unused-room stub
            continue
        data, o, init, main_ = rdt1.load(path)
        recs = []
        walk(init, recs, 'init')
        walk(main_, recs, 'main')
        out[key] = dict(stage=int(key[0]), room=int(key[1:3], 16), player=int(key[3]), records=recs)
    OUT.write_text(json.dumps(out, indent=1))
    print(len(out), 'rdts', sum(len(v['records']) for v in out.values()), 'records')


if __name__ == '__main__':
    main()
