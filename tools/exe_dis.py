"""Disassemble Biohazard.exe (GOG, base 0x400000): python tools/exe_dis.py <va> [count]"""
import os, struct, sys
from pathlib import Path
import capstone
D = (Path(os.environ['RE1_GAME_DIR']) / 'Biohazard.exe').read_bytes()
pe = struct.unpack_from('<I', D, 0x3c)[0]; n = struct.unpack_from('<H', D, pe + 6)[0]; so = struct.unpack_from('<H', D, pe + 20)[0]
S = [struct.unpack_from('<IIII', D, pe + 24 + so + i * 40 + 8) for i in range(n)]
def rd(va, k):
    for vs, a, rs, ro in S:
        if 0x400000 + a <= va < 0x400000 + a + max(vs, rs): return D[ro + va - 0x400000 - a:][:k]
    return bytes(k)
if __name__ == '__main__':
    va, cnt = int(sys.argv[1], 0), int(sys.argv[2]) if len(sys.argv) > 2 else 40
    for i, ins in enumerate(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(rd(va, cnt * 8), va)):
        if i >= cnt: break
        print(f'{ins.address:#x}  {ins.mnemonic} {ins.op_str}')
