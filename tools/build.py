"""Build a UI-only patch for one exact manufacturer V2.4 image. No device IO."""
import struct
from common import ROOT, BUILD, ORIGINAL, EXPECTED, ORIGINAL_URL, ORIGIN, APPEND, LIMIT, HOOKS, sha, tool, compiler_path, write_json
from ips import encode, apply

def jal(pc, target, rd=0):
    delta = target - pc
    if delta % 2 or not -(1 << 20) <= delta < (1 << 20):
        raise ValueError('Invalid JAL range/alignment')
    delta &= 0x1fffff
    return struct.pack('<I', ((delta>>20)&1)<<31 | ((delta>>1)&1023)<<21 | ((delta>>11)&1)<<20 | ((delta>>12)&255)<<12 | rd<<7 | 0x6f)

def jal_target(pc, word):
    delta = ((word>>31)&1)<<20 | ((word>>12)&255)<<12 | ((word>>20)&1)<<11 | ((word>>21)&1023)<<1
    return pc + delta - ((1<<21) if delta & (1<<20) else 0)

def main():
    original = ORIGINAL.read_bytes()
    if len(original) != 135096 or sha(original) != EXPECTED:
        raise SystemExit('This build only accepts the hash-locked original V2.4 BIN')
    BUILD.mkdir(exist_ok=True)
    (BUILD/'overlay.ld').write_text('SECTIONS { . = 0x27400; .overlay : { *(.text*) *(.rodata*) } /DISCARD/ : { *(.comment) *(.riscv.attributes) *(.eh_frame*) } .forbidden : { *(.data*) *(.bss*) *(.sdata*) *(.sbss*) } } ASSERT(SIZEOF(.forbidden)==0,"overlay must not allocate RAM");\n')
    asm = ['.section .text.trampolines,"ax",@progbits', '.option norvc', '.option norelax']
    trampolines = {name: addr for addr, (_, name) in HOOKS.items()}
    trampolines.update({'original_glyph12':0x8a5a, 'original_glyph16':0x8b5c, 'original_glyph24':0x8c64, 'original_glyph32':0x8d6c})
    for name, addr in trampolines.items():
        word = struct.unpack_from('<I', original, addr-ORIGIN)[0]
        if word & 127 != 0x6f or (word >> 7) & 31 != 5:
            raise SystemExit(f'Unexpected stock prologue at {addr:#x}')
        target = jal_target(addr, word)
        asm += ['.global '+name, name+':', f'  lui t1,%hi({target})', f'  addi t1,t1,%lo({target})',
                '  jalr t0,t1,0', f'  lui t1,%hi({addr+4})', f'  addi t1,t1,%lo({addr+4})', '  jr t1']
    (BUILD/'trampolines.S').write_text('\n'.join(asm)+'\n')
    args = ['-march=rv32im','-mabi=ilp32','-Os','-ffreestanding','-fno-builtin','-fno-stack-protector',
            '-fno-pic','-fno-pie','-msmall-data-limit=0','-mno-relax','-nostdlib','-Wall','-Wextra','-Werror',
            '-fstack-usage','-Wl,--no-relax','-T',compiler_path(BUILD/'overlay.ld'),
            compiler_path(ROOT/'src/overlay.c'),compiler_path(BUILD/'trampolines.S'),'-o',compiler_path(BUILD/'overlay.elf')]
    tool('gcc', *args)
    tool('objcopy','-O','binary',compiler_path(BUILD/'overlay.elf'),compiler_path(BUILD/'overlay.bin'))
    (BUILD/'overlay.disasm').write_text(tool('objdump','-d',compiler_path(BUILD/'overlay.elf')))
    symbols = {}
    for row in tool('nm','-n',compiler_path(BUILD/'overlay.elf')).splitlines():
        parts = row.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0],16)
    overlay = (BUILD/'overlay.bin').read_bytes()
    if APPEND + len(overlay) > LIMIT:
        raise SystemExit('Overlay exceeds the conservative application Flash bound')
    image = bytearray(original)
    image.extend(b'\xff' * (APPEND-ORIGIN-len(image)))
    image.extend(overlay)
    edits = []
    for addr,(hook,_) in HOOKS.items():
        offset = addr-ORIGIN
        before = bytes(image[offset:offset+4])
        after = jal(addr,symbols[hook])
        image[offset:offset+4] = after
        edits.append({'address':hex(addr),'offset':offset,'before':before.hex(),'after':after.hex(),'hook':hook,'target':hex(symbols[hook])})
    old,new = b'DMT-99 V2.4',b'DMT 2.4RU  '
    version_offset = original.index(old)
    image[version_offset:version_offset+len(old)] = new
    patch = encode(original,image)
    if apply(original,patch) != image:
        raise SystemExit('IPS round-trip mismatch')
    (BUILD/'firmware.ips').write_bytes(patch)
    (BUILD/'DMT99RU.BIN').write_bytes(image)
    manifest = {'schema':1,'version':(ROOT/'VERSION').read_text().strip(),
                'original_url':ORIGINAL_URL,'original_sha256':EXPECTED,'original_bytes':len(original),
                'candidate_sha256':sha(image),'candidate_bytes':len(image),'patch_sha256':sha(patch),
                'size':len(image),'append_address':hex(APPEND),'append_bytes':len(overlay),
                'patches':edits,'version_edit':{'offset':version_offset,'before':old.decode(),'after':new.decode()},
                'symbols':symbols,'compiler':tool('gcc','--version').splitlines()[0],
                'status':'EXPERIMENTAL — NOT HARDWARE VALIDATED','hardware_validated':False,
                'external_flash_writes':False,'device_access':False}
    write_json(BUILD/'manifest.json',manifest)
    print(f'Built {len(image)} bytes; SHA-256 {sha(image)}')

if __name__ == '__main__':
    main()
