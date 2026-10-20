# 잠긴 문과 열쇠

문 AOT(`door_aot_set`, 26바이트)의 `LockId` 바이트: bit7=잠금 가능, 하위 6비트=해제 플래그 번호(`Flg_2 0xC38744`), `LockType`=필요 아이템(0=잠금 없음, 0xFE=반대쪽에서 잠김, 0xFF=이벤트 잠금). 판정 코드 exe `0x455b40..0x455c8b`. 검 열쇠(51) 문은 질이 `Flg_0` 비트 0x7C(락픽 입수) 이후 락픽으로 엽니다.

| 해제 비트 | 필요 아이템 | 문 위치 → 목적지 | 열쇠 위치 | 비고 |
|---|---|---|---|---|
| 4 | 갑옷 열쇠 (Armor Key) | 굽은 복도 (Winding Passage) → `0-14` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 5 | 갑옷 열쇠 (Armor Key) | 중앙 홀 (Main Hall 1F) → `0-11` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 6 | 검 열쇠 (Sword Key) | 다실 (Tea Room) → `0-0F`<br>바 (Bar) → `0-04` | 저택 세이브 룸 (Mansion Save Room) (플래그 22, 크리스) | 질은 락픽(Flg_0[0x7C] 이후) |
| 7 | 방패 열쇠 (Shield Key) | 다락 입구 (Attic Entry) → `1-10` | 식당 (Dining Room) (플래그 33, 공통) |  |
| 9 | 검 열쇠 (Sword Key) | 미술실 (Art Room) → `0-08` | 저택 세이브 룸 (Mansion Save Room) (플래그 22, 크리스) | 질은 락픽(Flg_0[0x7C] 이후) |
| 10 | 갑옷 열쇠 (Armor Key) | 서쪽 계단 (West Stairway 1F) → `0-02` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 11 | 검 열쇠 (Sword Key) | 중앙 복도 (Central Corridor) → `0-0E` | 저택 세이브 룸 (Mansion Save Room) (플래그 22, 크리스) | 질은 락픽(Flg_0[0x7C] 이후) |
| 12 | 투구 열쇠 (Helmet Key) | 서쪽 계단 (West Stairway 2F) → `1-15` | 식물 42 방 (Plant 42 Room) (플래그 88, 공통) |  |
| 13 | 갑옷 열쇠 (Armor Key) | C자 복도 ('C' Passage) → `1-0D` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 14 | 갑옷 열쇠 (Armor Key) | C자 복도 ('C' Passage) → `1-05` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 16 | 갑옷 열쇠 (Armor Key) | 동쪽 계단 (East Stairway 2F) → `1-08` | 온실 (Greenhouse) (플래그 27, 공통) |  |
| 24 | 투구 열쇠 (Helmet Key) | 뒤쪽 복도 (Back Passage) → `0-19` | 식물 42 방 (Plant 42 Room) (플래그 88, 공통) |  |
| 25 | 투구 열쇠 (Helmet Key) | 강의실 입구 (Lesson Room Entry) → `1-0C` | 식물 42 방 (Plant 42 Room) (플래그 88, 공통) |  |
| 28 | 마스터 키 (Master Key) | 연구소 입구 (Laboratory Entry) → `4-01` | 중앙 연구실 (Main Lab) (플래그 95, 공통) |  |
| 29 | 동력 구역 열쇠 (Power Room Key) | O자 통로 ('O' Room) → `4-0C` | 영상 자료실 (Visual Data Room) (플래그 137, 공통) |  |
| 41 | 002호실 열쇠 (Key for Room 002) | 중앙 복도 (Central Corridor) → `3-06` | 벌집 복도 (Beehive Passage) (플래그 72, 공통) |  |
| 42 | 003호실 열쇠 (Key for Room 003) | 벌집 복도 (Beehive Passage) → `3-0A` | 무기 창고 (Arms Storage) (플래그 114, 공통) |  |
| 43 | 제어실 열쇠 (Control Room Key) | 대형 수조 (Water Tank) → `3-11` | 001호 욕실 (Room 001 Bathroom) (플래그 156, 공통) |  |
| 44 | 마스터 키 (Master Key) | 감방 입구 (Cell Entry) → `4-12` | 중앙 연구실 (Main Lab) (플래그 95, 공통) |  |
| 48 | 옷장 열쇠 (Closet Key) | 옷장 (Wardrobe) → `0-1C` |  |  |
