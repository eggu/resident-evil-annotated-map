# Annotated Map: Survivor's Notes — 1.1.1

## 한국어

- **ASI 플러그인으로 배포 방식을 바꿨습니다.** `scripts/RE1.AnnotatedMap.asi`로 설치하며, REbirth MOD SELECTION에서 체크할 필요가 없습니다. Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함합니다. Classic REbirth는 계속 필요합니다.
- 기본 열기 키를 **Tab**, 패드 **BACK**(View/Create)으로 바꿨습니다. Classic REbirth는 기본으로 START에 키 설정 화면을 둡니다.
- 상태 화면 지도에서도 열기 키로 전체 화면 지도를 엽니다. 기존 `7` 키 전환은 없앴습니다.
- 상태 화면에서 연 전체 지도에서 앞/뒤·좌/우로 층과 장소를 바꿀 수 있습니다. 배경이 비치던 문제와 장소 전환 중 크래시를 고쳤습니다.
- 아래쪽 이동 화살표가 범례에 가려지지 않도록 범례 위로 옮겼습니다. 범례에 `[TAB]` 문구를 표시합니다.
- 기본값과 주석이 담긴 `scripts/RE1.AnnotatedMap.ini`를 포함합니다.

### 설치·업그레이드

게임 종료 후 ZIP을 `Biohazard.exe` 옆에 폴더 구조 그대로 풉니다. 1.1.0에서 업그레이드할 때는 `RE1.AnnotatedMap.dll`과 `mod_annotated_map/`을 지우고, 기존 설정을 유지하려면 `mod_annotated_map/RE1.AnnotatedMap.ini`를 `scripts/`로 옮기세요. [설치 안내](README.md).

전체 빌드, 원본 EXE 기반 네이티브 회귀, 패키지 구성 검사를 통과했습니다. Wine(macOS)에서 Classic REbirth 1.1.3 + 포함된 로더로 Tab 열기, 상태 화면 지도에서 열기, 층·장소 이동을 확인했습니다. 실제 패드 BACK 버튼과 Windows 실기 환경은 미확인입니다.

## English

- **Now distributed as an ASI plugin.** Installs as `scripts/RE1.AnnotatedMap.asi`; no REbirth MOD SELECTION step is needed. Ultimate ASI Loader v9.7.4 (MIT) is included as `dsound.dll`. Classic REbirth is still required.
- The default open key is now **Tab**, and controller **BACK** (View/Create). Classic REbirth uses START for its key settings screen by default.
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
