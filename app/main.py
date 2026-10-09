import asyncio
import hashlib
import hmac
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.config import ROOT
from app import store
from app.engine import answer
from app.ingestion import load_kb, refresh

async def maintenance():
    while True:
        store.purge()
        await store.sync()
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(store.init)
    await store.sync()
    task=asyncio.create_task(maintenance())
    yield
    task.cancel()

app=FastAPI(title='PlacidWay Knowledge Assistant',lifespan=lifespan,docs_url=None,redoc_url=None)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
active=set()

def secret():
    value=os.getenv('SESSION_SECRET','')
    if len(value)<32:raise HTTPException(503,'Session security is not configured.')
    return value.encode()

def sign(value):return value+'.'+hmac.new(secret(),value.encode(),hashlib.sha256).hexdigest()

def verified(value):
    try:
        body,sig=value.rsplit('.',1)
        return body if hmac.compare_digest(sign(body),value) else None
    except Exception:return None

def sid(request):
    value=verified(request.cookies.get('pw_session',''))
    return value if value and len(value)==32 else secrets.token_hex(16)

def origin():return os.getenv('APP_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL') or 'http://127.0.0.1:8000'

def cookie(response,name,value,max_age):
    response.set_cookie(name,value,httponly=True,samesite='strict',secure=origin().startswith('https:'),max_age=max_age)

def admin(request):
    value=verified(request.cookies.get('pw_admin',''))
    if not value or not value.startswith('admin:') or int(value.split(':')[1])<time.time():raise HTTPException(401,'Please sign in.')

async def throttle(request,namespace,maximum=20,seconds=60):
    # Direct socket address; do not trust caller-supplied X-Forwarded-For.
    ip=request.client.host if request.client else 'unknown'
    key=hmac.new(secret(),ip.encode(),hashlib.sha256).hexdigest()
    try:allowed=await asyncio.to_thread(store.limit,namespace+':'+key,maximum,seconds)
    except RuntimeError:raise HTTPException(503,'The assistant is temporarily unavailable. Please try again shortly.')
    if not allowed:raise HTTPException(429,'Please wait a moment before trying again.')

@app.middleware('http')
async def security(request,call_next):
    if request.method in ['POST','PUT','PATCH','DELETE']:
        request_origin=request.headers.get('origin')
        allowed=origin()
        if request_origin and request_origin!=allowed:return JSONResponse({'detail':'Origin not allowed'},status_code=403)
        if int(request.headers.get('content-length','0') or 0)>20000:return JSONResponse({'detail':'Request too large'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api'):response.headers['Cache-Control']='no-store'
    return response

@app.get('/')
async def home():return FileResponse(ROOT/'static/index.html')

@app.get('/admin')
async def admin_page():return FileResponse(ROOT/'static/admin.html')

@app.get('/api/health')
async def health():
    kb=load_kb()
    return {'status':'ok' if len(kb['sources'])==7 and all(s['lines'] and s['status']=='ok' for s in kb['sources']) else 'degraded','sources':len(kb['sources']),
            'last_refresh':kb['last_refresh'],'groq_configured':bool(os.getenv('GROQ_API_KEY')),
            'supabase_configured':store.configured(),'supabase':store.cloud_status(),'warnings':sum(s['status']!='ok' for s in kb['sources'])}

@app.get('/api/sources')
async def sources():
    kb=load_kb()
    return {'last_refresh':kb['last_refresh'],'sources':[{k:v for k,v in s.items() if k not in ['lines','etag','last_modified']} for s in kb['sources']]}

class Message(BaseModel):
    message:str=Field(min_length=1,max_length=2000)

@app.post('/api/chat')
async def chat(payload:Message,request:Request):
    await throttle(request,'chat')
    session_id=sid(request)
    if session_id in active:raise HTTPException(409,'Please wait for your current answer.')
    if len(active)>=4:raise HTTPException(503,'The assistant is busy. Please try again shortly.')
    active.add(session_id)
    context=store.session(session_id)
    async def stream():
        start=time.monotonic()
        def event(kind,data):return f'event: {kind}\ndata: {json.dumps(data,ensure_ascii=False)}\n\n'
        try:
            yield event('status',{'text':'Finding the right source…'})
            task=asyncio.create_task(answer(payload.message,context))
            while not task.done():
                done,_=await asyncio.wait({task},timeout=4)
                if not done:yield event('status',{'text':'Checking evidence and prices…'})
            result=await task
            store.save_session(session_id,context)
            await asyncio.to_thread(store.event,session_id,payload.message,result.get('entity') or result['intent'],result['outcome'],int((time.monotonic()-start)*1000))
            # Validation happens BEFORE release; partial unvalidated LLM output is never shown.
            yield event('validated',{k:v for k,v in result.items() if k!='text'})
            chunks=result['text'].split(' ')
            for i in range(0,len(chunks),7):
                yield event('delta',{'text':(' ' if i else '')+' '.join(chunks[i:i+7])})
                await asyncio.sleep(.012)
            yield event('done',{})
        except asyncio.CancelledError:
            if 'task' in locals():task.cancel()
            raise
        except Exception:
            await asyncio.to_thread(store.error,'chat_stream_failed')
            yield event('error',{'text':'Something interrupted this answer. Please try again or use the quote form.'})
        finally:active.discard(session_id)
    response=StreamingResponse(stream(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})
    cookie(response,'pw_session',sign(session_id),86400)
    return response

@app.post('/api/chat/reset')
async def reset(request:Request):
    session_id=sid(request)
    if session_id in active:raise HTTPException(409,'Please wait for your current answer.')
    store.delete_session(session_id)
    response=JSONResponse({'ok':True});response.delete_cookie('pw_session');return response

class Login(BaseModel):password:str=Field(max_length=200)

@app.post('/api/admin/login')
async def login(payload:Login,request:Request):
    await throttle(request,'login',5,900)
    expected=os.getenv('ADMIN_PASSWORD','')
    if not expected or not hmac.compare_digest(payload.password,expected):raise HTTPException(401,'Incorrect password.')
    response=JSONResponse({'ok':True});cookie(response,'pw_admin',sign('admin:'+str(int(time.time()+3600))),3600);return response

@app.post('/api/admin/logout')
async def logout():
    response=JSONResponse({'ok':True});response.delete_cookie('pw_admin');return response

@app.get('/api/admin/dashboard')
async def dashboard(request:Request):
    admin(request);kb=load_kb()
    try:metrics=await asyncio.to_thread(store.analytics)
    except Exception:raise HTTPException(503,'Dashboard temporarily unavailable. Please try again shortly.')
    return {**metrics,'refresh':{'at':kb['last_refresh'],'sources':[{k:v for k,v in s.items() if k!='lines'} for s in kb['sources']]},
            'history':list(reversed(kb['history'])),'supabase_configured':store.configured(),'supabase':store.cloud_status()}

@app.post('/api/admin/refresh')
async def do_refresh(request:Request):
    admin(request);await throttle(request,'refresh',2,60)
    result=await refresh()
    await store.sync()
    return result

