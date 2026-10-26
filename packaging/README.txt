Annotated Map: Survivor's Notes - Resident Evil (1996)
상세 지도: 생존자의 메모

지원: GOG 일본어판 Resident Evil(Biohazard.exe) + Classic REbirth 1.1.4 + Ultimate ASI Loader.
Classic REbirth는 별도로 설치해야 합니다. Ultimate ASI Loader v9.7.4(MIT)는 dsound.dll로 포함되어 있습니다.
지도 화면에 방 이름, 잠긴 문과 열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자를 표시합니다.

설치
1. 게임을 종료합니다.
2. ZIP의 내용을 Biohazard.exe가 있는 게임 폴더에 폴더 구조 그대로 복사합니다.
   (dsound.dll, scripts/RE1.AnnotatedMap.asi, scripts/RE1.AnnotatedMap.ini)
   REuncap 등으로 Ultimate ASI Loader가 이미 dsound.dll로 설치되어 있으면 dsound.dll은 건너뛰어도 됩니다.
   ASI 로더가 아닌 다른 dsound.dll(예: DSOAL)이 있으면 덮어쓰지 말고, 포함된 dsound.dll을 winmm.dll 이름으로 복사하세요.
3. 게임을 실행합니다. REbirth MOD SELECTION에서 체크할 필요가 없습니다.
1.1.0에서 업그레이드: 게임 폴더의 RE1.AnnotatedMap.dll과 mod_annotated_map 폴더를 지웁니다.
기존 설정을 유지하려면 mod_annotated_map/RE1.AnnotatedMap.ini를 scripts/로 옮겨 기본 INI 대신 사용하세요.

사용
- 탐색 중이나 상태창 지도에서 Tab 또는 패드 START(Menu/Options): 전체 화면 지도 열기. Tab, Esc, 취소 버튼: 닫기.
- 지도에서 앞/뒤 이동: 층 선택, 좌/우 이동: 장소 선택.
- 숫자 키: 0 전체 표시, 1 방 이름·저장, 2 문·열쇠, 3 핵심 아이템, 4 문서·지도, 5 퍼즐, 6 일반 아이템,
  8 표시 범위(방문한 방 → 공개된 방 → 모든 방), 9 한국어 / English.
- 이름 크기: - / = (+), 불투명도: Shift + 위 키. 숫자패드 -/+도 지원합니다.
- 기본값: 영어, 이름100%, 불투명도70%, 방 표시만 켬.
- 설정은 scripts/RE1.AnnotatedMap.ini에 저장됩니다([Keys]에서 열기·닫기 키 변경).

패드 지도 버튼 변경 (기존 1.1.0에서도 지원)
게임 종료 후 위 INI의 [Keys]에서 OpenPad=START를 사용하지 않는 버튼으로 바꿉니다.
예: OpenPad=LS (왼쪽 스틱 클릭). [Keys]나 OpenPad가 없으면 추가하세요.
지원: A B X Y LB RB START BACK LS RS UP DOWN LEFT RIGHT, NONE.
LT/RT 트리거와 버튼 조합은 지원하지 않습니다. 게임 자체의 패드 설정과 별개입니다.
OpenPad=NONE이면 패드 지도 단축키를 끕니다. 키보드 OpenKey=TAB은 계속 사용할 수 있습니다.
키보드 키는 OpenKey=TAB, 추가 닫기 키는 CloseKey=ESC에서 바꿉니다.
파일의 주석을 참고하고 저장한 뒤 게임을 재실행하세요.

제거
scripts/RE1.AnnotatedMap.asi와 .ini(.log)를 지웁니다. 다른 ASI 모드가 없으면 dsound.dll도 지웁니다. EXE와 세이브는 수정하지 않습니다.

비공식 팬 모드입니다. Capcom과 관련이 없으며 게임 파일을 포함하지 않습니다.
https://github.com/eggu/resident-evil-annotated-map

================================================================
English
================================================================

Supported: GOG Japanese Resident Evil (Biohazard.exe) + Classic REbirth 1.1.4 + Ultimate ASI Loader.
Classic REbirth must be installed separately. Ultimate ASI Loader v9.7.4 (MIT) is included as dsound.dll.
Shows room names, locked doors and required keys, key items, documents and maps,
puzzles, common items, typewriters and item boxes on the map.

Installation
1. Close the game.
2. Copy the ZIP contents into the folder containing Biohazard.exe, preserving
   the directory structure (dsound.dll, scripts/RE1.AnnotatedMap.asi and scripts/RE1.AnnotatedMap.ini).
   If Ultimate ASI Loader is already installed as dsound.dll (e.g. by REuncap), you can skip dsound.dll.
   If you have a different dsound.dll (e.g. DSOAL), do not overwrite it: copy the included one as winmm.dll.
3. Launch the game. Nothing needs to be enabled in REbirth MOD SELECTION.
Upgrading from 1.1.0: delete RE1.AnnotatedMap.dll and the mod_annotated_map folder from the game folder.
To keep your settings, move mod_annotated_map/RE1.AnnotatedMap.ini into scripts/ instead of the default INI.

Controls
- While exploring or on the status-screen map, press Tab or controller START (Menu/Options) to open the full-screen map.
  Press Tab, START, Esc or the cancel button to close it.
- On the map: move forward/backward to select a floor; left/right to select an area.
- Number keys: 0 all annotations, 1 room names/typewriters/item boxes, 2 doors/keys,
  3 key items, 4 documents/maps, 5 puzzles, 6 common items,
  8 visibility (visited/revealed/all rooms),
  9 Korean/English.
- Name size: - / = (+); opacity: Shift + those keys. Numpad -/+ is supported.
- Defaults: English, size 100%, opacity 70%, Rooms only.
- Settings are saved in scripts/RE1.AnnotatedMap.ini.
  Configure opening and closing controls under [Keys].

Changing the controller map button (also supported in the existing 1.1.0 release)
Close the game and change OpenPad=START under [Keys] in the INI to an unused button,
e.g. OpenPad=LS for left-stick click. Add [Keys]/OpenPad if they are missing.
Supported: A B X Y LB RB START BACK LS RS UP DOWN LEFT RIGHT, or NONE.
LT/RT triggers and button combinations are not supported. This setting is
independent of the game's controller bindings. OpenPad=NONE disables the pad
shortcut; OpenKey=TAB still works on the keyboard. Change OpenKey for the keyboard
toggle or CloseKey=ESC for the additional close key. Save and restart the game.
The included INI has default values and comments explaining each setting.

Uninstall
Delete scripts/RE1.AnnotatedMap.asi and its .ini/.log. Also delete dsound.dll if no other ASI mod uses it.
The EXE and save files are not modified.

Unofficial fan mod, unaffiliated with Capcom. No game files are included.
https://github.com/eggu/resident-evil-annotated-map
