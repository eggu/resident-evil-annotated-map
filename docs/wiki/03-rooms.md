# 방 목록과 지도 슬롯

키 `s-rr` = 맵 스테이지(0–4)-방 번호(16진). 저택 재방문(Stage6/7 폴더)은 스테이지 0/1과 같은 슬롯·플래그를 씁니다. 방문 비트는 `Flg_7 (0xC387A0)`의 비트 번호(MSB 우선)입니다. 이름은 evilresource.com 하이라이트 이미지를 게임 TIM 방 마스크에 겹쳐 자동 대응했고, 0-1D/0-1E/1-1D/2-11/2-12는 같은 방의 카메라별 분할 슬롯(exe 0x43ca60)입니다.

| 키 | 한국어 | English | TIM | 페이지 | 방문 비트 | 픽셀 |
|---|---|---|---|---|---|---|
| `0-00` | 저택 세이브 룸 | Mansion Save Room | MAP01.TIM | 0 | 0 | 44 |
| `0-01` | 서쪽 계단 | West Stairway 1F | MAP01.TIM | 0 | 1 | 291 |
| `0-02` | 빈 방 | Vacant Room | MAP01.TIM | 0 | 2 | 37 |
| `0-03` | 중앙 복도 | Central Corridor | MAP01.TIM | 0 | 3 | 183 |
| `0-04` | 다실 | Tea Room | MAP01.TIM | 0 | 4 | 155 |
| `0-05` | 식당 | Dining Room | MAP01.TIM | 0 | 5 | 465 |
| `0-06` | 중앙 홀 | Main Hall 1F | MAP01.TIM | 0 | 6 | 904 |
| `0-07` | 미술실 | Art Room | MAP01.TIM | 0 | 7 | 174 |
| `0-08` | L자 복도 | 'L' Passage | MAP01.TIM | 0 | 8 | 222 |
| `0-09` | 굽은 복도 | Winding Passage | MAP01.TIM | 0 | 9 | 120 |
| `0-0A` | 뒤쪽 복도 | Back Passage | MAP01.TIM | 0 | 10 | 101 |
| `0-0B` | 동쪽 계단 | East Stairway 1F | MAP01.TIM | 0 | 11 | 86 |
| `0-0C` | 온실 | Greenhouse | MAP01.TIM | 0 | 12 | 60 |
| `0-0D` | 호랑이 석상실 | Tiger Statue Room | MAP01.TIM | 0 | 13 | 20 |
| `0-0E` | 사육사 침실 | Keeper's Bedroom | MAP01.TIM | 0 | 14 | 81 |
| `0-0F` | 바 | Bar | MAP01.TIM | 0 | 15 | 182 |
| `0-10` | 승강기 계단 | Elevator Stairway | MAP01.TIM | 0 | 16 | 86 |
| `0-11` | 탈의실 | Dressing Room | MAP01.TIM | 0 | 17 | 149 |
| `0-12` | 옷장 | Wardrobe | MAP01.TIM | 0 | 18 | 121 |
| `0-13` | 욕실 | Bathroom | MAP01.TIM | 0 | 19 | 60 |
| `0-14` | 실외 보일러 | Outside Boiler | MAP01.TIM | 0 | 20 | 61 |
| `0-15` | 함정 방 | Trap Room | MAP01.TIM | 0 | 21 | 30 |
| `0-16` | 거실 | Living Room | MAP01.TIM | 0 | 22 | 102 |
| `0-17` | 대미술관 | Large Gallery | MAP01.TIM | 0 | 23 | 253 |
| `0-18` | 저택 창고 | Mansion Storeroom | MAP01.TIM | 0 | 24 | 31 |
| `0-19` | 정원 서재 | Courtyard Study | MAP01.TIM | 0 | 25 | 32 |
| `0-1A` | 지붕 통로 | Roofed Passage | MAP01.TIM | 0 | 26 | 89 |
| `0-1B` | 창고 | Store Room | MAP01.TIM | 0 | 27 | 81 |
| `0-1C` | 숨겨진 옷장 | Wardrobe Closet | MAP01.TIM | 0 | 28 | 57 |
| `0-1D` | 미술실 | Art Room | MAP01.TIM | 0 | 29 | 76 |
| `0-1E` | 바 | Bar | MAP01.TIM | 0 | 30 | 14 |
| `0-1F` | 고립된 통로 | Isolated Passage | MAP01.TIM | 0 | 31 | 48 |
| `1-01` | 서쪽 계단 | West Stairway 2F | MAP02.TIM | 1 | 33 | 264 |
| `1-02` | 식당 위층 | Dining Room 2F | MAP02.TIM | 1 | 34 | 237 |
| `1-03` | 중앙 홀 | Main Hall 2F | MAP02.TIM | 1 | 35 | 447 |
| `1-04` | C자 복도 | 'C' Passage | MAP02.TIM | 1 | 36 | 179 |
| `1-05` | 갑옷실 | Armor Room | MAP02.TIM | 1 | 37 | 237 |
| `1-06` | 작은 서재 | Small Library | MAP02.TIM | 1 | 38 | 103 |
| `1-07` | 동쪽 계단 | East Stairway 2F | MAP02.TIM | 1 | 39 | 167 |
| `1-08` | 사슴 방 | Deer Room | MAP02.TIM | 1 | 40 | 66 |
| `1-09` | 침실 | Bedroom | MAP02.TIM | 1 | 41 | 64 |
| `1-0A` | 서재 | Study | MAP02.TIM | 1 | 42 | 35 |
| `1-0B` | 강의실 입구 | Lesson Room Entry | MAP02.TIM | 1 | 43 | 85 |
| `1-0C` | 강의실 | Lesson Room | MAP02.TIM | 1 | 44 | 200 |
| `1-0D` | 기둥 복도 | Pillar Passage | MAP02.TIM | 1 | 45 | 95 |
| `1-0E` | 다락 입구 | Attic Entry | MAP02.TIM | 1 | 46 | 63 |
| `1-0F` | 작은 식당 | Small Dining Room | MAP02.TIM | 1 | 47 | 80 |
| `1-10` | 다락 | Attic | MAP02.TIM | 1 | 48 | 271 |
| `1-11` | 테라스 입구 | Terrace Entry | MAP02.TIM | 1 | 49 | 39 |
| `1-12` | 테라스 | Terrace | MAP02.TIM | 1 | 50 | 52 |
| `1-13` | 승강기 복도 | Elevator 2F | MAP02.TIM | 1 | 51 | 179 |
| `1-14` | 거친 통로 | Rough Passage | MAP02.TIM | 1 | 52 | 197 |
| `1-15` | 박제실 | Trophy Room | MAP02.TIM | 1 | 53 | 57 |
| `1-16` | 서재 | Large Library | MAP02.TIM | 1 | 54 | 192 |
| `1-17` | 개인 서재 | Private Library | MAP02.TIM | 1 | 55 | 96 |
| `1-18` | 헬기장 전망대 | Heliport Lookout | MAP02.TIM | 1 | 56 | 56 |
| `1-19` | 벽장 | Closet | MAP02.TIM | 1 | 57 | 30 |
| `1-1A` | 지하 통로 1 | Underground Passage 1 | MAP03.TIM | 2 | 58 | 365 |
| `1-1B` | 지하 통로 2 | Underground Passage 2 | MAP03.TIM | 2 | 59 | 511 |
| `1-1C` | 주방 | Kitchen | MAP03.TIM | 2 | 60 | 323 |
| `1-1D` | 작은 식당 | Small Dining Room | MAP02.TIM | 1 | 61 | 18 |
| `1-1E` | 승강기 계단 | Elevator Stairway B1 | MAP03.TIM | 2 | 62 | 115 |
| `2-00` | 중앙 정원 | Courtyard Garden | MAP04.TIM | 3 | 63 | 307 |
| `2-01` | 수문 | Water Gate | MAP04.TIM | 3 | 64 | 279 |
| `2-02` | 폭포 | Falls | MAP04.TIM | 3 | 65 | 460 |
| `2-04` | 기숙사 정문 | Guardhouse Gate | MAP04.TIM | 3 | 67 | 290 |
| `2-05` | 분수 | Fountain | MAP04.TIM | 3 | 68 | 405 |
| `2-06` | 지하 석상실 | Item Chamber | MAP05.TIM | 4 | 69 | 44 |
| `2-07` | 지하 입구 | Underground Entry | MAP05.TIM | 4 | 70 | 258 |
| `2-08` | 갈림길 | Branched Passage | MAP05.TIM | 4 | 71 | 308 |
| `2-09` | 발전기실 | Generator Room | MAP05.TIM | 4 | 72 | 233 |
| `2-0A` | 엔리코의 방 | Enrico Room | MAP05.TIM | 4 | 73 | 202 |
| `2-0B` | 바위 통로 1 | Boulder Passage 1 | MAP05.TIM | 4 | 74 | 157 |
| `2-0C` | 거미 방 | Black Tiger Room | MAP05.TIM | 4 | 75 | 237 |
| `2-0D` | 직선 통로 | Straight Passage | MAP05.TIM | 4 | 76 | 175 |
| `2-0E` | 지하 세이브 룸 | Underground Save Room | MAP05.TIM | 4 | 77 | 59 |
| `2-0F` | 바위 통로 2 | Boulder Passage 2 | MAP05.TIM | 4 | 78 | 290 |
| `2-11` | 바위 통로 1 | Boulder Passage 1 | MAP05.TIM | 4 | 80 | 102 |
| `2-12` | 바위 통로 2 | Boulder Passage 2 | MAP05.TIM | 4 | 81 | 24 |
| `3-00` | 기숙사 입구 | Guardhouse Entry | MAP0A.TIM | 5 | 82 | 409 |
| `3-01` | 001호실 | Room 001 | MAP0A.TIM | 5 | 83 | 162 |
| `3-02` | 001호 욕실 | Room 001 Bathroom | MAP0A.TIM | 5 | 84 | 131 |
| `3-03` | 기숙사 세이브 룸 | Guardhouse Save Room | MAP0A.TIM | 5 | 85 | 159 |
| `3-04` | 오락실 | Rec Room | MAP0A.TIM | 5 | 86 | 965 |
| `3-05` | 중앙 복도 | Central Corridor | MAP0A.TIM | 5 | 87 | 353 |
| `3-06` | 002호실 | Room 002 | MAP0A.TIM | 5 | 88 | 151 |
| `3-07` | 002호 욕실 | Room 002 Bathroom | MAP0A.TIM | 5 | 89 | 75 |
| `3-08` | 벌집 복도 | Beehive Passage | MAP0A.TIM | 5 | 90 | 490 |
| `3-09` | 약품 창고 | Drug Storeroom | MAP0A.TIM | 5 | 91 | 124 |
| `3-0A` | 003호실 | Room 003 | MAP0A.TIM | 5 | 92 | 151 |
| `3-0B` | 003호 욕실 | Room 003 Bathroom | MAP0A.TIM | 5 | 93 | 75 |
| `3-0C` | 식물 42 방 | Plant 42 Room | MAP0A.TIM | 5 | 94 | 600 |
| `3-0D` | 대형 수조 입구 | Water Tank Entry | MAP0B.TIM | 6 | 95 | 410 |
| `3-0E` | 대형 수조 | Water Tank | MAP0B.TIM | 6 | 96 | 1334 |
| `3-0F` | 회의실 | Meeting Room | MAP0B.TIM | 6 | 97 | 238 |
| `3-10` | 무기 창고 | Arms Storage | MAP0B.TIM | 6 | 98 | 84 |
| `3-11` | 제어실 | Control Room | MAP0B.TIM | 6 | 99 | 160 |
| `4-00` | 연구소 입구 | Laboratory Entry | MAP06.TIM | 7 | 100 | 409 |
| `4-01` | 비상 통로 | Emergency Tunnel | MAP06.TIM | 7 | 101 | 776 |
| `4-02` | 사다리 방 | Ladder Room | MAP07.TIM | 8 | 102 | 129 |
| `4-03` | 계단 | Stairway | MAP07.TIM | 8 | 103 | 328 |
| `4-04` | 영상 자료실 | Visual Data Room | MAP07.TIM | 8 | 104 | 242 |
| `4-05` | O자 통로 | 'O' Room | MAP08.TIM | 9 | 105 | 383 |
| `4-06` | 작은 실험실 | Small Lab | MAP08.TIM | 9 | 106 | 153 |
| `4-07` | 수술실 | Operating Room | MAP08.TIM | 9 | 107 | 98 |
| `4-08` | 개인 복도 | Private Corridor | MAP08.TIM | 9 | 108 | 54 |
| `4-09` | 개인실 | Private Room | MAP08.TIM | 9 | 109 | 102 |
| `4-0A` | X선실 | X-Ray Room | MAP08.TIM | 9 | 110 | 102 |
| `4-0B` | 감방 입구 | Cell Entry | MAP08.TIM | 9 | 111 | 101 |
| `4-0C` | 승강기 입구 | Elevator Entry | MAP08.TIM | 9 | 112 | 212 |
| `4-0E` | 연구소 세이브 룸 | Lab Save Room | MAP08.TIM | 9 | 114 | 72 |
| `4-0F` | 동력 미로 1 | Power Maze 1 | MAP08.TIM | 9 | 115 | 169 |
| `4-10` | 동력 미로 2 | Power Maze 2 | MAP08.TIM | 9 | 116 | 138 |
| `4-11` | 동력실 | Power Room | MAP08.TIM | 9 | 117 | 148 |
| `4-12` | 감방 | Cell | MAP08.TIM | 9 | 118 | 57 |
| `4-13` | 중앙 연구실 | Main Lab | MAP09.TIM | 10 | 119 | 857 |
| `4-14` | 중앙 연구실 입구 | Main Lab Entry | MAP09.TIM | 10 | 120 | 192 |
| `4-16` | 시체 안치실 | Morgue | MAP08.TIM | 9 | 122 | 100 |

## 페이지별 미리보기

미리보기 그림은 게임 원본 지도 그림을 포함하므로 저장소에 넣지 않습니다. `build.py`를 실행하면 `docs/wiki/img/`에 생성됩니다. 노랑 마름모=잠긴 문, 시안=핵심 아이템, 흰색=문서·지도, 회색 점=일반 아이템, 주황 마름모=퍼즐, 연두=타자기·상자. `*`=이벤트 생성이라 방 중심에 표시.

- 페이지 0 — `MAP01.TIM` (맵 스테이지 0): `img/page-00.png`
- 페이지 1 — `MAP02.TIM` (맵 스테이지 1): `img/page-01.png`
- 페이지 2 — `MAP03.TIM` (맵 스테이지 1): `img/page-02.png`
- 페이지 3 — `MAP04.TIM` (맵 스테이지 2): `img/page-03.png`
- 페이지 4 — `MAP05.TIM` (맵 스테이지 2): `img/page-04.png`
- 페이지 5 — `MAP0A.TIM` (맵 스테이지 3): `img/page-05.png`
- 페이지 6 — `MAP0B.TIM` (맵 스테이지 3): `img/page-06.png`
- 페이지 7 — `MAP06.TIM` (맵 스테이지 4): `img/page-07.png`
- 페이지 8 — `MAP07.TIM` (맵 스테이지 4): `img/page-08.png`
- 페이지 9 — `MAP08.TIM` (맵 스테이지 4): `img/page-09.png`
- 페이지 10 — `MAP09.TIM` (맵 스테이지 4): `img/page-10.png`
