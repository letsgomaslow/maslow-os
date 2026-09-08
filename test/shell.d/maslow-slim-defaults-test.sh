#!/bin/bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/base-test.sh"
require_command python3
python3 - "$ROOT" <<'PY'
import pathlib,sys,tempfile,subprocess,os
root=pathlib.Path(sys.argv[1])
packages=set((root/'install/omarchy-base.packages').read_text().splitlines())
assert not packages & {'kdenlive','obs-studio','moonlight-qt'}
assert {'docker','docker-compose','git','lazydocker'} <= packages
seeds=list((root/'applications').glob('*.desktop'))
assert all('Exec=omarchy-launch-webapp' not in p.read_text() and 'Exec=omarchy-webapp-handler' not in p.read_text() for p in seeds)
with tempfile.TemporaryDirectory() as temp:
 home=pathlib.Path(temp)/'home'; apps=home/'.local/share/applications'; apps.mkdir(parents=True)
 existing=apps/'My Web App.desktop'; existing.write_text('[Desktop Entry]\nName=My Web App\nExec=omarchy-launch-webapp https://example.org\n')
 old=existing.read_bytes()
 mockroot=pathlib.Path(temp)/'runtime'; mockroot.mkdir(); (mockroot/'applications').symlink_to(root/'applications')
 mockbin=pathlib.Path(temp)/'bin'; mockbin.mkdir()
 for name,content in {'omarchy-cmd-present':'exit 1','update-desktop-database':'exit 0'}.items():
  p=mockbin/name;p.write_text('#!/bin/bash\n'+content+'\n');p.chmod(0o755)
 env=dict(os.environ,HOME=str(home),OMARCHY_PATH=str(mockroot),PATH=str(mockbin)+':'+os.environ['PATH'])
 for _ in range(2): subprocess.run(['bash',str(root/'bin/omarchy-refresh-applications')],env=env,check=True)
 assert existing.read_bytes()==old
 assert {p.name for p in apps.glob('*.desktop')}=={p.name for p in seeds}|{existing.name}
print('ok - lean provisioning preserves existing webapps, repeats without reseeding, and retains infrastructure')
PY
