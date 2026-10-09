"""Cloud persistence, outage retry, snapshot identity and privacy."""
import asyncio,json,httpx
from app import store,ingestion

def setup_cloud(monkeypatch,handler):
    monkeypatch.setenv('SUPABASE_URL','https://testproject.supabase.co')
    monkeypatch.setenv('SUPABASE_SECRET_KEY','sb_secret_test_only')
    monkeypatch.setattr(store,'TEST_MODE',False)
    monkeypatch.setattr(ingestion,'load_kb',lambda:{'sources':[{'id':'clinic','hash':'abc','status':'ok'}],'history':[]})
    original=httpx.Client
    monkeypatch.setattr(store.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))

def test_direct_cloud_write_never_saves_transcripts(monkeypatch):
    calls=[]
    def handler(r):
        calls.append(r)
        return httpx.Response(200,json={} if r.url.path.endswith('pw_dashboard') else None)
    setup_cloud(monkeypatch,handler)
    store.event('chat','private question','anal','answered',50)
    store.save_session('chat',{'history':[{'user':'private question','assistant':'private answer'}]})
    result=asyncio.run(store.sync())
    assert result['status']=='ok' and not store._queue
    body=' '.join(r.content.decode() for r in calls)
    assert 'private question' not in body and 'private answer' not in body
    event=json.loads(next(r.content for r in calls if r.url.path.endswith('pw_events')))
    assert event['question']=='Topic: anal'
    assert all('authorization' not in r.headers for r in calls)
    calls.clear()
    asyncio.run(store.sync())
    assert not any(r.url.path.endswith('pw_knowledge') for r in calls)

def test_failed_cloud_retains_volatile_queue_and_retry_succeeds(monkeypatch):
    fail=[True]
    def handler(r):return httpx.Response(503 if fail[0] else 204)
    setup_cloud(monkeypatch,handler)
    store.event('chat','private','adrenal','unknown',20)
    assert len(store._queue)==1
    assert asyncio.run(store.sync())['status']=='pending'
    fail[0]=False
    assert asyncio.run(store.sync())['synced']==1
    assert not store._queue

def test_snapshot_uploaded_again_for_different_project(monkeypatch):
    posts=[]
    def handler(r):
        if r.url.path.endswith('pw_knowledge'):posts.append(str(r.url))
        return httpx.Response(204)
    setup_cloud(monkeypatch,handler)
    asyncio.run(store.sync())
    monkeypatch.setenv('SUPABASE_URL','https://secondproject.supabase.co')
    asyncio.run(store.sync())
    assert len(posts)==2 and 'secondproject' in posts[-1]

def test_legacy_header_and_no_cloud_without_configuration():
    assert store.cloud_headers('eyJtest')['Authorization']=='Bearer eyJtest'
    assert asyncio.run(store.sync())=={'configured':False,'synced':0}
    assert store.cloud_status()['status']=='not_connected'

def test_limiter_fails_closed_on_database_outage(monkeypatch):
    import pytest
    setup_cloud(monkeypatch,lambda r:httpx.Response(503))
    with pytest.raises(RuntimeError):store.limit('test',5,60)
