"""Minimal RE1 (PC) RDT/SCD reader. Opcode sizes/signatures from BioRand biohazard-utils Bio1ConstantTable."""
import struct, sys
from pathlib import Path

SIZES = [2, 2, 2, 2, 4, 4, 4, 6, 4, 2, 2, 4, 26, 18, 2, 8,
         2, 2, 10, 4, 4, 2, 2, 10, 26, 4, 2, 22, 6, 2, 4, 28,
         14, 14, 4, 2, 4, 4, 0, 2, 6, 2, 12, 4, 2, 4, 0, 4,
         12, 4, 4, 2, 8, 4, 4, 4, 4, 2, 4, 6, 6, 12, 2, 6,
         16, 4, 4, 4, 2, 2, 44, 14, 2, 2, 2, 2, 4, 2, 4, 2, 2]
NAMES = ("end if else endif ck set cmpb cmpw setb cutnext cutcurr message door_aot_set aot_set nop scene_setup "
         "testitem testpickup aot_reset aot_delete evt_exec bgm_play bgm_stop se_play_3d item_aot_set setbyte item_ck "
         "enemy timer_setup ck_last_item xa_on obj dir_set pos_set ck_item_count cut_auto aot_on aot_switch op26 "
         "snd_fadeout eml_state movie_on effect plw_anim remove_item give_item op2e se_volume inst_cfg setw nop_wide "
         "sys_multi model_op objtbl_b_set ck_anim tbl37_set ck_bits get_eml_state msgnode_set eml_rot ck_counter "
         "effect_tracked effect_kill_a ck_tween obj_xfm spd_set effect_kill_b se_rate task_kill spd_add msg_list "
         "eml_pos effect_clear bank_bit bgm_bank_down bgm_bank_up swap_var objs_hide mass_mask xa_flag xa_flag_ck").split()


def offsets(data):
    return struct.unpack_from('<19I', data, 0x48)


def script_block(data, off):
    """Init/main SCD: u16 byte length followed by bytecode."""
    n = struct.unpack_from('<H', data, off)[0]
    return data[off + 2: off + 2 + n]


def ops(code, base=0):
    """Yield (pos, opcode, raw bytes). Stops on unknown/zero-size opcode."""
    i = 0
    while i < len(code):
        op = code[i]
        size = SIZES[op] if op < len(SIZES) else 0
        if size == 0 or i + size > len(code):
            yield base + i, op, code[i:i + 2], True
            return
        yield base + i, op, code[i:i + size], False
        i += size


def load(path):
    data = Path(path).read_bytes()
    o = offsets(data)
    return data, o, script_block(data, o[6]), script_block(data, o[7])



# ---- event scripts (RDT offset 8): port of biohazard-utils ScdReader.ReadScript1Event (scd_event_loop @0x42E190).
# Top-level ops 00..09 and control F6..FF; 01 enters the actor sub-ISA (exit 80/8B), 02/03 the tween sub-ISA (exit 01).
# SCD ops (main-SCD encoding) live inside 06 Block (u8 len, then u16-length-prefixed groups), 07 Single and FC Do payloads.
EVT_SIZE = {3: 1, 4: 3, 5: 4, 6: 2, 7: 2, 8: 2, 9: 2, 0xE8: 4, 0xF8: 4, 0xFA: 4, 0xFC: 2, 0xFF: 1}
ACTOR_SIZE = {0: 1, 0x80: 1, 0x81: 2, 0x82: 1, 0x83: 7, 0x84: 4, 0x85: 4, 0x86: 1, 0x87: 4, 0x88: 4, 0x89: 2, 0x8A: 2, 0x8B: 1, 0xFF: 1}
TWEEN_SIZE = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 4, 6: 4, 7: 8, 8: 3, 9: 2, 0xA: 4, 0xB: 8, 0xFF: 1}


def event_scripts(data, o):
    """List of event script byte strings; chunk ends at the next RDT chunk offset."""
    base = o[8]
    if not base:
        return []
    end = min([x for x in o if x > base] + [len(data)])
    offs = []
    for i in range((end - base) // 4):
        v = struct.unpack_from('<I', data, base + 4 * i)[0]
        if v == 0:
            break
        offs.append(v)
        if 4 * (i + 1) >= offs[0]:
            break
    return [data[base + a: base + (offs[i + 1] if i + 1 < len(offs) else end - base)] for i, a in enumerate(offs)]


def _scd_seq(code, base, out):
    i = 0
    while i < len(code):
        op = code[i]
        size = SIZES[op] if op < len(SIZES) else 0
        if size == 0 or i + size > len(code):
            return
        out.append((base + i, op, code[i:i + size]))
        i += size


def event_ops(code):
    """SCD ops (pos, op, raw) embedded in one event script, plus ('evt', pos, opcode, raw) top-level entries."""
    out, i, sub = [], 0, None
    while i < len(code):
        op = code[i]
        if sub is not None and op < 0xF6:
            if (sub == 'a' and op in (0x80, 0x8B)) or (sub == 't' and op == 1):
                sub = None; i += 1; continue
            size = (2 + (8 if i + 1 < len(code) and code[i + 1] & 15 else 0)) if sub == 'a' and op == 0x81 else (ACTOR_SIZE if sub == 'a' else TWEEN_SIZE).get(op, 0)
            if size and i + size <= len(code):
                i += size; continue
            sub = None   # unknown sub op: resume top level at the same byte (as the reference reader does)
        if op == 0xFF:
            sub = None; i += 1; continue
        if sub is None and op in (1, 2):
            sub = 'a' if op == 1 else 't'; i += 1; continue
        if sub is None and op == 3:
            sub = 't'; i += 1; continue
        if i + 2 > len(code):
            return out
        n = code[i + 1]
        if sub is None and op == 6:   # Block: groups of u16 total length (incl. the u16) + SCD ops, 0 terminates
            blk, j = code[i + 2: i + 1 + n], 0
            while j + 2 <= len(blk):
                g = struct.unpack_from('<H', blk, j)[0]
                if g == 0:
                    break
                _scd_seq(blk[j + 2: j + g], i + 2 + j + 2, out)
                j += g
            i += 2 + max(n - 1, 0); continue
        if (sub is None and op == 7) or op == 0xFC:
            _scd_seq(code[i + 2: i + n], i + 2, out)
            i += max(n, 2); continue
        if sub is None and op == 0x81:
            i += 2 + (8 if n & 15 else 0); continue
        size = EVT_SIZE.get(op, 1)
        out.append(('evt', i, op, code[i:i + size]))
        i += size
    return out


if __name__ == '__main__':
    data, o, init, main = load(sys.argv[1])
    for label, code in (('init', init), ('main', main)):
        print('==', label, len(code))
        for pos, op, raw, bad in ops(code):
            name = NAMES[op] if op < len(NAMES) else f'op{op:02x}'
            print(f'{pos:5x} {name:14s} {raw.hex(" ")}{"  <stop>" if bad else ""}')
