# Annotated Map: Survivor's Notes — 1.2.0

## English

**What's new**

- **Story event markers (key `6`, off by default).** A purple `?` diamond (icon only) marks story scenes found in the game scripts and disappears once the scene has happened. Scenes the scripts cannot settle are not shown.
- **Enemy markers (key `8`).** Enemies placed in each room appear as an icon per kind and disappear once killed. Enemies of the mansion revisit are shown only while you are in the revisited mansion.
- **Zoom.** On the full-screen map, the game's confirm / examine key zooms 1x / 2x and the game's map directions pan the map. The map always opens at 1x.
- **HD-style icons** for items, keys, documents, puzzles, typewriters and item boxes on the full-screen map (`HdIcons=0` in the INI switches back to pixel icons). Puzzle markers now carry a `!`.
- **Icon size and opacity** can be changed in game, and **item names** can be turned on and off with `H` (off by default; `H` cycles all names, all except common items, off). Item names use their category's colour and sit next to their own icon.
- **Weapons are now key items (`3`).** Locked-door keys are shown **on the door**; set `KeySide=1` in the INI to show them in the room you have not visited yet, as before.
- **Solved puzzles disappear** from the map, per character: Mansion 2F Pillar Passage (serum), Mansion 2F Small Dining Room (candles), Mansion 1F Bar (passage statue), Guardhouse B1 Water Tank Entry (crate bridge), the dining-room emblem hollow, the fountain medal hollows, the Roofed Passage crest mount, the Water Gate crank, the elevator batteries at the Falls and the Emergency Tunnel, the three hex-crank sockets, Plant 42's roots, V-JOLT, the poison-gas vents, the lock computer, the power terminal and the elevator power. The Beehive Passage door-code marker now sits at the code panel beside the Drug Storeroom door and disappears once that door is open.
- **Category colours** can be changed in the INI `[Colors]` section (`#RRGGBB`). Common items now use a cool grey. Saving settings in game keeps this section and its comments.
- The legend is titled **Map Notes / 지도 메모**, shows icon size and opacity, can be folded with `~`, and is shared by both map views. Adjustment hints sit in a small dim group beside it.
- Room and item names are laid out again: room names sit in the middle of the room's shape, long names use two lines, and common items or enemies under a key item appear once that item is taken.
- `F12` writes a debug capture (`scripts/RE1.AnnotatedMap.capture.txt`) for bug reports.
- If REbirth's HD textures are off (`HDLoader=0` or `RetroMode=1`), the map shows a short English notice instead of unreadable text.

**Changed keys**

| Key | 1.1.2 | 1.2.0 |
|---|---|---|
| `6` | Common items | Events |
| `7` | – | Common items |
| `8` | Visibility scope | Enemies |
| `9` | Language | Visibility scope |
| `\` (₩) | – | Language |
| `- · +` | Name size | Name size |
| `[ · ]` | – | Name opacity |
| `Shift + - · +` | Name opacity | Icon size |
| `Shift + [ · ]` | – | Icon opacity |

New keys: `H` item names, `~` fold the legend, `F12` debug capture. `[Keys] Modifier=CTRL` replaces Shift with Ctrl.

**Upgrading**

Close the game and extract the ZIP over the old files. Keep your existing `scripts/RE1.AnnotatedMap.ini` (skip it when extracting, or back it up and restore it): your settings are kept, and the file gains the new entries and a `Version` key the first time you play. Settings are stored by category name, so nothing is lost by the renumbered keys. The ZIP now also contains `LICENSE` and `NOTICE.md`.

Known limitations: larger names and icons keep their anchors and may overlap; enemy markers show the placement at room load, not movement.

## 한국어

**새 기능**

- **스토리 이벤트 표식(키 `6`, 기본 꺼짐).** 게임 스크립트에서 찾은 스토리 장면을 보라색 `?` 마름모(아이콘만)로 표시하고, 장면이 일어나면 사라집니다. 스크립트만으로 확정하지 못한 장면은 표시하지 않습니다.
- **적 표식(키 `8`).** 방에 배치되는 적을 종류별 아이콘으로 표시하고, 쓰러뜨리면 사라집니다. 저택 재방문 때의 적은 재방문한 저택에 있을 때만 표시합니다.
- **확대.** 전체 화면 지도에서 게임의 결정(확인·조사) 키로 1배/2배 확대하고, 게임의 지도 방향 입력으로 이동합니다. 지도는 항상 1배로 열립니다.
- 전체 화면 지도의 아이템·열쇠·문서·퍼즐·타자기·아이템 상자에 **HD풍 아이콘**을 사용합니다(INI `HdIcons=0`이면 도트 아이콘). 퍼즐 표식에는 `!`가 들어갑니다.
- **아이콘 크기·불투명도**를 게임 안에서 바꿀 수 있고, **아이템 이름**은 `H`로 켜고 끕니다(기본 끔, 모두 → 일반 아이템 제외 → 끔 순환). 아이템 이름은 분류 색으로 자기 아이콘 옆에 표시됩니다.
- **무기를 핵심 아이템(`3`)으로 옮겼습니다.** 잠긴 문의 열쇠는 **문 위**에 표시합니다. INI `KeySide=1`이면 예전처럼 아직 가지 않은 쪽 방에 표시합니다.
- **푼 퍼즐이 지도에서 사라집니다**(캐릭터별 판정): 저택 2층 기둥 복도(혈청), 저택 2층 작은 식당(촛대), 저택 1층 바(비밀 통로 석상), 기숙사 지하 대형 수조 입구(상자 다리), 식당 엠블럼 홈, 분수 메달 홈, 지붕 통로 문장 받침대, 수문 크랭크, 폭포·비상 통로 엘리베이터 배터리, 육각 크랭크 3곳, 식물 42 뿌리, V-JOLT, 독가스 환기구, 잠금 컴퓨터, 전력 단말기, 엘리베이터 전원. 벌집 복도의 문 암호 표식은 약품 창고 문 옆 암호 패널 위치로 옮겼고, 그 문이 열리면 사라집니다.
- 분류별 **색**을 INI `[Colors]`에서 `#RRGGBB`로 바꿀 수 있습니다. 일반 아이템은 차가운 회색을 씁니다. 게임 안에서 저장해도 이 구역과 주석은 유지됩니다.
- 범례 제목이 **지도 메모 / Map Notes**로 바뀌고, 아이콘 크기·불투명도를 표시하며, `~`로 접을 수 있습니다. 두 지도 화면이 같은 범례를 씁니다. 조절 안내는 범례 옆의 작고 흐린 글씨입니다.
- 방 이름과 아이템 이름 배치를 다시 계산했습니다. 방 이름은 방 모양의 가운데에, 긴 이름은 두 줄로 표시하며, 핵심 아이템 아래에 가려진 일반 아이템·적은 그 아이템을 얻으면 나타납니다.
- `F12`로 버그 제보용 디버그 기록(`scripts/RE1.AnnotatedMap.capture.txt`)을 저장합니다.
- REbirth의 HD 텍스처가 꺼져 있으면(`HDLoader=0` 또는 `RetroMode=1`) 읽을 수 없는 글자 대신 짧은 영어 안내문을 표시합니다.

**바뀐 키**

| 키 | 1.1.2 | 1.2.0 |
|---|---|---|
| `6` | 일반 아이템 | 이벤트 |
| `7` | – | 일반 아이템 |
| `8` | 표시 범위 | 적 |
| `9` | 언어 | 표시 범위 |
| `\`(₩) | – | 언어 |
| `- · +` | 이름 크기 | 이름 크기 |
| `[ · ]` | – | 이름 불투명도 |
| `Shift + - · +` | 이름 불투명도 | 아이콘 크기 |
| `Shift + [ · ]` | – | 아이콘 불투명도 |

새 키: `H` 아이템 이름, `~` 범례 접기, `F12` 디버그 기록. `[Keys] Modifier=CTRL`로 Shift 대신 Ctrl을 쓸 수 있습니다.

**업그레이드**

게임을 종료하고 ZIP을 기존 파일 위에 풉니다. 기존 `scripts/RE1.AnnotatedMap.ini`는 건너뛰거나 백업 후 복원하세요. 설정은 그대로 유지되고, 처음 실행할 때 새 항목과 `Version` 키가 파일에 추가됩니다. 설정은 분류 이름으로 저장되므로 키 번호가 바뀌어도 값은 잃지 않습니다. ZIP에 `LICENSE`와 `NOTICE.md`가 함께 들어갑니다.

알려진 제한: 이름과 아이콘을 키우면 기존 위치를 유지해 겹칠 수 있습니다. 적 표식은 방에 들어갈 때의 배치 위치이며 움직임은 따라가지 않습니다.
