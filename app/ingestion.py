"""Strict seven-URL crawler. Visible text is data, never executable instructions."""
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser
import httpx
from bs4 import BeautifulSoup
from app.config import DATA, ROOT, USER_AGENT

BASE = 'https://www.placidway.com'
SOURCES = [
    ('clinic', 'Clinic profile', '/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center'),
    ('adenocarcinoma', 'Adenocarcinoma package', '/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC'),
    ('adrenal', 'Adrenal package', '/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC'),
    ('anal', 'Anal cancer package', '/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC'),
    ('videos', 'Clinic videos', '/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center'),
    ('prices', 'Clinic price list', '/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center'),
    ('comparison', 'International price comparison', '/search-medical-pricings/Alternative-Medicine/All/1'),
]
PACKAGES = {'adenocarcinoma', 'adrenal', 'anal'}
LOCK = asyncio.Lock()

def now():
    return datetime.now(timezone.utc).isoformat()

def clean(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract(html, source_id, title, url):
    soup = BeautifulSoup(html, 'html.parser')
    for el in soup.select('script,style,nav,footer,header,svg,noscript,form,select,button,[hidden],[aria-hidden="true"]'):
        el.decompose()
    if source_id in PACKAGES:
        roots = soup.select('#about')
    elif source_id == 'clinic':
        roots = soup.select('#about,#details,#treatments,#qualifications,#testimonials,#awards,#destination,#location,.profile-about .pack-about-items')
    elif source_id == 'prices':
        roots = soup.select('#prices,#about,#location')
    elif source_id == 'videos':
        roots = soup.select('.center-videos-page > #about,.center-videos-page > .related-videos')
    else:
        roots = soup.select('main.search-pricing_page .pack-inner-content')
    if not roots:
        raise ValueError('Expected content container missing; retaining previous content')
    # Tables become one verbatim normalized line per row, with their real headers.
    for root in roots:
        for table in root.select('table'):
            rows = []
            for row in table.select('tr'):
                cells = [clean(c.get_text(' ', strip=True)) for c in row.select('th,td')]
                rows.append(' | '.join(cells))
            table.replace_with(soup.new_string('\n' + '\n'.join(rows) + '\n'))
        for a in root.select('a,span,strong,b,em'):
            a.unwrap()
    texts = '\n'.join(root.get_text('\n', strip=True) for root in roots)
    for boundary in ['Related Experiences:', 'Share with AI', 'Recent Reviews', 'Request your Free Quote']:
        texts = texts.split(boundary)[0]
    lines = [clean(x) for x in texts.splitlines() if clean(x)]
    # Don't incorporate related recommendations or social widgets.
    lines = [x for x in lines if x not in ['Chat with Center', 'Read More', 'Copy link', 'Quote']]
    if len(lines) < 8:
        raise ValueError('Suspiciously empty extraction; retaining previous content')
    h1 = soup.find('h1')
    heading = clean(h1.get_text(' ', strip=True)) if h1 else title
    lines.insert(0, heading)
    if source_id in PACKAGES:
        block = soup.select_one('.pack-price-block')
        if block and 'Price starting from' in block.get_text():
            # Preserve the exact visible price wording as its own evidence.
            for text in block.stripped_strings:
                if '$' in text or 'Price starting from' in text:
                    lines.insert(1, clean(text))
    chunks = []
    section = heading
    for n, text in enumerate(lines, 1):
        if re.match(r'^(Included in|Cost of|Optional Specialized|Excluded Services|FAQs:|3-Week|Risks and|How |What |Who |Patient Travel|Alternative Cancer Treatment Cost)', text) and len(text) < 170:
            section = text
        chunks.append({'id': f'{source_id}:L{n}', 'line': n, 'text': text, 'section': section})
    content_hash = hashlib.sha256('\n'.join(lines).encode()).hexdigest()
    return {'id': source_id, 'title': title, 'heading': heading, 'url': url, 'hash': content_hash,
            'fetched_at': now(), 'checked_at': now(), 'status': 'ok', 'warning': None, 'lines': chunks}

def load_kb():
    path = DATA / 'knowledge.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'sources': [], 'history': [], 'last_refresh': None}

def save_kb(kb):
    temp = DATA / 'knowledge.tmp'
    temp.write_text(json.dumps(kb, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(DATA / 'knowledge.json')

def change_record(old, new):
    before = {x['text'] for x in old['lines']} if old else set()
    after = {x['text'] for x in new['lines']}
    return {'at': now(), 'source': new['id'], 'kind': 'updated' if old else 'initial',
            'old_hash': old['hash'] if old else None, 'new_hash': new['hash'],
            'removed': sorted(before-after), 'added': sorted(after-before),
            'price_before': sorted(x for x in before-after if '$' in x),
            'price_after': sorted(x for x in after-before if '$' in x)}

async def refresh(fetcher=None):
    if LOCK.locked():
        return {'status': 'running', 'message': 'A refresh is already running.'}
    async with LOCK:
        kb = load_kb()
        old_map = {s['id']: s for s in kb['sources']}
        sources, changes = [], []
        async with httpx.AsyncClient(timeout=35, headers={'User-Agent': USER_AGENT}, follow_redirects=False) as client:
            get = fetcher or client.get
            try:
                rr = await get(BASE + '/robots.txt')
                rr.raise_for_status()
                robots = RobotFileParser(); robots.parse(rr.text.splitlines())
                delay = max(1.05, robots.crawl_delay(USER_AGENT) or 0)
            except Exception:
                robots = None
                delay = 1.05
            for sid, title, path in SOURCES:
                old = old_map.get(sid)
                try:
                    if robots is None or not robots.can_fetch(USER_AGENT, BASE+path):
                        raise ValueError('Robots rules unavailable or disallow this page')
                    await asyncio.sleep(delay)
                    headers = {}
                    if old and old.get('etag'): headers['If-None-Match'] = old['etag']
                    if old and old.get('last_modified'): headers['If-Modified-Since'] = old['last_modified']
                    r = await get(BASE+path, headers=headers)
                    if r.status_code == 304 and old:
                        new = {**old, 'checked_at': now(), 'status': 'ok', 'warning': None}
                    else:
                        r.raise_for_status()
                        if len(r.content) > 3_000_000: raise ValueError('Page too large')
                        new = extract(r.text, sid, title, BASE+path)
                        new['etag'], new['last_modified'] = r.headers.get('etag'), r.headers.get('last-modified')
                        if old and len(new['lines']) < len(old['lines'])*0.55:
                            raise ValueError('Large content loss detected; review required')
                        if not old or old['hash'] != new['hash']:
                            changes.append(change_record(old, new))
                        else:
                            new['fetched_at'] = old['fetched_at']
                    sources.append(new)
                except Exception as exc:
                    warning = str(exc) if isinstance(exc, ValueError) else 'Source request failed; cached content retained'
                    new = dict(old) if old else {'id': sid, 'title': title, 'url': BASE+path, 'lines': [], 'fetched_at': None}
                    new.update(status='warning', warning=warning, checked_at=now())
                    sources.append(new)
        kb.update(sources=sources, last_refresh=now(), history=(kb['history']+changes)[-100:])
        save_kb(kb)
        return {'status': 'warning' if any(s['status']=='warning' for s in sources) else 'ok',
                'changed': len(changes), 'sources': len(sources), 'at': kb['last_refresh']}

def import_reviewed_snapshots():
    kb = {'sources': [], 'history': [], 'last_refresh': now()}
    for i, (sid, title, path) in enumerate(SOURCES, 1):
        source = extract((ROOT/'work'/f'source-{i}.html').read_text(encoding='utf-8'), sid, title, BASE+path)
        kb['sources'].append(source); kb['history'].append(change_record(None, source))
    save_kb(kb)
    print('Imported', len(kb['sources']), 'sources;', sum(len(s['lines']) for s in kb['sources']), 'evidence lines')

if __name__ == '__main__':
    import sys
    if '--snapshots' in sys.argv: import_reviewed_snapshots()
    else: print(asyncio.run(refresh()))
