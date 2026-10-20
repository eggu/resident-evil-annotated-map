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


if __name__ == '__main__':
    data, o, init, main = load(sys.argv[1])
    for label, code in (('init', init), ('main', main)):
        print('==', label, len(code))
        for pos, op, raw, bad in ops(code):
            name = NAMES[op] if op < len(NAMES) else f'op{op:02x}'
            print(f'{pos:5x} {name:14s} {raw.hex(" ")}{"  <stop>" if bad else ""}')
