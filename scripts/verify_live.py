"""Run real acceptance checks against a deployed backend (uses LLM tokens)."""
import argparse
import uuid
import httpx


parser = argparse.ArgumentParser()
parser.add_argument('--backend', required=True)
parser.add_argument('--frontend', required=True)
args = parser.parse_args()
base = args.backend.rstrip('/')
origin = args.frontend.rstrip('/')
run_id = uuid.uuid4().hex[:12]
client = httpx.Client(timeout=120, follow_redirects=True)


def send(session, message, failure=None):
    return client.post(base + '/chat', json={'session_id':session, 'message':message},
                       headers={'X-Simulate-Failure':failure} if failure else {})


def check_reply(response):
    assert response.status_code == 200, f'Chat returned HTTP {response.status_code}; no provider error body printed'
    body = response.json()
    assert isinstance(body['reply'], str) and body['reply'].strip()
    metadata = body['metadata']
    assert metadata['resolution_source'] in ('LIVE_INFERENCE','LLM_CACHE')
    assert isinstance(metadata['model'], str) and metadata['model']
    for field in ('latency_ms','input_tokens','output_tokens','fallback_attempts'):
        assert type(metadata[field]) is int and metadata[field] >= 0
    return body


assert client.get(origin).status_code == 200, 'Frontend unavailable'
health = client.get(base + '/health')
assert health.status_code == 200
assert health.json()['status'] == 'ok' and health.json()['keys_configured'] >= 2
assert health.json()['cache_enabled'] is True
cors = client.options(base + '/chat', headers={'Origin':origin,
    'Access-Control-Request-Method':'POST', 'Access-Control-Request-Headers':'content-type,x-simulate-failure'})
assert cors.headers.get('access-control-allow-origin') in (origin, '*'), 'Frontend origin not allowed'
print('PASS frontend, backend health and CORS')

message = f'What is the capital of France? Answer briefly. Verification reference {run_id}.'
first_session = f'live-{run_id}-first'
first = check_reply(send(first_session, message))
second = check_reply(send(f'live-{run_id}-cache', message))
assert first['metadata']['resolution_source'] == 'LIVE_INFERENCE'
assert second['metadata']['resolution_source'] == 'LLM_CACHE'
assert first['reply'] == second['reply']
assert second['metadata']['key_id'] is None
assert second['metadata']['fallback_attempts'] == 0
assert first['metadata']['input_tokens'] == second['metadata']['input_tokens']
assert first['metadata']['output_tokens'] == second['metadata']['output_tokens']
assert second['metadata']['latency_ms'] < first['metadata']['latency_ms']
print('PASS real inference, cache identity, cached usage and faster latency')

for status in (429, 500):
    body = check_reply(send(f'live-{run_id}-fallback-{status}',
        f'Give one short fact about Python. Reference {run_id}-{status}.', f'key_1={status}'))
    assert body['metadata']['key_id'] == 'key_2'
    assert body['metadata']['fallback_attempts'] == 1
print('PASS real key_2 replies after simulated 429 and 500')

path = base + f'/sessions/{first_session}/messages'
before = client.get(path).json()
failed = send(first_session, f'Fail this turn {run_id}', '*=429')
assert failed.status_code == 503 and failed.json() == {'detail':'all providers unavailable'}
assert client.get(path).json() == before, 'Failed request changed history'
assert client.get(base + f'/sessions/missing-{run_id}/messages').status_code == 404
assert client.post(base + '/chat', json={'session_id':first_session,'message':' '}).status_code == 422
assert client.post(base + '/chat', content='{bad', headers={'Content-Type':'application/json'}).status_code == 422
assert client.get(path).json() == before
print('PASS all-key failure, rollback, validation and unknown-session handling')

check_reply(send(first_session, 'Repeat the capital you just mentioned.'))
history = client.get(path).json()['messages']
assert [m['role'] for m in history] == ['user','assistant','user','assistant']
assert history[0]['content'] == message
assert history[1]['content'] == first['reply']
assert history[1]['metadata'] == first['metadata']
assert client.get(base + f'/sessions/live-{run_id}-cache/messages').json()['messages'][0]['content'] == message
print('PASS multi-turn history and session isolation')
print('Restart persistence must be checked after restarting the backend service.')
