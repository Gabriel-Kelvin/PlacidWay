import pytest
from app import store

@pytest.fixture(autouse=True)
def isolated_runtime_store(monkeypatch,tmp_path):
    """Tests must neither share abuse counters nor sync fixture data to the cloud."""
    monkeypatch.setattr(store,'DATA',tmp_path)
    monkeypatch.setattr(store,'TEST_MODE',True)
    monkeypatch.delenv('SUPABASE_URL',raising=False)
    monkeypatch.delenv('SUPABASE_SECRET_KEY',raising=False)
    monkeypatch.setenv('SESSION_SECRET','isolated-test-session-secret-32-characters')
    store.init()
    store._sessions.clear()
