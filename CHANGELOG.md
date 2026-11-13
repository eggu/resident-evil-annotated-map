# Changelog

## 1.3.1 - 2026-11-13

English
- `DisplayMode=Auto` now uses HD mode only with Classic REbirth installed, `HDLoader=1`, and `RetroMode` and `LowResEnable` off; every other case, including no Classic REbirth, is SD (the mod no longer refuses to start without it).

한국어
- `DisplayMode=Auto`는 Classic REbirth가 설치되어 있고 `HDLoader=1`, `RetroMode`·`LowResEnable`이 꺼져 있을 때만 HD 모드이며, 그 밖의 모든 경우(Classic REbirth가 없을 때 포함)는 SD 모드입니다. Classic REbirth가 없어도 모드가 시작됩니다.

## 1.3.0 - 2026-11-13

English
- SD mode: with Classic REbirth's HD textures off (`HDLoader=0` or missing, or `RetroMode=1`) the map is drawn at the original resolution with 9x9 pixel markers, padlocks per key, pixel-font room names on leader lines and a compact legend, instead of the old notice. New INI key `DisplayMode` (`Auto`, `HD`, `SD`). Markers on the status-screen map are smaller (7x7).

한국어
- SD 모드: Classic REbirth의 HD 텍스처가 꺼져 있으면(`HDLoader=0`이거나 없음, 또는 `RetroMode=1`) 안내문 대신 원래 해상도로 9x9 픽셀 표식, 열쇠별 자물쇠, 지시선으로 연결한 픽셀 글꼴 방 이름, 간결한 범례를 표시합니다. INI 키 `DisplayMode`(`Auto`, `HD`, `SD`)를 추가했습니다. 상태 화면 지도의 표식은 더 작게(7x7) 표시합니다.

## 1.2.0

English
- Story event markers (key `6`, off by default) and enemy markers (key `8`); both disappear once the scene has happened or the enemy is dead.
- Zoom on the full-screen map with the game's confirm / examine key; HD-style icons; icon size and opacity; item names on `H`; weapons are key items; locked-door keys sit on the door (`KeySide=1` restores the old placement).
- Solved puzzles disappear from the map, per character; the Beehive Passage door-code marker was moved to its panel.
- Category colours in the INI `[Colors]` section; legend titled Map Notes, foldable with `~`; room and item names laid out again; `F12` debug capture.
- Keys changed: `6` events, `7` common items, `8` enemies, `9` visibility scope, `\` language, `[ · ]` name opacity, `Shift + - · +` icon size, `Shift + [ · ]` icon opacity. Saved settings are kept. The ZIP now includes `LICENSE` and `NOTICE.md`.

한국어
- 스토리 이벤트 표식(키 `6`, 기본 꺼짐)과 적 표식(키 `8`)을 추가했습니다. 장면이 일어나거나 적을 쓰러뜨리면 사라집니다.
- 전체 화면 지도에서 게임의 결정(확인·조사) 키로 확대, HD풍 아이콘, 아이콘 크기·불투명도, `H`로 아이템 이름, 무기를 핵심 아이템으로 이동, 잠긴 문의 열쇠를 문 위에 표시(`KeySide=1`이면 예전 배치).
- 푼 퍼즐이 캐릭터별로 지도에서 사라집니다. 벌집 복도 문 암호 표식을 암호 패널 위치로 옮겼습니다.
- INI `[Colors]`로 분류별 색 변경, 범례 제목 "지도 메모"와 `~` 접기, 방·아이템 이름 배치 재계산, `F12` 디버그 기록.
- 키 변경: `6` 이벤트, `7` 일반 아이템, `8` 적, `9` 표시 범위, `\` 언어, `[ · ]` 이름 불투명도, `Shift + - · +` 아이콘 크기, `Shift + [ · ]` 아이콘 불투명도. 저장된 설정은 유지됩니다. ZIP에 `LICENSE`와 `NOTICE.md`를 포함합니다.

## 1.1.2 - 2026-10-26

English
- The default controller map button is now START (Menu/Options) instead of BACK, which Classic REbirth uses for its settings screen.
- When upgrading from 1.1.1 and keeping your INI, change `OpenPad=BACK` to `OpenPad=START` under `[Keys]`.

한국어
- 패드 지도 기본 버튼을 BACK에서 START(Menu/Options)로 바꿨습니다. Classic REbirth는 BACK으로 설정 화면을 엽니다.
- 1.1.1에서 업그레이드하며 기존 INI를 유지했다면 `[Keys]`의 `OpenPad=BACK`을 `OpenPad=START`로 바꾸세요.

## 1.1.1 - 2026-10-26

English
- Distributed as an ASI plugin: `scripts/RE1.AnnotatedMap.asi` with Ultimate ASI Loader v9.7.4 as `dsound.dll`; no REbirth MOD SELECTION step. Classic REbirth is still required.
- The default open key is Tab (controller BACK); the open key also opens the full-screen map from the status-screen map and the old `7` toggle was removed.
- The full-screen map opened from the status screen changes floor and area with the movement keys; fixed the status screen showing through and a crash while changing areas.
- The down arrow moved above the legend; the legend shows `[TAB]`. Includes a commented default `scripts/RE1.AnnotatedMap.ini`.
- Upgrading from 1.1.0: delete `RE1.AnnotatedMap.dll` and `mod_annotated_map/`; move your INI into `scripts/` to keep your settings.

한국어
- ASI 플러그인으로 배포 방식을 바꿨습니다. `scripts/RE1.AnnotatedMap.asi`와 `dsound.dll`로 포함된 Ultimate ASI Loader v9.7.4로 설치하며 REbirth MOD SELECTION 설정은 필요 없습니다. Classic REbirth는 계속 필요합니다.
- 기본 열기 키가 Tab(패드 BACK)로 바뀌었고, 상태 화면 지도에서도 열기 키로 전체 화면 지도를 엽니다. 기존 `7` 키 전환은 없앴습니다.
- 상태 화면에서 연 전체 지도에서 이동 키로 층·장소를 바꿀 수 있습니다. 배경이 비치던 문제와 장소 전환 중 크래시를 고쳤습니다.
- 아래쪽 화살표를 범례 위로 옮기고 범례에 `[TAB]`을 표시합니다. 기본값과 주석이 담긴 `scripts/RE1.AnnotatedMap.ini`를 포함합니다.
- 1.1.0에서 업그레이드: `RE1.AnnotatedMap.dll`과 `mod_annotated_map/`을 지우고, 설정을 유지하려면 INI를 `scripts/`로 옮기세요.

## 1.1.0 - 2026-10-25

English
- The status-screen map shows the same full legend as the full-screen map, in the empty band below the HUD.
- Larger Pretendard Medium legend with colours matched to the RE3 map mod.
- Name size (`- · +`, 50–150%) and opacity (`Shift` + `- · +`, 10–100%) adjustable in game and saved to the INI.
- New defaults: English, size 100%, opacity 70%, Rooms on, other categories off. Existing INI values are kept.
- Fixed unnecessary wrapping of room names such as Mansion 2F Study and Closet.

한국어
- 상태 화면 지도에도 전체 화면 지도와 같은 범례를 HUD 아래 빈 영역에 표시합니다.
- 범례를 Pretendard Medium으로 키우고 RE3 지도 모드와 색상을 맞췄습니다.
- 이름 크기(`- · +`, 50–150%)와 불투명도(`Shift` + `- · +`, 10–100%)를 게임 안에서 조절하고 INI에 저장합니다.
- 새 기본값: 영어, 크기 100%, 불투명도 70%, 방 표시만 켬. 기존 INI 값은 유지됩니다.
- 저택 2층 서재·벽장 등 방 이름이 불필요하게 줄바꿈되던 문제를 고쳤습니다.

## 1.0.1 - 2026-10-20

English
- Leader lines are drawn before labels so they no longer cover text.
- Body, English title and Korean title fonts can be set separately at build time.

한국어
- 연결선을 이름보다 먼저 그려 글자를 덮지 않도록 고쳤습니다.
- 빌드할 때 본문·영문 제목·한글 제목 글꼴을 각각 지정할 수 있습니다.

## 1.0.0 - 2026-10-20

English
- First release. Korean and English room names, locked doors and required keys, key and common items, documents and maps, puzzles, typewriters and item boxes on the original Resident Evil PC map.
- Open the full-screen map with M (controller RB); switch Korean / English with `9`.
- Collection and puzzle progress and the Chris / Jill item differences are reflected.

한국어
- 첫 릴리스입니다. 원작 Resident Evil PC판 지도에 한국어·영어 방 이름, 잠긴 문과 열쇠, 핵심·일반 아이템, 문서·지도, 퍼즐, 타자기·아이템 상자를 표시합니다.
- M(패드 RB)으로 전체 화면 지도를 열고 `9`로 한국어·영어를 전환합니다.
- 수집·해결 상태와 크리스·질의 아이템 배치 차이를 반영합니다.
