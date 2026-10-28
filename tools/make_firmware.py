#!/usr/bin/env python3
"""Create DMT99RU.BIN from the official image + verified release patch.

Standard-library only; no compiler required. Does not copy to a device.
"""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
from ips import apply

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, help='Optional official V2.4 BIN; otherwise downloaded from FNIRSI')
    parser.add_argument('--output', type=Path, default=Path('DMT99RU.BIN'))
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    patch = (folder/'firmware.ips').read_bytes()
    if digest(patch) != manifest['patch_sha256']:
        raise SystemExit('Release patch SHA-256 mismatch')
    if args.original:
        original = args.original.read_bytes()
    else:
        url = manifest['original_url']
        if not url.startswith('https://cdn.shopify.com/s/files/1/0694/8310/2426/files/'):
            raise SystemExit('Unexpected manufacturer download URL')
        request = urllib.request.Request(url, headers={'User-Agent':'dmt99-russian-firmware'})
        with urllib.request.urlopen(request, timeout=60) as response:
            original = response.read()
    if len(original) != manifest['original_bytes'] or digest(original) != manifest['original_sha256']:
        raise SystemExit('Wrong manufacturer image — no output was written')
    image = apply(original,patch)
    if len(image) != manifest['candidate_bytes'] or digest(image) != manifest['candidate_sha256']:
        raise SystemExit('Result verification failed — no output was written')
    if args.output.exists():
        if digest(args.output.read_bytes()) == manifest['candidate_sha256']:
            print(f'Already verified: {args.output}')
            return
        raise SystemExit(f'Refusing to overwrite an existing different file: {args.output}')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(image)
    print(f'Created {args.output} ({len(image)} bytes)')
    print(f'SHA-256: {digest(image)}')
    print('Experimental firmware. Hardware startup and measurement accuracy are not validated.')
    print('No multimeter was accessed. The original manufacturer image can be restored through a working bootloader.')

if __name__ == '__main__':
    main()
