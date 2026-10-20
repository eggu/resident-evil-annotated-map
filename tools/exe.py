"""Static helpers for Biohazard.exe (GOG, image base 0x400000)."""
import os, struct, sys
import capstone

EXE = str(Path(os.environ.get('RE1_GAME_DIR') or sys.exit('Set RE1_GAME_DIR to the game folder (Biohazard.exe, jpn/); see README')) / 'Biohazard.exe')
DATA = open(EXE, 'rb').read()
_pe = struct.unpack_from('<I', DATA, 0x3c)[0]
_n = struct.unpack_from('<H', DATA, _pe + 6)[0]
_so = struct.unpack_from('<H', DATA, _pe + 20)[0]
SECTIONS = []
for i in range(_n):
    o = _pe + 24 + _so + i * 40
    vs, va, rs, ro = struct.unpack_from('<IIII', DATA, o + 8)
    SECTIONS.append((0x400000 + va, vs, rs, ro))


def off(va):
    for sva, vs, rs, ro in SECTIONS:
        if sva <= va < sva + max(vs, rs):
            return ro + va - sva if va - sva < rs else None
    return None


def read(va, n):
    o = off(va)
    return DATA[o:o + n] if o is not None else bytes(n)


def u8(va): return read(va, 1)[0]
def u16(va): return struct.unpack('<H', read(va, 2))[0]
def s16(va): return struct.unpack('<h', read(va, 2))[0]
def u32(va): return struct.unpack('<I', read(va, 4))[0]


MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def dis(va, n=40):
    out = []
    for ins in MD.disasm(read(va, n * 8), va):
        out.append(f'{ins.address:08x} {ins.mnemonic} {ins.op_str}')
        if len(out) >= n:
            break
    return out


TEXT = SECTIONS[0]


def callers(target):
    """Direct E8 call / E9 jmp sites to target inside .text."""
    sva, vs, rs, ro = TEXT
    res = []
    for i in range(rs - 5):
        b = DATA[ro + i]
        if b in (0xE8, 0xE9):
            va = sva + i
            if (va + 5 + struct.unpack_from('<i', DATA, ro + i + 1)[0]) & 0xffffffff == target:
                res.append(va)
    return res


def imm_refs(value):
    """Occurrences of a 32-bit little-endian constant in .text."""
    sva, vs, rs, ro = TEXT
    pat = struct.pack('<I', value)
    res, i = [], DATA.find(pat, ro, ro + rs)
    while i >= 0:
        res.append(sva + i - ro)
        i = DATA.find(pat, i + 1, ro + rs)
    return res


def func_start(va):
    """Walk back to a likely prologue (preceded by CC/C3 padding)."""
    for a in range(va, va - 0x4000, -1):
        if read(a - 1, 1) in (b'\xcc', b'\xc3', b'\x90') and read(a, 1) in (b'\x55', b'\x83', b'\x53', b'\x56', b'\x57', b'\x81', b'\x8b', b'\x6a', b'\xa1'):
            if a % 16 == 0:
                return a
    return None


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dis':
        print('\n'.join(dis(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 40)))
    elif cmd == 'callers':
        for c in callers(int(sys.argv[2], 16)):
            print(hex(c), hex(func_start(c) or 0))
    elif cmd == 'refs':
        for c in imm_refs(int(sys.argv[2], 16)):
            print(hex(c), hex(func_start(c) or 0))
