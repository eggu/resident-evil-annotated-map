"""List every call to the pickup-flag helpers in Biohazard.exe with the immediate arguments pushed just before it.

Usage: RE1_GAME_DIR=<game> python tools/exe_flag_calls.py [target_va ...]   (default 0x414fe0 Flg_off, 0x414f90 Flg_on guess)
"""
import os, struct, sys
from pathlib import Path
import capstone
exe = Path(os.environ['RE1_GAME_DIR']) / 'Biohazard.exe'
D = exe.read_bytes()
pe = struct.unpack_from('<I', D, 0x3c)[0]
n = struct.unpack_from('<H', D, pe + 6)[0]; so = struct.unpack_from('<H', D, pe + 20)[0]
secs = []
for i in range(n):
    o = pe + 24 + so + i * 40
    vs, va, rs, ro = struct.unpack_from('<IIII', D, o + 8)
    secs.append((0x400000 + va, vs, rs, ro, struct.unpack_from('<I', D, o + 36)[0]))
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail = False
targets = [int(a, 0) for a in sys.argv[1:]] or [0x414fe0]
for va, vs, rs, ro, ch in secs:
    if not ch & 0x20000000: continue
    code = D[ro:ro + rs]
    hist = []
    for ins in md.disasm(code, va):
        hist.append(ins); hist = hist[-8:]
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x') and int(ins.op_str, 16) in targets:
            pushes = [h.op_str for h in hist[:-1] if h.mnemonic == 'push']
            print(f'{ins.address:#x} call {ins.op_str} pushes={pushes}')
