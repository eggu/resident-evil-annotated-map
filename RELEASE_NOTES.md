# Annotated Map: Survivor's Notes — 1.3.0

## English

**What's new**

- **SD mode.** With Classic REbirth's HD textures off (`HDLoader=0` or missing, or `RetroMode=1` in the game's `config.ini`) the map no longer shows a notice: it is drawn at the original resolution.
  - 9×9 pixel markers: puzzles (amber `!`), events (purple `?`), key items (cyan circle), herbs, ammo, spray, ink ribbons, files, maps, typewriters, item boxes; enemies are small red crosses. Every locked door shows a padlock whose colour and pattern belong to its key. On the status-screen map the markers are smaller (7×7).
  - Room names in a pixel font, fixed on the map: on the zoomed map a name sits inside its room when it fits, otherwise outside on a thin leader line. Names scroll with the map and are cut at the screen edge. On Mansion 1F and 2F, which have many rooms, names appear only on the zoomed map.
  - A compact legend and 1x floor/area and player arrows. Name and icon size, opacity and item names do not apply in SD mode.
- **New INI key `DisplayMode`** (`Auto`, `HD`, `SD`): `Auto` chooses SD when REbirth's HD textures are off and HD otherwise, once at game start. Restart the game after changing REbirth's HD setting.
- HD mode is unchanged.

**Upgrading**

Close the game and extract the ZIP over the old files. Keep your existing `scripts/RE1.AnnotatedMap.ini` (skip it when extracting, or back it up and restore it): your settings are kept, and the file gains `DisplayMode` the first time a setting is saved.

Requires Classic REbirth 1.1.3 or later. Known limitations: see the README.

## 한국어

**새 기능**

- **SD 모드.** Classic REbirth의 HD 텍스처가 꺼져 있으면(게임 `config.ini`에서 `HDLoader=0`이거나 없음, 또는 `RetroMode=1`) 안내문 대신 원래 해상도로 지도를 그립니다.
  - 9×9 픽셀 표식: 퍼즐(주황 `!`), 이벤트(보라 `?`), 핵심 아이템(하늘색 원), 허브, 탄약, 스프레이, 잉크 리본, 문서, 지도, 타자기, 아이템 상자, 적은 작은 빨간 십자. 잠긴 문은 열쇠마다 색과 무늬가 다른 자물쇠로 표시합니다. 상태 화면 지도의 표식은 더 작습니다(7×7).
  - 픽셀 글꼴 방 이름은 지도에 고정됩니다. 확대 지도에서는 방 안에 들어가면 방 안에, 아니면 방 밖에 가는 지시선으로 연결하고, 지도와 함께 움직이며 화면 가장자리에서 잘립니다. 방이 많은 저택 1층·2층은 확대했을 때만 방 이름을 표시합니다.
  - 간결한 범례와 1배 층·구역 화살표, 플레이어 화살표. 이름·아이콘 크기, 불투명도, 아이템 이름은 SD 모드에서 적용되지 않습니다.
- **INI 키 `DisplayMode` 추가**(`Auto`, `HD`, `SD`): `Auto`는 REbirth HD 텍스처가 꺼져 있으면 SD, 아니면 HD를 게임 시작 때 한 번 선택합니다. REbirth의 HD 설정을 바꾼 뒤에는 게임을 다시 시작하세요.
- HD 모드는 그대로입니다.

**업그레이드**

게임을 종료하고 ZIP을 기존 파일 위에 풉니다. 기존 `scripts/RE1.AnnotatedMap.ini`는 건너뛰거나 백업 후 복원하세요. 설정은 그대로 유지되고, 설정을 처음 저장할 때 `DisplayMode`가 파일에 추가됩니다.

Classic REbirth 1.1.3 이상이 필요합니다. 알려진 제한은 README를 참고하세요.
