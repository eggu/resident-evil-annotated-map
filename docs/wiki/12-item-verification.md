# 아이템 검증(지도 표시 대상)

RDT의 `item_aot_set`은 엔진이 *놓을 수 있는* 아이템이라 실제로 줍지 못하는 기록도 섞여 있습니다: 교체 상태(선반에 되돌린 망가진 산탄총, 바·식당의 엠블럼 교체), 컷신으로 건네받는 아이템(배리·레베카·리처드), 같은 플래그를 쓰는 캐릭터별 변형(창고의 산성탄=질 / 권총탄=크리스 등), 사용되지 않는 기록. 그래서 각 아이템을 evilresource 방 페이지(원작 Chris/Jill 모드)의 내용과 캐릭터별로 대조해, "그 방에서 줍는다"고 확인된 것만 지도에 표시합니다(`tools/verify_items.py`). 방↔페이지는 내용 대조(room_match)와 지도 슬롯 이름 양쪽을 씁니다. 첫 문장이 "given to you/hands you"이면 건네받는 아이템으로 봅니다.

추가: 2층 지도(79)는 `item_aot_set`이 없고 응접실 입구 벽난로 이벤트(`ck(7,17)`)로 주므로 `curated.json event_items`로 넣었습니다.

## 제외된 항목

| 아이템 | 방 | 획득 플래그 | 캐릭터 | 판정 | evilresource 설명 |
|---|---|---|---|---|---|
| 혈청 (Serum) | 저택 세이브 룸 (Mansion Save Room) | 23 | 크리스 | evilresource 목록에 없음 |  |
| 혈청 (Serum) | 저택 세이브 룸 (Mansion Save Room) | 23 | 질 | evilresource 목록에 없음 |  |
| 혈청 (Serum) | 저택 세이브 룸 (Mansion Save Room) | 24 | 크리스 | evilresource 목록에 없음 |  |
| 혈청 (Serum) | 저택 세이브 룸 (Mansion Save Room) | 24 | 질 | evilresource 목록에 없음 |  |
| 황금 엠블럼 (Gold Emblem) | 식당 (Dining Room) | 43 | 크리스 | evilresource 목록에 없음 |  |
| 황금 엠블럼 (Gold Emblem) | 식당 (Dining Room) | 43 | 질 | evilresource 목록에 없음 |  |
| 엠블럼 (Emblem) | 바 (Bar) | 20 | 크리스 | evilresource 목록에 없음 |  |
| 엠블럼 (Emblem) | 바 (Bar) | 20 | 질 | evilresource 목록에 없음 |  |
| 책상 열쇠 (Desk Key) | 욕실 (Bathroom) | 3 | 질 | evilresource 목록에 없음 |  |
| 망가진 산탄총 (Broken Shotgun) | 거실 (Living Room) | 1 | 크리스 | evilresource 목록에 없음 |  |
| 망가진 산탄총 (Broken Shotgun) | 거실 (Living Room) | 1 | 질 | evilresource 목록에 없음 |  |
| 권총 탄창 (Hand Gun Bullets) | 저택 창고 (Mansion Storeroom) | 217 | 질 | evilresource 목록에 없음 |  |
| 유산탄 (Acid Rounds) | 저택 창고 (Mansion Storeroom) | 217 | 크리스 | evilresource 목록에 없음 |  |
| 무전기 (Comm. Radio) | 지붕 통로 (Roofed Passage) | 59 | 크리스 | evilresource 목록에 없음 |  |
| 책상 열쇠 (Desk Key) | 창고 (Store Room) | 34 | 질 | evilresource 목록에 없음 |  |
| 산탄총 탄약 (Shotgun Shells) | 침실 (Bedroom) | 38 | 질 | evilresource 목록에 없음 |  |
| 무전기 (Comm. Radio) | 강의실 (Lesson Room) | 85 | 질 | 이벤트로 건네받음 | If you have not already acquired it, it will be given to you by Barry. |
| 패스 넘버 (Pass Number) | 강의실 (Lesson Room) | 86 | 질 | 이벤트로 건네받음 | After being lowered down into the Isolated Passage, wait for a few minutes until Barry ret |
| 책상 열쇠 (Desk Key) | 테라스 입구 (Terrace Entry) | 149 | 질 | evilresource 목록에 없음 |  |
| 화염방사기 (Flamethrower) | 바위 통로 1 (Boulder Passage 1) | 153 | 질 | evilresource 목록에 없음 |  |
| 매그넘 탄약 (Magnum Rounds) | 바위 통로 1 (Boulder Passage 1) | 125 | 질 | evilresource 목록에 없음 |  |
| 소이탄 (Flame Rounds) | 바위 통로 1 (Boulder Passage 1) | 126 | 크리스 | evilresource 목록에 없음 |  |
| 잉크 리본 (Ink Ribbon) | 거미 방 (Black Tiger Room) | 250 | 크리스 | evilresource 목록에 없음 |  |
| 화염방사기 (Flamethrower) | 직선 통로 (Straight Passage) | 172 | 크리스 | evilresource 목록에 없음 |  |
| 권총 탄창 (Hand Gun Bullets) | 기숙사 세이브 룸 (Guardhouse Save Room) | 166 | 질 | evilresource 목록에 없음 |  |
| 유탄 (Explosive Rounds) | 기숙사 세이브 룸 (Guardhouse Save Room) | 167 | 크리스 | evilresource 목록에 없음 |  |
| 무전기 (Comm. Radio) | 벌집 복도 (Beehive Passage) | 8 | 크리스 | 이벤트로 건네받음 | If you have not already acquired it, it will be given to you by Rebecca if she helped you  |
| 백지 책 (Blank Book) | 003호실 (Room 003) | 255 | 크리스 | evilresource 목록에 없음 |  |
| 백지 책 (Blank Book) | 003호실 (Room 003) | 255 | 질 | evilresource 목록에 없음 |  |
| 책상 열쇠 (Desk Key) | 회의실 (Meeting Room) | 105 | 질 | evilresource 목록에 없음 |  |
| 매그넘 탄약 (Magnum Rounds) | 연구소 세이브 룸 (Lab Save Room) | 234 | 질 | evilresource 목록에 없음 |  |
| 소이탄 (Flame Rounds) | 연구소 세이브 룸 (Lab Save Room) | 234 | 크리스 | evilresource 목록에 없음 |  |
