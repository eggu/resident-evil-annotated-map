# Resident Evil(1996) 지도 모드 위키

원작 RE1 PC(GOG 일본어판 + Classic REbirth 1.1.4)의 상태 화면 지도에 방 이름·잠긴 문·아이템·퍼즐을 덧그리기 위해 정리한 자료입니다. 표는 `tools/gen_wiki.py`가 `data/annotated.json`에서 생성합니다(손으로 고치지 말고 데이터/스크립트를 고친 뒤 `python build.py`).

| 문서 | 내용 |
|---|---|
| [01 원작 지도 동작](01-native-map.md) | 지도 TIM, 방=CLUT 블록, 방문 플래그, 상태 구조체, 그리기·텍스처 슬롯, SCD 플래그 그룹 |
| [02 데이터 추출과 검증](02-data-pipeline.md) | RDT/SCD 해석, 방 이름 대응, 월드→지도 변환 맞춤, 한계 |
| [03 방 목록](03-rooms.md) | 118개 지도 슬롯(한/영 이름, 페이지, 방문 비트) + 페이지별 미리보기 |
| [04 잠긴 문과 열쇠](04-locks-keys.md) | 20개 열쇠 문(해제 비트, 필요 아이템, 열쇠 위치) |
| [05 핵심 아이템](05-key-items.md) | 획득 플래그·캐릭터·조건부 여부·지도 좌표 |
| [06 퍼즐](06-puzzles.md) | evilresource 가이드 퍼즐 + 아이템 사용 지점 34곳(AOT 근거) |
| [07 문서와 지도](07-documents-maps.md) | 파일, 벽 지도 |
| [08 일반 아이템](08-common-items.md) | 탄약·회복·무기·잉크 리본 |
| [09 타자기·아이템 상자](09-save-points.md) | 세이브 지점 |
| [10 출처](10-sources.md) | 게임 파일, BioRand, RE1-Mod-SDK, evilresource |
| [12 아이템 검증](12-item-verification.md) | evilresource 대조로 지도에서 뺀 아이템과 이유 |

## 요약

- **맵 스테이지** 0 저택 1층(+재방문), 1 저택 2층·지하, 2 정원·지하 동굴, 3 기숙사, 4 연구소. RDT 폴더 Stage6/7은 저택 재방문이며 스테이지 0/1의 지도·플래그를 그대로 씁니다.
- **방문**: `Flg_7 0xC387A0[base[stage]+slot]` / **획득**: `0xC3876C[flag]` / **문 해제**: `0xC38744[LockId&0x3F]` (MSB 우선 비트).
- **캐릭터**: `Status_flg 0xC33090 & 0x800000` = 질(RDT 파일 끝 자리 1).
- 원작에는 월드→지도 투영이 없어서, 문 AOT ↔ 지도의 노란 문 표시를 맞춘 방별 변환으로 아이템 좌표를 계산했습니다(중앙 오차 ≈0.5px, 방 밖이면 방 안으로 이동).

- [지도 전용 화면 추가 가능성](11-dedicated-map-feasibility.md) — 2026-10-19 후보 구현 및 검증 경계
