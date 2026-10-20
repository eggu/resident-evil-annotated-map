# Annotated Map: Survivor's Notes — Resident Evil (1996)

**주석 달린 지도: 생존자의 메모** — 원작 Resident Evil PC판(GOG 일본어판 `Biohazard.exe` + [Classic REbirth 1.1.4](https://classicrebirth.com/index.php/re1cb-changelog/))의 지도에 방 이름, 잠긴 문과 필요한 열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자를 표시하는 비공식 REbirth 모드입니다. 한국어/영어를 지원합니다.

- 상태 화면 지도에는 아이콘만, **M**(패드 **RB**)으로 여는 전체 화면 지도에는 이름까지 표시합니다.
- 주운 아이템, 연 문, 푼 퍼즐은 지도에서 사라집니다. 아이템이 남은 방은 호박색으로 칠합니다.
- 잠긴 문의 열쇠는 아직 가지 않은 쪽 방에 표시합니다. 전체 화면 지도에는 현재 위치와 바라보는 방향을 화살표로 표시합니다.
- 크리스/질의 아이템 배치 차이를 반영합니다.

## 설치

1. [Releases](https://github.com/eggu/resident-evil-annotated-map/releases)에서 `RE1-Annotated-Map-<버전>.zip`을 받습니다. `Source code`는 설치 파일이 아닙니다.
2. 게임을 종료하고 ZIP의 내용을 `Biohazard.exe`가 있는 게임 폴더에 폴더 구조 그대로 복사합니다.
3. 게임 실행 → REbirth **MOD SELECTION**에서 `Annotated Map: Survivor's Notes`를 체크합니다.

제거: 게임 폴더의 `mod_annotated_map/`과 `RE1.AnnotatedMap.dll`을 지웁니다. EXE와 세이브는 수정하지 않습니다. 지원 대상이 아닌 `Biohazard.exe`(타임스탬프 `0x3642d468`이 아닌 경우)에서는 아무것도 패치하지 않습니다.

[한글 HD 번역 모드](https://github.com/eggu/resident-evil-korean-hd-translation)와 함께 사용할 수 있습니다.

## 단축키

| 키 | 동작 |
|---|---|
| M / 패드 RB | 전체 화면 지도 열기·닫기 (탐색 중, 조작 가능한 상태에서) |
| Esc / 취소 버튼 | 전체 화면 지도 닫기 |
| 앞/뒤 이동 | 층 선택 |
| 좌/우 이동 | 장소 선택 |
| 0 | 전체 표시 켜기/끄기 |
| 1 | 방 이름·타자기·아이템 상자 |
| 2 | 잠긴 문·열쇠 |
| 3 | 핵심 아이템 (+ 아이템이 남은 방 호박색) |
| 4 | 문서·지도 |
| 5 | 퍼즐 |
| 6 | 일반 아이템 |
| 7 | 전체 화면 지도 ↔ 상태창 지도 |
| 8 | 표시 범위: 방문한 방 → 공개된 방(층 지도 획득) → 모든 방 |
| 9 | 한국어 / English |

## 설정 (`mod_annotated_map/RE1.AnnotatedMap.ini`)

처음 실행할 때 만들어지며 표시 옵션을 저장합니다.

| 항목 | 기본값 | 설명 |
|---|---|---|
| `[Keys] OpenKey` | `M` | 키보드로 열기·닫기. 한 글자, `ESC`, `TAB`, `SPACE`, `F1`–`F12`, `0x4D` 같은 가상 키 코드, `NONE` |
| `[Keys] OpenPad` | `RB` | 패드로 열기·닫기(XInput). `A B X Y LB RB START BACK LS RS UP DOWN LEFT RIGHT`, `NONE` |
| `[Keys] CloseKey` | `ESC` | 키보드로 닫기 |
| `[Keys] CloseOnCancel` | `1` | 게임의 취소 버튼으로 닫기 |
| `[AnnotatedMap] RoomTint` | `1` | `0`이면 아이템이 남은 방 색칠 끄기 |
| `[AnnotatedMap] NameOpacity` | `70` | 이름 불투명도(10–100) |
| `[Calibration] OffsetX/OffsetY/Z` | | 상태창 지도 주석 위치·깊이 보정 |
| `[Calibration] ArrowRotation` | `0` | 캐릭터 화살표 방향 보정(도) |

## 빌드

저장소에는 게임 파일이 없습니다. 이미 추출한 데이터(`data/annotated.json`, `room_xform.json`, `map_rooms.json`)를 사용하므로 빌드에는 게임 폴더의 `Biohazard.exe`(네이티브 테스트)와 `jpn/Item_m2`의 지도 TIM만 필요합니다. 글꼴은 `fonts/`의 오픈 라이선스 글꼴(Pretendard, 나눔명조, Noto Serif)을 사용합니다.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export RE1_GAME_DIR="/path/to/Resident Evil"   # Biohazard.exe와 jpn/이 있는 GOG 일본어판 폴더
.venv/bin/python build.py --package           # 위키 → 에셋 → DLL → 네이티브 테스트 → dist/ ZIP
```

- 데이터를 다시 추출하려면 `--extract`를 붙입니다. 이때는 모든 `ROOM*.RDT`와 `refs/evilresource/pages/*.html`([evilresource.com/resident-evil](https://www.evilresource.com/resident-evil) 방 페이지)이 필요합니다. 참고 자료: [RE1-Mod-SDK](https://github.com/Gemini-Loboto3/RE1-Mod-SDK), [biorand/classic](https://github.com/biorand/classic), [biorand/biohazard-utils](https://github.com/biorand/biohazard-utils).
- 손으로 관리하는 데이터는 `data/curated.json`(퍼즐, 이벤트 아이템, 방 이름 보정)과 `data/items.json`(아이템 이름)입니다.
- `tests/test_native.py`는 실제 EXE와 빌드한 DLL을 Unicorn으로 실행해 패치, 플래그 판정, 지도 입력, 그리기 명령을 확인합니다. `tools/audit_fit.py`는 방별 월드→지도 변환을 점검합니다.
- GitHub Actions(`.github/workflows/package.yml`)는 `main`에 푸시할 때 암호화된 비공개 입력(EXE, 지도 TIM)을 풀어 같은 빌드와 테스트를 실행하고 배포 ZIP을 아티팩트로 올립니다.

조사 자료와 구현 근거는 [위키](docs/wiki/README.md)에 있습니다.

## 라이선스

소스는 [MIT License](LICENSE)입니다. 비공식 팬 모드이며 Capcom 및 Classic REbirth와 관련이 없습니다. 참고 자료와 글꼴 라이선스는 [NOTICE](NOTICE.md)에 있습니다.
