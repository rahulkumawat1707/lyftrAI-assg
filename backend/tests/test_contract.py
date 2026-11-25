import asyncio
from concurrent.futures import ThreadPoolExecutor

import litellm
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.gateway import Gateway
from app.main import create_app


class TestGateway(Gateway):
    __test__ = False

    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []

    def deployments(self, failures):
        result = super().deployments(failures)
        for d in result:
            if 'mock_response' not in d['litellm_params']:
                d['litellm_params']['mock_response'] = litellm.ModelResponse(
                    choices=[{'message':{'role':'assistant','content':'Paris is the capital of France.'}}],
                    usage={'prompt_tokens':42,'completion_tokens':9,'total_tokens':51},
                    model='gpt-4o-mini')
        return result

    async def answer(self, messages, failure_header=''):
        self.calls.append(messages)
        return await super().answer(messages, failure_header)


@pytest.fixture
def setup(tmp_path):
    settings = Settings(database_url=f'sqlite:///{tmp_path / "test.db"}',
                        keys=('test-key-a','test-key-b'), model='openai/gpt-4o-mini', simulate=True)
    gateway = TestGateway(settings)
    with TestClient(create_app(settings, gateway)) as client:
        yield client, gateway, settings


def post(client, session='one', message='What is the capital of France?', **kwargs):
    return client.post('/chat', json={'session_id':session,'message':message}, **kwargs)


def test_health_and_exact_routes(setup):
    client, _, _ = setup
    assert client.get('/health').json() == {'status':'ok','keys_configured':2,'cache_enabled':True}
    assert client.get('/sessions/unknown/messages').status_code == 404
    assert client.get('/sessions/unknown/messages').json() == {'detail':'session not found'}


def test_cache_and_request_metadata(setup):
    client, gateway, _ = setup
    first = post(client).json()
    second = post(client, session='two').json()
    assert first['reply'] == second['reply']
    live, cached = first['metadata'], second['metadata']
    assert live['resolution_source'] == 'LIVE_INFERENCE'
    assert live['key_id'] == 'key_1'
    assert cached['resolution_source'] == 'LLM_CACHE'
    assert cached['key_id'] is None and cached['fallback_attempts'] == 0
    assert live['input_tokens'] == cached['input_tokens'] == 42
    assert live['output_tokens'] == cached['output_tokens'] == 9
    assert isinstance(live['latency_ms'], int)
    assert cached['latency_ms'] < live['latency_ms']
    different = post(client, session='three', message='A different question').json()
    assert different['metadata']['resolution_source'] == 'LIVE_INFERENCE'


@pytest.mark.parametrize('status',[429,500,502,503])
def test_litellm_router_failover(setup,status):
    client, _, _ = setup
    response = post(client, headers={'X-Simulate-Failure':f'key_1={status}'})
    assert response.status_code == 200, response.text
    assert response.json()['metadata']['key_id'] == 'key_2'
    assert response.json()['metadata']['fallback_attempts'] == 1
    assert response.json()['reply'] == 'Paris is the capital of France.'
    # Simulation is request scoped; normal traffic still starts at key_1.
    normal = post(client, session='normal', message='A fresh question').json()
    assert normal['metadata']['key_id'] == 'key_1'


def test_all_fail_and_rollback(setup):
    client, _, _ = setup
    response = post(client, headers={'X-Simulate-Failure':'*=429'})
    assert response.status_code == 503
    assert response.json() == {'detail':'all providers unavailable'}
    assert client.get('/sessions/one/messages').status_code == 404
    post(client)
    before = client.get('/sessions/one/messages').json()
    response = post(client, message='This turn must not be saved', headers={'X-Simulate-Failure':'key_1=429,key_2=500'})
    assert response.status_code == 503
    assert client.get('/sessions/one/messages').json() == before


@pytest.mark.parametrize('body',[
    {}, {'session_id':'s'}, {'message':'hello'}, {'session_id':'','message':'hi'},
    {'session_id':'  ','message':'hi'}, {'session_id':'x'*129,'message':'hi'},
    {'session_id':'s','message':''}, {'session_id':'s','message':'   '},
    {'session_id':'s','message':'x'*4001}, {'session_id':1,'message':'hi'},
    {'session_id':'s','message':None}, {'session_id':'s','message':['hi']},
])
def test_validation_does_not_save(setup, body):
    client, _, _ = setup
    response = client.post('/chat',json=body)
    assert response.status_code == 422
    assert 'detail' in response.json()
    assert client.get('/sessions/s/messages').status_code == 404


def test_malformed_json_and_trim(setup):
    client, _, _ = setup
    assert client.post('/chat',content='{bad',headers={'Content-Type':'application/json'}).status_code == 422
    assert post(client,message=' '+('x'*4000)+' ').status_code == 200
    assert client.get('/sessions/one/messages').json()['messages'][0]['content'] == 'x'*4000


def test_context_isolation_prompt_and_restart(setup):
    client, gateway, settings = setup
    client.post('/chat',json={'session_id':'one','message':'My name is Ada','system_prompt':'Be concise.'})
    post(client,message='What is my name?')
    assert [m['role'] for m in gateway.calls[-1]] == ['system','user','assistant','user']
    assert gateway.calls[-1][0]['content'] == 'Be concise.'
    assert gateway.calls[-1][1]['content'] == 'My name is Ada'
    post(client, session='two')
    assert len(gateway.calls[-1]) == 2
    history = client.get('/sessions/one/messages').json()
    assert [m['role'] for m in history['messages']] == ['user','assistant','user','assistant']
    assert 'metadata' not in history['messages'][0]
    assert 'metadata' in history['messages'][1]
    with TestClient(create_app(settings,TestGateway(settings))) as restarted:
        assert restarted.get('/sessions/one/messages').json() == history


def test_simulation_switch_and_cors(setup):
    client,gateway,settings = setup
    settings.simulate = False
    assert post(client,headers={'X-Simulate-Failure':'*=429'}).status_code == 200
    response = client.options('/chat',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,x-simulate-failure'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:3000'


def test_missing_keys_unhealthy(tmp_path):
    settings=Settings(database_url=f'sqlite:///{tmp_path / "empty.db"}', keys=())
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').status_code == 503
        assert post(client).json() == {'detail':'all providers unavailable'}
