"""CI only: decrypt the private game inputs (Biohazard.exe, map TIMs) and copy the checksum-verified files to .ci-inputs/.
Local builds point RE1_GAME_DIR at their own game folder instead."""
import hashlib,json,os,subprocess,tarfile,tempfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/'.github/ci-inputs.json').read_text(encoding='utf-8'))
    archive=ROOT/'local/ci-build-inputs.tar.gz.enc'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['ciphertext_sha256']:
        raise ValueError('CI source archive checksum mismatch')
    key=os.environ.get('BUILD_INPUTS_KEY')
    if not key:
        raise ValueError('CI requires BUILD_INPUTS_KEY; local builds do not use this script')
    with tempfile.TemporaryDirectory(prefix='re1-map-ci-') as directory:
        work=Path(directory);plain=work/'inputs.tar.gz'
        subprocess.run(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000',
                        '-in',str(archive),'-out',str(plain),'-pass','env:BUILD_INPUTS_KEY'],check=True)
        with tarfile.open(plain) as source:
            seen=set()
            for member in source:
                path=PurePosixPath(member.name)
                if (not member.isfile() or path.is_absolute() or '..' in path.parts
                    or member.name not in manifest['files'] or member.name in seen):
                    raise ValueError('Unexpected CI input archive entry')
                seen.add(member.name);data=source.extractfile(member).read()
                expected=manifest['files'][member.name]
                if len(data)!=expected['size'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
                    raise ValueError(f'CI source file checksum mismatch: {member.name}')
                target=work/'verified'/path;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
        if seen!=set(manifest['files']):
            raise ValueError('CI source archive has missing files')
        destination=ROOT/'.ci-inputs'
        # Only validated, named files are copied; no archive extraction touches the repo.
        import shutil
        for name in seen:
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(work/'verified'/name,target)
    print(f'Prepared {len(seen)} verified CI source inputs')


if __name__=='__main__':main()
