"""LiteLLM owns provider calls, ordered fallbacks, and the response cache."""
import logging
import re

import litellm
from litellm import Router
from litellm.caching.caching import Cache

litellm.suppress_debug_info = True
logging.getLogger('LiteLLM').setLevel(logging.CRITICAL)
logging.getLogger('LiteLLM Router').setLevel(logging.CRITICAL)


class ProvidersUnavailable(Exception):
    pass


def parse_failure(value):
    failures = {}
    for part in value.split(','):
        match = re.fullmatch(r'\s*(key_[1-9]\d*|\*)\s*=\s*(429|500|502|503)\s*', part)
        if match:
            failures[match[1]] = int(match[2])
    return failures


class Gateway:
    def __init__(self, settings):
        self.settings = settings
        self.cache = Cache(type='local', ttl=settings.cache_ttl)

    def configured(self):
        return len(self.settings.keys) >= 2 and all(not k.startswith('replace_') for k in self.settings.keys)

    def deployments(self, failures):
        result = []
        for index, key in enumerate(self.settings.keys, 1):
            key_id = f'key_{index}'
            params = dict(model=self.settings.model, api_key=key, timeout=self.settings.timeout, max_retries=0)
            status = failures.get(key_id, failures.get('*'))
            if status:
                # LiteLLM raises this at its provider boundary; no credentials are
                # changed and the next deployment still makes a real LLM call.
                params['mock_response'] = 'litellm.RateLimitError' if status == 429 else 'litellm.InternalServerError'
            result.append(dict(model_name=key_id, litellm_params=params, model_info={'id':key_id}))
        return result

    async def answer(self, messages, failure_header=''):
        if not self.configured():
            raise ProvidersUnavailable()
        cache_args = dict(model=self.settings.model, messages=messages)
        cached = self.cache.get_cache(**cache_args)
        if cached:
            return {**cached, 'resolution_source':'LLM_CACHE', 'key_id':None, 'fallback_attempts':0}

        failures = parse_failure(failure_header) if self.settings.simulate else {}
        deployments = self.deployments(failures)
        ids = [d['model_name'] for d in deployments]
        router = Router(model_list=deployments, num_retries=0,
                        fallbacks=[{ids[0]:ids[1:]}],
                        max_fallbacks=len(ids)-1, disable_cooldowns=True,
                        cache_responses=False)
        try:
            response = await router.acompletion(model=ids[0], messages=messages)
            reply = response.choices[0].message.content
            if not reply or not reply.strip() or response.usage is None:
                raise ProvidersUnavailable()
            key_id = response._hidden_params.get('model_id')
            if key_id not in ids:
                raise ProvidersUnavailable()
            payload = dict(reply=reply, model=self.settings.model,
                           input_tokens=int(response.usage.prompt_tokens),
                           output_tokens=int(response.usage.completion_tokens))
            self.cache.add_cache(payload, **cache_args)
            return {**payload, 'resolution_source':'LIVE_INFERENCE',
                    'key_id':key_id, 'fallback_attempts':ids.index(key_id)}
        except Exception:
            # Provider errors can contain secrets. Never send or log their text.
            raise ProvidersUnavailable() from None
