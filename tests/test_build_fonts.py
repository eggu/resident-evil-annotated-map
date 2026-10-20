"""Check build font arguments without generating assets or requiring game files."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
help_result = subprocess.run([sys.executable, str(ROOT / 'build.py'), '--help'], capture_output=True, text=True)
assert help_result.returncode == 0, help_result.stderr
for option in ('--font', '--title-font-en', '--title-font-ko'):
    assert option in help_result.stdout
    result = subprocess.run([sys.executable, str(ROOT / 'build.py'), option, str(ROOT / 'fonts/missing.ttf')], capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    assert 'Font file not found:' in result.stderr
print('Build font option checks passed')

# Exercise the driver with subprocesses intercepted: verify absolute paths reach the asset generator.
import runpy
from unittest.mock import patch
calls = []
font = ROOT / 'fonts/Pretendard-Medium.otf'
with patch.object(sys, 'argv', ['build.py', '--font', str(font)]), patch('subprocess.run', side_effect=lambda cmd, **kwargs: calls.append(cmd)):
    runpy.run_path(str(ROOT / 'build.py'), run_name='__main__')
assets = next(cmd for cmd in calls if any(str(arg).endswith('/tools/gen_assets.py') for arg in cmd))
assert assets[-2:] == ['--font', str(font.resolve())], assets
print('Custom font forwarding passed')
