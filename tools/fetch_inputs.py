"""Fetch hash-locked manufacturer input and research fixtures into ignored cache."""
from pathlib import Path
import argparse
import json
import urllib.request
import time
from common import CACHE, ROOT, ORIGINAL, ORIGINAL_URL, EXPECTED, sha

def download(url, dest, expected):
    if dest.exists():
        if sha(dest.read_bytes()) != expected:
            raise SystemExit(f'Existing input has wrong SHA-256: {dest.name}')
        return
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'dmt99-russian-firmware/0.1'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2)
    if sha(data) != expected:
        raise SystemExit(f'Download checksum mismatch: {dest.name}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + '.partial')
    tmp.write_bytes(data)
    tmp.replace(dest)
    print(f'Verified {dest.name}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-only', action='store_true')
    args = parser.parse_args()
    download(ORIGINAL_URL, ORIGINAL, EXPECTED)
    if args.original_only:
        return
    lock = json.loads((ROOT / 'inputs.lock.json').read_text(encoding='utf-8'))
    base = 'https://raw.githubusercontent.com/' + lock['repository'] + '/' + lock['commit'] + '/'
    for item in lock['files']:
        download(base + item['path'], CACHE / 'upstream' / item['path'], item['sha256'])

if __name__ == '__main__':
    main()
