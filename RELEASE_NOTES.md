# Annotated Map: Survivor's Notes — 1.0.0

## 한국어

원작 Resident Evil PC판 지도에 한국어·영어 주석을 추가합니다.

- 방 이름, 잠긴 문과 열쇠, 핵심·일반 아이템, 문서·지도, 퍼즐, 타자기·아이템 상자를 표시합니다.
- M / 패드 RB로 전체 화면 지도를 열고, 숫자 9로 한국어·영어를 전환합니다.
- 수집·해결 상태와 크리스·질의 아이템 배치 차이를 반영합니다.
- 빌드 시 본문·영문 제목·한글 제목 글꼴을 각각 지정할 수 있습니다. 생략하면 포함된 오픈소스 글꼴을 사용합니다.
- 방 이름 연결선은 겹침 검사에서 제외하고, 외부 이름은 주변 여백이 넓은 위치부터 배치합니다.
- 저장소 README와 다음 패키지용 설치 안내를 한국어·영어로 제공합니다.

### 설치

GOG 일본어판 `Biohazard.exe`와 Classic REbirth 1.1.4가 필요합니다. 게임을 종료하고 배포 ZIP을 게임 폴더에 풀어 폴더 구조를 유지한 뒤, REbirth MOD SELECTION에서 `Annotated Map: Survivor's Notes`를 선택하세요. 설치·제거는 [README](README.md)를 참고하세요.

### 검증 상태

- 기본 글꼴 에셋 생성과 방 이름 배치 검사 통과: 한글·영문 배치 실패 0개.
- 글꼴 옵션 검사와 DLL 컴파일 통과.
- 영문 열쇠 이름·아이콘 겹침 1건이 남아 있습니다.

## English

Adds Korean and English annotations to the original Resident Evil PC map.

- Displays room names, locked doors and required keys, key and common items, documents and maps, puzzles, typewriters and item boxes.
- Open the full-screen map with M / controller RB and switch Korean / English with number key 9.
- Reflects collection and puzzle state, with Chris and Jill item placements.
- Supports separate build-time fonts for body text, the English title and the Korean title. Bundled open-source fonts are used when options are omitted.
- Leader lines are excluded from collision checks; external room labels prefer positions with more surrounding space.
- Repository READMEs and installation instructions for the next package are available in Korean and English.

### Installation

Requires the GOG Japanese `Biohazard.exe` and Classic REbirth 1.1.4. Close the game, extract the release ZIP into the game folder while preserving its directory structure, then enable `Annotated Map: Survivor's Notes` in REbirth MOD SELECTION. See the [README](README.en.md) for installation and removal details.

### Validation status

- Default-font asset generation and room-label placement checks passed: zero unplaced names in either language.
- Font option checks and DLL compilation passed.
- One English key-label/icon overlap remains.
