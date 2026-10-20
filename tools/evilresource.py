"""Parse scraped evilresource.com RE1 location pages -> data/evilresource.json (per page: title, links, contents by game mode)."""
import html, json, re
from pathlib import Path
ROOT = Path(__file__).parent.parent
out = []
for f in sorted((ROOT / 'refs/evilresource/pages').glob('*.html')):
    h = f.read_text(errors='replace')
    t = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    title = html.unescape(re.sub(r'<[^>]+>', '', t.group(1))).split('(')[0].strip() if t else f.stem
    for gm, body in re.findall(r'<li data-gamemode="(gm\d+)">(.*?)</li>', h, re.S):
        name = re.search(r'<h4[^>]*>(.*?)</h4>', body, re.S)
        mode = re.search(r'title="Game mode: ([^"]+)"', body)
        text = re.search(r'<div class="text">(.*?)</div>', body, re.S)
        link = re.search(r'href="/resident-evil/([^"/]+)/([^"]+)"', body)
        if name:
            out.append(dict(page=f.stem, location=title, name=html.unescape(re.sub(r'<[^>]+>', '', name.group(1)).strip()),
                            mode=mode.group(1) if mode else gm,
                            desc=html.unescape(re.sub(r'<[^>]+>', '', text.group(1))).strip() if text else '',
                            category=link.group(1) if link else '', slug=link.group(2) if link else ''))
(ROOT / 'data/evilresource.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(len(out))
