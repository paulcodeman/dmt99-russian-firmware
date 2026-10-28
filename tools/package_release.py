"""Package the verified patch, without redistributing the manufacturer image."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from common import ROOT, BUILD, ORIGINAL, sha

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=(ROOT/'VERSION').read_text().strip())
    args = parser.parse_args()
    version = args.version.removeprefix('v')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise SystemExit('Invalid release version')
    if version != (ROOT/'VERSION').read_text().strip():
        raise SystemExit('Tag version must match VERSION')
    manifest = json.loads((BUILD/'manifest.json').read_text(encoding='utf-8'))
    verification = json.loads((BUILD/'verification.json').read_text(encoding='utf-8'))
    if verification['candidate_sha256'] != manifest['candidate_sha256']:
        raise SystemExit('Verification does not belong to the current build')
    if sha((BUILD/'firmware.ips').read_bytes()) != manifest['patch_sha256']:
        raise SystemExit('Patch hash differs from verified manifest')
    dist = ROOT/'dist'
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dmt99-release-') as tmp:
        stage = Path(tmp)/f'DMT99-RU-EN-v{version}'
        stage.mkdir()
        for name in ['firmware.ips','manifest.json','verification.json','overlay.bin']:
            shutil.copy2(BUILD/name,stage/name)
        for name in ['make_firmware.py','ips.py']:
            shutil.copy2(ROOT/'tools'/name,stage/name)
        for name in ['NOTICE.md','LICENSE']:
            shutil.copy2(ROOT/name,stage/name)
        shutil.copy2(ROOT/'src/DejaVu-LICENSE.txt',stage/'DejaVu-LICENSE.txt')
        shutil.copy2(ROOT/'docs/RELEASE_README_RU.md',stage/'README_RU.md')
        shutil.copytree(BUILD/'previews',stage/'previews')
        # Exercise the exact end-user utility included in the release ZIP.
        output = Path(tmp)/'DMT99RU.BIN'
        subprocess.run([sys.executable,str(stage/'make_firmware.py'),'--original',str(ORIGINAL),'--output',str(output)],check=True)
        if output.read_bytes() != (BUILD/'DMT99RU.BIN').read_bytes():
            raise SystemExit('End-user patch utility does not reproduce the compiled image')
        archive = dist/(stage.name+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    z.write(path,stage.name+'/'+path.relative_to(stage).as_posix())
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise SystemExit('Release archive integrity check failed')
    shutil.copy2(BUILD/'firmware.ips',dist/f'DMT99-RU-EN-v{version}.ips')
    shutil.copy2(BUILD/'manifest.json',dist/f'DMT99-RU-EN-v{version}-manifest.json')
    files=sorted(p for p in dist.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (dist/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in files))
    print(f'Packaged verified release v{version}: {archive.name}')

if __name__ == '__main__':
    main()
