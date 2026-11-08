# Annotated Map: Survivor's Notes — Unreleased (test candidate 18)

## 한국어

- **숫자 키 번호가 바뀌었습니다.** `0` 전체, `1` 방 이름, `2` 잠긴 문, `3` 핵심 아이템, `4` 문서·지도, `5` 퍼즐, `6` 이벤트(새로 추가), `7` 일반 아이템, `8` 적, `9` 표시 범위. 언어 전환은 `9`에서 `\`(₩) 키로 옮겼고, 범례에는 `[H]` 아래에 `[\] 언어: 한국어`로 표시합니다. 저장된 설정은 분류 이름으로 저장되어 값이 그대로 유지되며, 설정 파일 버전만 5로 올라갑니다.
- **이벤트(스포일러) 표식을 추가했습니다(키 `6`, 기본 꺼짐).** 보라색 `?` 마름모(이름 없이 아이콘만). 게임 스크립트에서 찾은 스토리 장면만 표시하고, 장면이 일어나면 사라집니다. 보스는 기존 적 표식을 그대로 쓰며, 스크립트만으로 확정하지 못한 장면은 표시하지 않습니다.
- **퍼즐 표식에 `!`를 넣었습니다.** 주황색 마름모 안의 `!`입니다(도트 아이콘).
- **이미 푼 퍼즐이 계속 표시되던 문제를 고쳤습니다.** 저택 2층 기둥 복도(혈청), 저택 2층 작은 식당(촛대), 저택 1층 바(비밀 통로 석상), 기숙사 지하 대형 수조 입구(상자 다리), 그리고 같은 종류의 식당 엠블럼 홈·분수 메달 홈. 크리스와 질은 스크립트가 쓰는 플래그가 달라 캐릭터별로 판정합니다.
- 퍼즐 11개도 풀면 사라집니다: 지붕 통로 문장 받침대(문장 4개), 수문 크랭크, 폭포·비상 통로 엘리베이터 배터리, 육각 크랭크 3곳, 식물 42 뿌리, V-JOLT 조합, 독가스 환기구, 잠금 컴퓨터, 전력 단말기, 엘리베이터 전원. 헬기장 신호탄과 벌집 복도 문 암호는 게임 데이터에 완료 기록이 없어 계속 표시됩니다.
- 기숙사 1층 벌집 복도의 문 암호 표식을 약품 창고 문 옆 암호 패널 위치로 고쳤습니다.
- 아이콘 크기를 키우면(150%, 200%) 이름이 자기 아이콘에 가려지던 문제를 고쳤습니다. 이름이 아이콘 크기에 맞춰 함께 밀려납니다.
- 일반 아이템 기본색을 차가운 회색(`#B8BCC4`)으로 바꿨고, 꺼진 범례 줄은 더 짙은 회색(`#6A6A6A`)입니다.
- 분류별 색을 INI `[Colors]`에서 `#RRGGBB`로 바꿀 수 있습니다. 게임 안에서 저장해도 이 구역과 주석은 유지됩니다.

- **적 표식(키 `7`)을 추가했습니다.** 방에 배치되는 적을 종류별 아이콘(RE1 HD 지도 모드와 같은 그림)으로 표시하고, 쓰러뜨리면 사라집니다. 저택 재방문 때의 적은 재방문한 저택에 있을 때만 표시합니다.
- **무기를 핵심 아이템(`3`)으로 옮겼습니다.**
- 잠긴 문의 열쇠를 **문 위**에 표시합니다. INI `KeySide=1`이면 예전처럼 아직 가지 않은 쪽 방에 표시합니다.
- **크기·불투명도 키를 다른 지도 모드와 같게 바꿨습니다.** `- · +` 이름 크기, `[ · ]` 이름 불투명도, `Shift + - · +` 아이콘 크기, `Shift + [ · ]` 아이콘 불투명도. 1.1.2까지의 `Shift + - · +`(이름 불투명도)는 이제 아이콘 크기입니다. 저장된 값은 그대로 유지됩니다.
- 새 키: `H` 아이템 이름 켜기/끄기(기본 끔), `~` 범례 접기, `F12` 디버그 기록. 일반 아이템에도 이름을 표시합니다(수량은 표시하지 않음).
- 범례 제목을 다른 지도 모드와 같은 **지도 메모 / Map Notes**로 바꾸고, 아이콘 크기·불투명도 값과 키 안내를 표시하며, 키 표기를 `- · +`, `Shift + - · +`처럼 바꿨습니다.
- 아이템 이름이 범례의 분류 색과 같은 색으로 표시됩니다(예: 일반 아이템은 `[6]`과 같은 주황, 문서는 분홍). 이름은 항상 자기 아이콘에 붙어 표시됩니다.
- 아이콘에 쓰는 보조 키를 INI `[Keys] Modifier`(`SHIFT`/`CTRL`)로 바꿀 수 있습니다.
- 방 이름과 아이템 이름 배치를 다시 계산했습니다. 방 이름은 방 모양의 가운데에, 긴 이름은 두 줄로, 핵심 아이템 아래에 가려진 일반 아이템·적은 그 아이템을 얻으면 나타납니다.
- 설정 파일에 `Version` 키를 둡니다. 예전 INI는 값은 그대로 두고 새 항목만 추가합니다. 설정 저장과 키 입력을 더 안전하게 처리합니다.

빌드와 원본 EXE 기반 네이티브 회귀, 설정·패키지 검사를 통과했습니다. 실제 게임 화면에서는 아직 확인하지 않았습니다.

## English

- **The number keys were renumbered.** `0` all, `1` rooms, `2` locks, `3` key items, `4` files and maps, `5` puzzles, `6` events (new), `7` common items, `8` enemies, `9` scope. The language switch moved from `9` to the `\` (₩) key and the legend shows `[\] LANGUAGE: ENGLISH` under `[H]`. Saved settings are stored by category name, so every value is kept; only the settings version becomes 5.
- **Event (spoiler) markers (key `6`, off by default).** A purple `?` diamond (icon only, no name). Only story scenes found in the game scripts are shown, and each disappears once it has happened. Bosses keep their enemy markers; scenes the scripts alone cannot settle are not shown.
- **Puzzle markers now carry a `!`** (orange diamond, pixel icon).
- **Solved puzzles no longer stay on the map.** Mansion 2F Pillar Passage (Serum), Mansion 2F Small Dining Room (Candles), Mansion 1F Bar (passage statue), Guardhouse B1 Water Tank Entry (crate bridge), plus the same kind of fault in the Dining Room emblem hollow and the fountain medal hollows. Chris and Jill scripts use different flags, so each character is checked separately.
- Eleven more puzzles now disappear once solved: the Roofed Passage crest mount (all four crests), the Water Gate crank, the elevator batteries at the Falls and the Emergency Tunnel, the three hex-crank sockets, Plant 42's roots, mixing V-JOLT, the poison-gas vents, the lock computer, the power terminal and the elevator power. The heliport flare and the Beehive Passage door code stay shown: the game keeps no completion record for them.
- The Guardhouse 1F Beehive Passage door-code marker now sits at the code panel beside the Drug Storeroom door.
- Names are no longer covered by their own icon at IconSize 150 % / 200 %: they move out with the icon.
- Common items default to a cool grey (`#B8BCC4`); disabled legend rows are a darker grey (`#6A6A6A`).
- Category colours can be set in the INI `[Colors]` as `#RRGGBB`. Saving settings in game keeps the section and its comments.

- **Enemy markers (key `7`).** Enemies placed in a room appear as an icon per kind (the same art as the RE1 HD map mod) and disappear once killed. Mansion-revisit enemies are shown only while you are in the revisited mansion.
- **Weapons are now key items (`3`).**
- Locked-door keys are shown **on the door**. Set `KeySide=1` in the INI to show them in the room not visited yet, as before.
- **Size and opacity keys now match the other map mods.** `- · +` name size, `[ · ]` name opacity, `Shift + - · +` icon size, `Shift + [ · ]` icon opacity. `Shift + - · +`, which changed name opacity up to 1.1.2, now changes icon size. Saved values are kept.
- New keys: `H` item names on/off (off by default), `~` fold the legend, `F12` debug capture. Common items now have names too (no quantities).
- The legend title is now **Map Notes / 지도 메모**, as in the other map mods; it shows icon size and opacity, and key hints are written as `- · +` and `Shift + - · +`.
- Item names use their category's legend colour (e.g. common items in the same orange as `[6]`, files in pink), and always sit next to their own icon.
- The icon modifier can be changed with `[Keys] Modifier` (`SHIFT`/`CTRL`) in the INI.
- Room and item names are laid out again: room names sit in the middle of the room's shape, long names use two lines, and common items or enemies under a key item appear once that item is taken.
- The settings file has a `Version` key. Older INIs keep their values and only gain the new entries. Saving settings and reading keys are more robust.

Passed the build, original-EXE native regression and settings/package checks. Not yet checked in the running game.

# Annotated Map: Survivor's Notes — 1.1.2

## 한국어

- 패드 지도 기본 버튼을 **BACK**에서 **START**(Menu/Options)로 바꿨습니다. Classic REbirth 기본 패드 배치는 BACK으로 설정 화면을 열어서 1.1.1 기본값과 겹쳤습니다.
- 1.1.1 문서의 "Classic REbirth는 기본으로 START에 키 설정 화면을 둔다"는 설명은 틀렸기에 고쳤습니다.
- 1.1.1에서 업그레이드할 때 기존 `scripts/RE1.AnnotatedMap.ini`를 유지하면 `OpenPad=BACK`이 남습니다. `[Keys]`의 `OpenPad=START`로 바꾸거나 포함된 INI로 덮어쓰세요.

전체 빌드, 원본 EXE 기반 네이티브 회귀, 패키지 구성 검사를 통과했습니다. 실제 패드 START 버튼과 Windows 실기 환경은 미확인입니다.

## English

- The default controller map button is now **START** (Menu/Options) instead of **BACK**. Classic REbirth's default controller layout opens its settings screen with BACK, which clashed with the 1.1.1 default.
- Corrects the 1.1.1 documentation, which wrongly said Classic REbirth uses START for its key settings screen by default.
- When upgrading from 1.1.1 and keeping your existing `scripts/RE1.AnnotatedMap.ini`, it still contains `OpenPad=BACK`. Change it to `OpenPad=START` under `[Keys]`, or overwrite it with the included INI.

Passed the full build, original-EXE native regression and package layout checks. A physical controller START button and native Windows remain unverified.

# Annotated Map: Survivor's Notes — 1.1.1

## 한국어

- **ASI 플러그인으로 배포 방식을 바꿨습니다.** `scripts/RE1.AnnotatedMap.asi`로 설치하며, REbirth MOD SELECTION에서 체크할 필요가 없습니다. Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함합니다. Classic REbirth는 계속 필요합니다.
- 기본 열기 키를 **Tab**, 패드 **BACK**(View/Create)으로 바꿨습니다.
- 상태 화면 지도에서도 열기 키로 전체 화면 지도를 엽니다. 기존 `7` 키 전환은 없앴습니다.
- 상태 화면에서 연 전체 지도에서 앞/뒤·좌/우로 층과 장소를 바꿀 수 있습니다. 배경이 비치던 문제와 장소 전환 중 크래시를 고쳤습니다.
- 아래쪽 이동 화살표가 범례에 가려지지 않도록 범례 위로 옮겼습니다. 범례에 `[TAB]` 문구를 표시합니다.
- 기본값과 주석이 담긴 `scripts/RE1.AnnotatedMap.ini`를 포함합니다.

### 설치·업그레이드

게임 종료 후 ZIP을 `Biohazard.exe` 옆에 폴더 구조 그대로 풉니다. 1.1.0에서 업그레이드할 때는 `RE1.AnnotatedMap.dll`과 `mod_annotated_map/`을 지우고, 기존 설정을 유지하려면 `mod_annotated_map/RE1.AnnotatedMap.ini`를 `scripts/`로 옮기세요. [설치 안내](README.md).

전체 빌드, 원본 EXE 기반 네이티브 회귀, 패키지 구성 검사를 통과했습니다. Wine(macOS)에서 Classic REbirth 1.1.3 + 포함된 로더로 Tab 열기, 상태 화면 지도에서 열기, 층·장소 이동을 확인했습니다. 실제 패드 BACK 버튼과 Windows 실기 환경은 미확인입니다.

## English

- **Now distributed as an ASI plugin.** Installs as `scripts/RE1.AnnotatedMap.asi`; no REbirth MOD SELECTION step is needed. Ultimate ASI Loader v9.7.4 (MIT) is included as `dsound.dll`. Classic REbirth is still required.
- The default open key is now **Tab**, and controller **BACK** (View/Create).
- The open key also opens the full-screen map from the status-screen map. The old `7` toggle was removed.
- The full-screen map opened from the status screen now changes floor and area with forward/back and left/right. Fixes the status screen showing through and a crash while changing areas.
- The down navigation arrow moved above the legend so it is no longer hidden. The legend shows `[TAB]`.
- Includes `scripts/RE1.AnnotatedMap.ini` with commented defaults.

### Installation and upgrade

Close the game and extract the ZIP beside `Biohazard.exe`, preserving its folders. When upgrading from 1.1.0, delete `RE1.AnnotatedMap.dll` and `mod_annotated_map/`; to keep your settings, move `mod_annotated_map/RE1.AnnotatedMap.ini` into `scripts/`. [Installation guide](README.en.md).

Passed the full build, original-EXE native regression and package layout checks. Verified on Wine (macOS) with Classic REbirth 1.1.3 and the bundled loader: Tab opening, opening from the status-screen map, and floor/area navigation. A physical controller BACK button and native Windows remain unverified.

# Annotated Map: Survivor's Notes — 1.1.0

## 한국어

- 작은 지도에도 전체 지도와 같은 범례 문구·켜짐/꺼짐·보기·범위·현재 언어를 표시합니다. HUD 아래 빈 영역에 배치했습니다.
- 범례를 Pretendard Medium, 4배 기준 본문20px·제목22px·테두리3px로 키우고 RE3 기준 색상으로 맞췄습니다. RE1의 기존 4bpp TIM 및 REbirth 1.1.4 경로를 유지하며 범례 전용 팔레트를 사용합니다.
- `- / = (+)` 또는 숫자패드 `-/+`: 이름 크기50~150%, 10%씩. `Shift`와 함께 누르면 불투명도10~100%, 10%씩 조절합니다. 현재 값을 범례에 표시하고 INI에 저장합니다.
- 새 설정의 기본값은 영어, 이름100%, 불투명도70%, 방 표시만 켬입니다. 기존 INI는 유지합니다. `All`은 방 표시를 위한 전체 스위치로 켜집니다.
- Mansion2F Study·Closet 등 바깥에 충분히 배치된 이름을 불필요하게 줄바꿈하던 조건을 수정했습니다.
- 기존 글꼴 옵션과 연결선을 이름보다 먼저 그리는1.0.1 수정사항을 유지했습니다.

### 설치·검증

게임 종료 후 ZIP을 `Biohazard.exe` 옆에 폴더 구조 그대로 풉니다. GOG 일본어판 및 Classic REbirth 1.1.4가 필요합니다. [설치 안내](README.md).

전체 빌드와 원본 EXE 기반 네이티브 회귀, 키/상하한/설정 저장·재로드, 이름 크기·알파 및 범례 배치 검사를 수행했습니다. 한글·영어 방 이름 배치 실패0개입니다. 실제 재시작 게임의 새 HUD/물리 키/GPU 알파/장시간 사용은 미확인입니다. 확대된 이름은 기존 위치를 유지해 겹칠 수 있으며, 기존 영문 열쇠 이름·아이콘 겹침1건이 남아 있습니다.

## English

- The status-screen map now shows the same full legend wording and states as the full-screen map, in the empty band below the HUD.
- Uses Pretendard Medium with body 20px, title 22px and outline 3px at the 4x reference scale, with RE3-matched legend colours. Keeps RE1's 4bpp TIM / REbirth 1.1.4 route and isolates the legend palette.
- `- / = (+)` or numpad `-/+` changes name size 50–150% in 10% steps. Add `Shift` for opacity 10–100%. Current values appear in the legend and persist in the INI.
- New defaults: English, size 100%, opacity 70%, Rooms on and other categories off. All remains on as the master switch. Existing INI values take precedence.
- Stops unnecessary wrapping of successfully placed outside names, including Mansion2F Study and Closet.
- Retains 1.0.1's configurable build fonts and leader-lines-before-labels fix.

### Installation and validation

Close the game and extract the ZIP beside `Biohazard.exe`, preserving its folders. Requires the GOG Japanese game and Classic REbirth 1.1.4. [Installation guide](README.en.md).

Validated the full build, original-EXE native regression, key/clamp/settings persistence, name size/alpha and legend layout. Zero unplaced room names in either language. Restarted-game HUD, physical keyboard, GPU alpha and long-session behavior remain unverified. Enlarged names keep fixed anchors and may overlap; one existing English key-label/icon overlap remains.

- Full map: the game's confirm/examine key (config.ini Key_Def / controller bindings) toggles 1x/2x zoom; native map directions pan smoothly while zoomed (offset only, no recompose). Names/icons scale to about 1.43x; zoom persists in the INI.
- 전체 지도: 게임의 결정(확인·조사) 키(config.ini Key_Def·패드 설정)로 1배/2배 확대, 확대 중 기존 지도 방향 입력으로 부드럽게 이동(오프셋만 이동, 재합성 없음). 이름·아이콘 약 1.43배, INI에 확대 상태 저장.
- [H] item names now cycle three states: all, all except common items, off (INI `ItemNames` 0 off / 1 all / 2 all but common, like the RE1 HD / RE2 / RE3 mods; the old 0/1 is kept). HD item icons are 20 % larger on the 1x full map and 50 % larger when zoomed (times IconSize); the Lockpick has its own icon.
- [H] 아이템 이름이 모두 → 일반 제외 → 끔 3단계로 순환(INI `ItemNames` 0 끔 / 1 모두 / 2 일반 제외, RE1 HD·RE2·RE3 모드와 같은 값, 이전 0/1은 그대로). HD 아이템 아이콘은 전체 지도 1배에서 20%, 확대에서 50% 더 크게(IconSize 곱), 락픽 전용 아이콘.
- Full map: HD-style icons (RE1 HD icon set) for items, keys, documents, maps, puzzles, typewriters and item boxes; the status-screen map keeps the pixel icons. Items without HD art yet keep the pixel icon. INI `HdIcons=0` turns it off.
- 전체 지도: 아이템·열쇠·문서·지도·퍼즐·타자기·아이템 상자에 HD풍 아이콘(RE1 HD 아이콘 세트) 사용. 상태 화면 지도는 도트 아이콘 유지. 아직 HD 그림이 없는 항목은 도트 아이콘 유지. INI `HdIcons=0`으로 끔.
- Zoomed pan can go a quarter of the viewport past every map edge, so edge rooms and names can be brought toward the centre.
- 확대 이동이 지도 가장자리를 뷰포트의 1/4만큼 넘어갈 수 있어, 가장자리의 방·이름을 가운데로 가져올 수 있음.
- The map always opens at 1x (zoom and pan reset on every open; no INI Zoom). The folded legend hint reads `[~] Map Notes` / `[~] 지도 메모` and sits at the bottom-left of the screen on its own black box.
- 지도는 항상 1배로 열림(열 때마다 확대·이동 초기화, INI Zoom 제거). 접힌 범례 안내는 `[~] 지도 메모`로 화면 왼쪽 아래 검은 상자 위에 표시.
- Zoom viewport now spans the full map area (legend shown: to its top edge, folded with [~]: to the screen bottom), pan bounds follow, and names/icons cut by a window edge are hidden whole with their marker.
- 확대 화면이 지도 영역 전체를 사용(범례 표시 시 범례 윗선까지, [~]로 접으면 화면 아래까지), 이동 범위도 이에 맞추고, 가장자리에 걸치는 이름·아이콘은 표식째로 숨김.
- Opening the map no longer stalls: texture uploads are spread over frames (`UploadBudget`, default 12 per frame).
- 지도를 열 때 멈칫하지 않도록 텍스처 업로드를 여러 프레임에 나눔(`UploadBudget`, 기본 프레임당 12).
- The adjustment hints are their own smaller, dimmer group beside the legend; common items are soft lavender #B4A7D6.
- 조절 안내를 범례와 분리해 작고 흐린 그룹으로 두고, 일반 아이템은 연보라 #B4A7D6.
- With REbirth HD textures off (HDLoader=0 / RetroMode=1) the map shows an English notice instead of unreadable text.
- REbirth HD 텍스처가 꺼져 있으면(HDLoader=0 / RetroMode=1) 읽을 수 없는 글자 대신 영어 안내문을 표시.
