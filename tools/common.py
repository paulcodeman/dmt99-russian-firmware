"""Build configuration shared by offline tools; never accesses a multimeter."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache'
BUILD = ROOT / 'build'
UPSTREAM = Path(os.environ.get('DMT99_UPSTREAM', str(CACHE / 'upstream')))
ORIGINAL = Path(os.environ.get('DMT99_ORIGINAL', str(CACHE / 'DMT-99_V2.4_20240306.BIN')))
ORIGIN = 0x6400
APPEND = 0x27400
LIMIT = 0x30000
EXPECTED = '4befdf6b58e063f03901f190000d790e60d20d0a23e5eeb2b6f6840f1830e98e'
ORIGINAL_URL = 'https://cdn.shopify.com/s/files/1/0694/8310/2426/files/DMT-99_V2.4_20240306.BIN?v=1756206088'
HOOKS = {
    0x678c: ('hook_image', 'original_image'),
    0x8e46: ('hook_string', 'original_string'),
    0x83d6: ('hook_ascii_char', 'original_ascii_char'),
    0x18ad2: ('hook_compact', 'original_compact'),
    0x19366: ('hook_large', 'original_large'),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(args):
    return subprocess.check_output(args, text=True, encoding='utf-8', errors='strict')

def tool(name, *args):
    prefix = os.environ.get('DMT99_CROSS', 'riscv64-unknown-elf-')
    if os.name == 'nt':
        prefix = os.environ.get('DMT99_CROSS', '/tmp/dmt99-toolchain-20261028/root/usr/bin/riscv64-unknown-elf-')
        return run(['wsl', '-d', 'Ubuntu', '--', prefix + name, *map(str, args)])
    if not shutil.which(prefix + name):
        raise SystemExit(f'Missing {prefix + name}; install the RISC-V toolchain or set DMT99_CROSS')
    return run([prefix + name, *map(str, args)])

def compiler_path(path):
    path = Path(path).resolve()
    if os.name == 'nt':
        return '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)

def font_path():
    for path in [os.environ.get('DMT99_FONT', ''), '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 r'\\wsl.localhost\Ubuntu\usr\share\fonts\truetype\dejavu\DejaVuSans.ttf']:
        if path and Path(path).is_file():
            return path
    raise SystemExit('Install fonts-dejavu-core or set DMT99_FONT for software previews')

def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
