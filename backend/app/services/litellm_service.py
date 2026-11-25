import hashlib, json, time
from pathlib import Path
from typing import Any
from litellm import completion, Cache
from ..config import settings

Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)
try:
    import litellm
    litellm.cache = Cache(type='disk', disk_cache_dir=settings.cache_dir)
except Exception as exc:
    print(f'[CACHE INIT] {type(exc).__name__}: {exc}', flush=True)

_response_cache: dict[str, dict[str, Any]] = {}
class AllProvidersUnavailable(Exception):
    pass

def _cache_key(messages):
    return hashlib.sha256(json.dumps({'models':[p['model'] for p in settings.providers], 'messages':messages}, sort_keys=True).encode()).hexdigest()

def _simulated_failures(header):
    out = {}
    for item in (header or '').split(','):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            try:
                code = int(value)
                if code in (429, 500, 502, 503): out[key.strip()] = code
            except ValueError: pass
    return out

def _estimate(messages, reply):
    return max(1, sum(len(str(m.get('content',''))) for m in messages)//4), max(1, len(reply)//4)

def generate(messages, failure_header=None):
    providers = settings.providers
    if not providers: raise AllProvidersUnavailable('No provider API keys configured')
    key = _cache_key(messages)
    if key in _response_cache:
        c = _response_cache[key]
        return {**c, 'latency_ms':1, 'key_id':None, 'fallback_attempts':0, 'resolution_source':'LLM_CACHE'}
    simulated = _simulated_failures(failure_header) if settings.enable_failure_simulation else {}
    start, last_error = time.perf_counter(), None
    for index, provider in enumerate(providers):
        fail = simulated.get('*') or simulated.get(provider['key_id'])
        if fail:
            last_error = RuntimeError(f"Simulated provider HTTP {fail}")
            print(f"[LLM FAILOVER] {provider['provider']} simulated {fail}", flush=True)
            continue
        try:
            response = completion(model=provider['model'], messages=messages, api_key=provider['api_key'], caching=True, timeout=30, max_retries=0)
            reply = response.choices[0].message.content or ''
            if not reply.strip(): raise RuntimeError('Empty provider response')
            usage = getattr(response, 'usage', None)
            est_in, est_out = _estimate(messages, reply)
            result = {'reply':reply, 'model':provider['model'], 'latency_ms':max(1,int((time.perf_counter()-start)*1000)),
                'input_tokens':int(getattr(usage,'prompt_tokens',0) or est_in), 'output_tokens':int(getattr(usage,'completion_tokens',0) or est_out),
                'key_id':provider['key_id'], 'fallback_attempts':index, 'resolution_source':'LIVE_INFERENCE'}
            _response_cache[key] = {k:result[k] for k in ('reply','model','input_tokens','output_tokens')}
            return result
        except Exception as exc:
            last_error = exc
            print(f"[LLM FAILOVER] {provider['provider']} {type(exc).__name__}: {exc}", flush=True)
    raise AllProvidersUnavailable() from last_error
