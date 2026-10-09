"""Supabase persistence; conversation turns live only in process memory."""
import asyncio, copy, hashlib, json, os, re, threading, time, uuid
from datetime import datetime, timezone
import httpx
from app.config import DATA, RETENTION
_sessions = {}
SESSION_TTL = 86400
TEST_MODE = False
_queue, _events, _limits, _errors, _state, _versions = {}, [], {}, [], {}, {}
_lock = threading.RLock()
_sync_lock = asyncio.Lock()
def stamp(): return datetime.now(timezone.utc).isoformat()
def configured(): return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SECRET_KEY'))
def cloud_headers(key):
    h={'apikey':key,'Prefer':'resolution=merge-duplicates'}
    if key.startswith('eyJ'): h['Authorization']='Bearer '+key
    return h

def request(method,path,**kwargs):
    if not configured(): raise RuntimeError('Supabase is not configured')
    with httpx.Client(timeout=15,headers=cloud_headers(os.environ['SUPABASE_SECRET_KEY'])) as c:
        r=c.request(method,os.environ['SUPABASE_URL'].rstrip('/')+'/rest/v1/'+path,**kwargs)
        r.raise_for_status()
        return r.json() if r.content else None

def init():
    if TEST_MODE:
        for value in [_sessions,_queue,_events,_limits,_errors,_state,_versions]: value.clear()
        return
    if not configured(): raise RuntimeError('SUPABASE_URL and SUPABASE_SECRET_KEY are required')
    try:
        rows=request('GET','pw_knowledge',params={'id':'eq.active','select':'snapshot'})
        if rows:
            from app.ingestion import save_kb
            save_kb(rows[0]['snapshot'])
        _state.update(status='ok',last_success=stamp())
    except Exception:
        _state.update(status='pending')
        error('supabase_startup_read_failed')

def redact(text):
    text=re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b','[email removed]',text)
    text=re.sub(r'\b(?:gsk_|sk-|sb_secret_)[\w-]+','[key removed]',text)
    text=re.sub(r'(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)','[phone removed]',text)
    text=re.sub(r'(?i)\b(my name is|i am called)\s+[^,.!?]+','[name removed]',text)
    return text[:2000]

def write(table,row):
    if TEST_MODE:
        (_events if table=='pw_events' else _errors).append(row)
        return
    try: request('POST',table,json=row)
    except Exception:
        with _lock:
            if len(_queue)>=1000: _queue.pop(next(iter(_queue)))
            _queue[row['id']]=(table,row)
        _state.update(status='pending')

def event(session_id,question,topic,outcome,latency_ms):
    write('pw_events',dict(id=str(uuid.uuid4()),created_at=stamp(),session_id=session_id,question='Topic: '+str(topic),topic=topic,outcome=outcome,latency_ms=latency_ms))
def error(code): write('pw_errors',dict(id=str(uuid.uuid4()),created_at=stamp(),code=code[:100]))
def limit(bucket,maximum,seconds):
    if TEST_MODE:
        with _lock:
            count,expiry=_limits.get(bucket,(0,0))
            if expiry<=time.time(): count,expiry=0,time.time()+seconds
            if count>=maximum: return False
            _limits[bucket]=(count+1,expiry)
            return True
    try: return request('POST','rpc/pw_take_limit',json={'p_bucket':bucket,'p_maximum':maximum,'p_seconds':seconds}) is True
    except Exception:
        error('supabase_rate_limit_unavailable')
        raise RuntimeError('Rate limit service unavailable') from None

def session(sid):
    value=_sessions.get(sid)
    if value and value[0]>time.time(): return copy.deepcopy(value[1])
    _sessions.pop(sid,None)
    return {'entity':None,'history':[],'disclaimer':False}
def save_session(sid,data): _sessions[sid]=(time.time()+SESSION_TTL,copy.deepcopy(data))
def delete_session(sid): _sessions.pop(sid,None)
def purge():
    for sid,(expiry,_) in list(_sessions.items()):
        if expiry<time.time(): _sessions.pop(sid,None)
def cloud_status(): return dict(_state) if configured() else {'status':'not_connected'}
async def sync():
    if not configured(): return {'configured':False,'synced':0}
    if _sync_lock.locked(): return {'configured':True,'synced':0,'status':'syncing'}
    async with _sync_lock: return await asyncio.to_thread(_sync)
def _sync():
    project=os.environ['SUPABASE_URL'].rstrip('/')
    count=0
    _state.update(status='syncing',last_attempt=stamp())
    try:
        with _lock: rows=list(_queue.items())[:100]
        for key,(table,row) in rows:
            request('POST',table,json=row)
            with _lock: _queue.pop(key,None)
            count+=1
        request('POST','rpc/pw_cleanup',json={'p_days':RETENTION})
        from app.ingestion import load_kb
        kb=load_kb()
        version=hashlib.sha256(json.dumps(kb,sort_keys=True).encode()).hexdigest()
        if kb['sources'] and _versions.get(project)!=version:
            request('POST','pw_knowledge',json={'id':'active','created_at':stamp(),'snapshot':kb})
            _versions[project]=version
        _state.update(status='pending' if _queue else 'ok',last_success=stamp())
        return {'configured':True,'synced':count,'status':_state['status']}
    except Exception:
        _state.update(status='pending')
        return {'configured':True,'synced':count,'status':'pending','warning':'Supabase unavailable; pending metrics temporarily held in memory.'}
def analytics():
    if TEST_MODE:
        data={'chats':len({r['session_id'] for r in _events}),'questions':len(_events),'outcomes':[],'popular':[],'gaps':[],'errors':_errors[-15:]}
    else: data=request('POST','rpc/pw_dashboard',json={})
    return {**data,'pending_sync':len(_queue)}
