"""Generate docs/wiki/*.md tables from data/annotated.json. Prose pages (native map, flags, sources) are hand-written."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
W = ROOT / 'docs/wiki'
d = json.loads((ROOT / 'data/annotated.json').read_text())
STAGE = ['저택(1차)', '저택 2층·지하', '정원·지하 동굴', '기숙사', '연구소']
CH = {(0,): '크리스', (1,): '질', (0, 1): '공통'}
FOLDER = {1: '저택', 2: '저택', 3: '정원', 4: '기숙사', 5: '연구소', 6: '저택(재방문)', 7: '저택(재방문)'}
rooms = d['rooms']


def rname(stage, room):
    r = rooms.get(f'{stage}-{room:02X}')
    return f"{r['name_ko']} ({r['name_en']})" if r else f'{stage}-{room:02X}'


def where(m):
    if not m:
        return '지도 없음'
    r = rooms[f"{m['stage']}-{m['slot']:02X}"]
    return f"p{r['page']} s{m['slot']} ({m['px']:.0f},{m['py']:.0f})"


def table(rows, head):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def write(name, title, body):
    (W / name).write_text(f'# {title}\n\n{body}\n')


# rooms
rows = []
for k, r in sorted(rooms.items(), key=lambda kv: (kv[1]['stage'], kv[1]['slot'])):
    rows.append((f"`{k}`", r['name_ko'], r['name_en'], d['pages'][r['page']]['file'], r['page'], r['visited_bit'], r['pixels']))
# preview images contain the game's own map art: generated locally (docs/wiki/img, git-ignored), listed here as paths
pages = '\n'.join(f"- 페이지 {p['page']} — `{p['file']}` (맵 스테이지 {p['stage']}): `img/page-{p['page']:02d}.png`"
                  for p in d['pages'])
write('03-rooms.md', '방 목록과 지도 슬롯',
      '키 `s-rr` = 맵 스테이지(0–4)-방 번호(16진). 저택 재방문(Stage6/7 폴더)은 스테이지 0/1과 같은 슬롯·플래그를 씁니다. '
      '방문 비트는 `Flg_7 (0xC387A0)`의 비트 번호(MSB 우선)입니다. 이름은 evilresource.com 하이라이트 이미지를 게임 TIM 방 마스크에 겹쳐 자동 대응했고, '
      '0-1D/0-1E/1-1D/2-11/2-12는 같은 방의 카메라별 분할 슬롯(exe 0x43ca60)입니다.\n\n'
      + table(rows, ['키', '한국어', 'English', 'TIM', '페이지', '방문 비트', '픽셀']) + '\n\n## 페이지별 미리보기\n\n'
      '미리보기 그림은 게임 원본 지도 그림을 포함하므로 저장소에 넣지 않습니다. `build.py`를 실행하면 `docs/wiki/img/`에 생성됩니다. '
      '노랑 마름모=잠긴 문, 시안=핵심 아이템, 흰색=문서·지도, 회색 점=일반 아이템, 주황 마름모=퍼즐, 연두=타자기·상자. `*`=이벤트 생성이라 방 중심에 표시.\n\n' + pages)

# locks
rows = []
key_found = defaultdict(list)
for i in d['items']:
    key_found[i['item']].append(i)
for L in d['locks']:
    sides = '<br>'.join(f"{rname(s['stage'], s['room'])} → `{s['target']}`" for s in L['sides'])
    found = '<br>'.join(f"{rname(i['stage'], i['room'])} (플래그 {i['flag']}, {CH[tuple(i['chars'])]})" for i in key_found.get(L['key'], []))
    note = '질은 락픽(Flg_0[0x7C] 이후)' if L['jill_lockpick'] else ''
    rows.append((L['bit'], f"{L['key_ko']} ({L['key_en']})", sides, found, note))
write('04-locks-keys.md', '잠긴 문과 열쇠',
      '문 AOT(`door_aot_set`, 26바이트)의 `LockId` 바이트: bit7=잠금 가능, 하위 6비트=해제 플래그 번호(`Flg_2 0xC38744`), '
      '`LockType`=필요 아이템(0=잠금 없음, 0xFE=반대쪽에서 잠김, 0xFF=이벤트 잠금). 판정 코드 exe `0x455b40..0x455c8b`. '
      '검 열쇠(51) 문은 질이 `Flg_0` 비트 0x7C(락픽 입수) 이후 락픽으로 엽니다.\n\n'
      + table(rows, ['해제 비트', '필요 아이템', '문 위치 → 목적지', '열쇠 위치', '비고']))

# items


def item_rows(cat):
    rows = []
    for i in sorted((x for x in d['items'] if x['category'] == cat), key=lambda x: (x['stage'], x['room'], x['item'])):
        rows.append((f"{i['name_ko']} ({i['name_en']})", i['item'], rname(i['stage'], i['room']), i['flag'], CH[tuple(i['chars'])],
                     '정확' if i['exact_position'] else '이벤트(방 중심)', '예' if i['event_guarded'] else '', ','.join(FOLDER[f] for f in i['folders']),
                     where(i['map'])))
    return rows


H = ['아이템', 'ID', '방', '획득 플래그', '캐릭터', '위치', '조건부', '데이터 폴더', '지도 좌표']
write('05-key-items.md', '핵심 아이템',
      '`item_aot_set`(26바이트) +0x16 바이트 = 획득 플래그 번호, 판정은 `Flg_ck(0xC3876C, flag)`(exe 0x418c00). '
      '좌표는 AOT 사각형 중심을 방별 변환으로 지도 TIM 픽셀에 투영한 값입니다. 사각형이 0인 항목은 이벤트(시계 뒤, 동상 파편 등)로 생성되므로 방 중심에 둡니다. '
      '"조건부"는 SCD `if ck(...)` 아래에서만 놓이는 경우입니다.\n\n' + table(item_rows('key'), H))
write('07-documents-maps.md', '문서와 지도',
      '아이템 ID 78–83은 벽 지도/지도 아이템(핸들러가 AOT 종류 0xF로 처리), 95 이상은 파일입니다.\n\n' + table(item_rows('document'), H))
write('08-common-items.md', '일반 아이템(탄약·회복·무기·잉크 리본)', table(item_rows('common'), H))

# item verification audit (tools/verify_items.py)
ST = {'unlisted': 'evilresource 목록에 없음', 'given': '이벤트로 건네받음', 'pickup': '줍기'}
rows = []
for i in sorted(d['items_excluded'], key=lambda x: (x['stage'], x['room'], x['item'])):
    for c in i['hidden_chars']:
        ev = i['evidence'][('Chris', 'Jill')[c]]
        rows.append((f"{i['name_ko']} ({i['name_en']})", rname(i['stage'], i['room']), i['flag'], ('크리스', '질')[c], ST[ev['status']],
                     (ev['desc'] or '').replace('|', '/')[:90]))
write('12-item-verification.md', '아이템 검증(지도 표시 대상)',
      'RDT의 `item_aot_set`은 엔진이 *놓을 수 있는* 아이템이라 실제로 줍지 못하는 기록도 섞여 있습니다: '
      '교체 상태(선반에 되돌린 망가진 산탄총, 바·식당의 엠블럼 교체), 컷신으로 건네받는 아이템(배리·레베카·리처드), '
      '같은 플래그를 쓰는 캐릭터별 변형(창고의 산성탄=질 / 권총탄=크리스 등), 사용되지 않는 기록. '
      '그래서 각 아이템을 evilresource 방 페이지(원작 Chris/Jill 모드)의 내용과 캐릭터별로 대조해, '
      '"그 방에서 줍는다"고 확인된 것만 지도에 표시합니다(`tools/verify_items.py`). '
      '방↔페이지는 내용 대조(room_match)와 지도 슬롯 이름 양쪽을 씁니다. 첫 문장이 "given to you/hands you"이면 건네받는 아이템으로 봅니다.\n\n'
      '추가: 2층 지도(79)는 `item_aot_set`이 없고 응접실 입구 벽난로 이벤트(`ck(7,17)`)로 주므로 `curated.json event_items`로 넣었습니다.\n\n'
      '## 제외된 항목\n\n' + table(rows, ['아이템', '방', '획득 플래그', '캐릭터', '판정', 'evilresource 설명']))

# puzzles
rows = [(rname(p['stage'], p['room']), ', '.join(f'{k} ({e})' for k, e in zip(p['items_ko'], p['items_en'])) or '-', CH[tuple(p['chars'])],
         p['note'], p['source'], where(p['map'])) for p in d['puzzles']]
write('06-puzzles.md', '퍼즐(아이템 사용 지점)',
      'evilresource 퍼즐 가이드 16개와 아이템 사용 지점을 합쳤습니다. 위치는 퍼즐을 실행하는 AOT의 중심입니다: '
      '`useitem` 데이터[0]=9는 이벤트 실행(번호=데이터[2]), 데이터[0]=4는 아이템 검사·물건 밀어 넣기 목표 칸(갑옷 방의 환기구 메시지 AOT와 같은 좌표)입니다. '
      '한 방에 여러 퍼즐이 있으면 이벤트 번호로 구분했습니다(바: 피아노=8, 비밀 통로 동상=4/5). '
      'AOT와 evilresource 방향 설명이 어긋나는 문 없는 카메라 슬롯·문 1개짜리 방(시체 안치소, 동력실)은 설명의 방향(남서쪽 책상, 동쪽 단말기)으로 둡니다. '
      '헬기장(2-03)은 게임 지도에 그려지지 않아 표시하지 않습니다. 근거가 없던 "Room 003 빈 책" 퍼즐은 삭제했습니다(빈 책은 Room 001 침대 위에 있을 뿐).\n\n'
      + table(rows, ['방', '사용 아이템', '캐릭터', '내용', '근거', '지도 좌표']))

# saves
rows = [('타자기' if s['kind'] == 'typewriter' else '아이템 상자', rname(s['stage'], s['room']), where(s['map'])) for s in d['saves']]
write('09-save-points.md', '타자기와 아이템 상자', 'AOT SCE 16(타자기)·8(아이템 상자).\n\n' + table(rows, ['종류', '방', '지도 좌표']))
print('wiki tables written')
