# 퍼즐(아이템 사용 지점)

evilresource 퍼즐 가이드 16개와 아이템 사용 지점을 합쳤습니다. 위치는 퍼즐을 실행하는 AOT의 중심입니다: `useitem` 데이터[0]=9는 이벤트 실행(번호=데이터[2]), 데이터[0]=4는 아이템 검사·물건 밀어 넣기 목표 칸(갑옷 방의 환기구 메시지 AOT와 같은 좌표)입니다. 한 방에 여러 퍼즐이 있으면 이벤트 번호로 구분했습니다(바: 피아노=8, 비밀 통로 동상=4/5). AOT와 evilresource 방향 설명이 어긋나는 문 없는 카메라 슬롯·문 1개짜리 방(시체 안치소, 동력실)은 설명의 방향(남서쪽 책상, 동쪽 단말기)으로 둡니다. 헬기장(2-03)은 게임 지도에 그려지지 않아 표시하지 않습니다. 근거가 없던 "Room 003 빈 책" 퍼즐은 삭제했습니다(빈 책은 Room 001 침대 위에 있을 뿐).

| 방 | 사용 아이템 | 캐릭터 | 내용 | 근거 | 지도 좌표 |
|---|---|---|---|---|---|
| 식당 (Dining Room) | 황금 엠블럼 (Gold Emblem) | 공통 | Gold Emblem in the fireplace hollow -> clock compartment (Shield Key) | RDT 1050 useitem event 4/5 (fireplace hollow; ER: west side) | p0 s5 (17,60) |
| 바 (Bar) | 악보 (Music Score) | 공통 | Music Score on the piano -> secret room | RDT 10F0 useitem event 8 (piano) | p0 s15 (33,41) |
| 바 (Bar) | 엠블럼 (Emblem) | 공통 | Emblem replaces the Gold Emblem in the secret room | RDT 10F0 useitem event 4/5 (statue in the hidden passage) | p0 s30 (32,30) |
| 호랑이 석상실 (Tiger Statue Room) | 푸른 보석 (Blue Jewel), 붉은 보석 (Red Jewel) | 공통 | Blue and Red Jewel in the tiger's eyes | RDT 10D0 useitem (tiger statue) | p0 s13 (26,28) |
| 거실 (Living Room) | 망가진 산탄총 (Broken Shotgun) | 크리스 | Broken Shotgun replaces the rack shotgun (Chris) | RDT 1160 shotgun item_aot_set (wall rack) | p0 s22 (118,42) |
| 지붕 통로 (Roofed Passage) | 바람 문장 (Wind Crest), 달 문장 (Moon Crest), 별 문장 (Star Crest), 태양 문장 (Sun Crest) | 공통 | Four crests on the mount -> courtyard door | RDT 11A0 useitem events 14/17/18/19 (crest mount) | p0 s26 (82,4) |
| 온실 (Greenhouse) | 제초제 (Herbicide) | 공통 | Herbicide into the greenhouse water pump | RDT 10C0 useitem event 11 (water pump) | p0 s12 (42,30) |
| 작은 식당 (Small Dining Room) | 라이터 (Lighter) | 공통 | Lighter on the candles | RDT 20F0 useitem event 21 (candles) | p1 s15 (105,48) |
| 강의실 입구 (Lesson Room Entry) | 라이터 (Lighter) | 공통 | Lighter on the fireplace -> Map of 2F | RDT 20B0 useitem event 21 (fireplace) | p1 s11 (122,29) |
| 기둥 복도 (Pillar Passage) | 혈청 (Serum) | 공통 | Serum for Richard | RDT 20D0 event AOT (Richard; ER: lying on the floor) | p1 s13 (102,55) |
| 수문 (Water Gate) | 사각 크랭크 (Square Crank) | 공통 | Square Crank raises/lowers the floodgate | RDT 3010 useitem event 2 (crank socket) | p3 s1 (84,30) |
| 폭포 (Falls) | 배터리 (Battery) | 공통 | Battery powers the falls elevator | RDT 3020 useitem event 12 (elevator) | p3 s2 (69,62) |
| 분수 (Fountain) | 늑대 메달 (Wolf Medal), 독수리 메달 (Eagle Medal) | 공통 | Wolf and Eagle Medals in the fountain | RDT 3050 useitem events 9/10: midpoint of the east (eagle) and west (wolf) hollows; marker at the fountain centre (hole of the drawn ring) | p3 s5 (56,82) |
| 지하 입구 (Underground Entry) | 육각 크랭크 (Hexagonal Crank) | 공통 | Hexagonal Crank | RDT 3070 useitem event 3 | p4 s7 (59,18) |
| 바위 통로 2 (Boulder Passage 2) | 육각 크랭크 (Hexagonal Crank) | 공통 | Hexagonal Crank | RDT 30F0 useitem event 3 (item-check areas excluded) | p4 s15 (48,62) |
| 지하 석상실 (Item Chamber) | 육각 크랭크 (Hexagonal Crank) | 공통 | Hexagonal Crank | RDT 3060 useitem event 3 | p4 s6 (22,66) |
| 2-03 | 신호탄 (Flare) | 공통 | Flare on the heliport | heliport has no map slot | 지도 없음 |
| 회의실 (Meeting Room) | V-JOLT (V-Jolt) | 공통 | V-Jolt on Plant 42's roots | RDT 40F0 useitem event 0 (Plant 42's roots; ER: meeting room) | p6 s15 (89,46) |
| 비상 통로 (Emergency Tunnel) | 배터리 (Battery) | 공통 | Battery powers the heliport elevator | RDT 5010 useitem event 12 (elevator) | p7 s1 (34,32) |
| 영상 자료실 (Visual Data Room) | 슬라이드 (Slides) | 공통 | Slides in the projector | RDT 5040 useitem event 16 (projector) | p8 s4 (54,54) |
| 수술실 (Operating Room) | MO 디스크 (MO-Disk) | 공통 | MO-Disk terminal (Morgue) | RDT 5070 useitem event 20 (MO terminal; ER: south west desk of the morgue); Morgue is a camera slot without doors, placed by ER: desk in the south west corner | p9 s22 (60,28) |
| 동력 미로 2 (Power Maze 2) | MO 디스크 (MO-Disk) | 공통 | MO-Disk terminal (Power Maze 2) | RDT 5100 useitem event 13 (MO terminal) | p9 s16 (95,83) |
| 개인실 (Private Room) | MO 디스크 (MO-Disk) | 공통 | MO-Disk terminal (Private Room) | RDT 5090 useitem event 13 (MO terminal) | p9 s9 (52,14) |
| 갑옷실 (Armor Room) | - | 공통 | Armor Room: push both statues onto the floor vents, then press the switch (Sun Crest cabinet) | RDT 2050 event 0 switch; vents = useitem type-4 targets at x 4785/13635 | p1 s5 (94,33) |
| 대미술관 (Large Gallery) | - | 공통 | Large Gallery: press the picture switches from newborn to old man, then the last picture (Star Crest) | RDT 1170 event 12 (last picture) | p0 s23 (83,44) |
| 개인 서재 (Private Library) | - | 공통 | Private Library: push the statue to the spotlight spot -> secret bookcase (MO Disk) | RDT 2170 event 1 (light spot; ER: north west corner); switch = event 0 on the west wall | p1 s23 (26,14) |
| 박제실 (Trophy Room) | - | 공통 | Trophy Room: switch the light off, push the steps under the deer head (Red Jewel) | RDT 2150 event 4 (deer head) | p1 s21 (12,10) |
| 벌집 복도 (Beehive Passage) | - | 공통 | Drug storeroom door code: light all nine lamps | RDT 4080 door to the Drug Storeroom | p5 s8 (70,54) |
| 약품 창고 (Drug Storeroom) | - | 공통 | Mix V-JOLT (Water, UMB No.2/3/4/7, NP-003...) at the chemicals | RDT 4090 event 6/17 | p5 s9 (70,45) |
| 수술실 (Operating Room) | - | 공통 | Poison gas: push both crates onto the floor vents before moving the steps to the air duct | RDT 5070 useitem type-4 targets (vents at z 6430/9820) | p9 s7 (78,24) |
| 작은 실험실 (Small Lab) | - | 공통 | Small Lab computer: user/password from the X-Ray room unlock the electronic doors | RDT 5060 event 0 (computer) | p9 s6 (75,8) |
| 동력 미로 1 (Power Maze 1) | - | 공통 | Power Maze 1 terminal (south west): restore power | RDT 50F0 event 0 | p9 s15 (78,68) |
| 동력실 (Power Room) | - | 공통 | Power Room terminal (east side): connect elevator power | ER: terminal on the east side (one-door room; message AOTs project west of the door) | p9 s17 (98,90) |
| 대형 수조 입구 (Water Tank Entry) | - | 공통 | Push the three crates into the pool to cross to the water tank | whole passage (pool = useitem type-4 areas); room anchor | p6 s13 (100,32) |
