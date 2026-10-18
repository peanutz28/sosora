"""Preflight must never reset a session when any readiness dependency fails."""
import asyncio
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('preflight.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

@pytest.mark.parametrize('failure', [None, 'model', 'asr', 'socket'])
def test_readiness_gates_seed(monkeypatch, capsys, failure):
    calls=[]
    monkeypatch.setenv('BACKEND_URL','http://backend')
    monkeypatch.setenv('FRONTEND_URL','http://frontend')
    monkeypatch.setenv('ASR_BASE_URL','http://asr')
    monkeypatch.setenv('LLM_BASE_URL','http://llm/v1')
    monkeypatch.setenv('LLM_MODEL','expected')
    class Response:
        text='SOSora'
        def __init__(self,value):self.value=value
        def raise_for_status(self):pass
        def json(self):return self.value
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):
            calls.append(url)
            if url.endswith('/models'):return Response({'data':[{'id':'wrong' if failure=='model' else 'expected'}]})
            if url=='http://backend/health':return Response({'status':'ok','demo_mode':False,'graph_edges':2})
            return Response({'status':'down' if failure=='asr' else 'ready','model':'tiny.en'})
        async def post(self,url,**kwargs):
            calls.append('seed')
            return Response({'seeded':9,'state':{'incidents':[{'reachable':True}]*9}})
    class Socket:
        async def __aenter__(self):
            if failure=='socket':raise OSError('unavailable')
            return self
        async def __aexit__(self,*args):pass
        async def recv(self):return '{"type":"state","state":{"incidents":[]}}'
    monkeypatch.setattr(p.httpx,'AsyncClient',Client)
    monkeypatch.setattr(p.websockets,'connect',lambda *a,**k:Socket())
    result=asyncio.run(p.main())
    assert result==int(failure is not None)
    assert ('seed' in calls)==(failure is None)
    assert len([c for c in calls if c!='seed'])==5
    assert ('FAIL seed withheld' in capsys.readouterr().out)==(failure is not None)
