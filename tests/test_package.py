"""Check the release layout and bundled defaults without rebuilding the DLL."""
import configparser
import hashlib
import runpy
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
zip_type = zipfile.ZipFile
with tempfile.TemporaryDirectory() as tmp:
    archive = Path(tmp) / 'package.zip'
    with patch.object(sys, 'argv', ['build.py', '--package']), \
         patch('subprocess.run'), \
         patch('zipfile.ZipFile', side_effect=lambda *args, **kwargs: zip_type(archive, *args[1:], **kwargs)):
        runpy.run_path(str(ROOT / 'build.py'), run_name='__main__')
    with zip_type(archive) as z:
        assert z.testzip() is None
        assert sorted(z.namelist()) == ['RE1-Annotated-Map-README.txt', 'dsound.dll', 'scripts/RE1.AnnotatedMap.asi',
                                        'scripts/RE1.AnnotatedMap.ini', 'scripts/UltimateASILoader-LICENSE.txt']
        # unmodified Ultimate ASI Loader v9.7.4 x86 (Ultimate-ASI-Loader-NoPDB.zip dinput8.dll)
        assert hashlib.sha256(z.read('dsound.dll')).hexdigest() == \
            'ec2f4824eca58dd40f425756a4a7cec77b8e381f21d11d7c846ec4b339b617ab'
        assert b'MIT License' in z.read('scripts/UltimateASILoader-LICENSE.txt')
        bundled = z.read('scripts/RE1.AnnotatedMap.ini')
        assert bundled == (ROOT / 'packaging/RE1.AnnotatedMap.ini').read_bytes()
        assert z.read('scripts/RE1.AnnotatedMap.asi') == (ROOT / 'mod_annotated_map/RE1.AnnotatedMap.dll').read_bytes()
        config = configparser.ConfigParser()
        config.read_string(bundled.decode('ascii'))
        assert dict(config['Keys']) == dict(openkey='TAB', openpad='START', closekey='ESC', closeoncancel='1')
        assert dict(config['AnnotatedMap']) == dict(all='1', rooms='1', locks='0', keyitems='0', documents='0',
            puzzles='0', commonitems='0', language='en', scope='1', namesize='100', nameopacity='70', roomtint='1')
        assert dict(config['Calibration']) == dict(offsetx='0', offsety='0', z='16', arrowrotation='0')
print('ASI release layout, module identity and commented default INI passed')
