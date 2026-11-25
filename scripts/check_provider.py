"""Print only safe status diagnostics. Never print provider exception bodies."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import Settings
from backend.app.gateway import Gateway


async def main():
    settings = Settings()
    if len(sys.argv) > 1:
        settings.model = sys.argv[1]
    for index, key in enumerate(settings.keys, 1):
        import litellm
        try:
            r = await litellm.acompletion(model=settings.model, api_key=key,
                messages=[{'role':'user','content':'Reply with the single word hello.'}],
                max_retries=0, timeout=25)
            print({'key_id':f'key_{index}','ok':True,'model':r.model,'input_tokens':r.usage.prompt_tokens})
        except Exception as e:
            print({'key_id':f'key_{index}','ok':False,'error_type':type(e).__name__,'status':getattr(e,'status_code',None)})
            # Print only the provider's public error message after removing all
            # configured credentials. Never print exception or request objects.
            text = str(e)
            for secret in settings.keys:
                text = text.replace(secret, '[REDACTED]')
            import re
            text = re.sub(r'AIza[\w-]+', '[REDACTED]', text)
            text = re.sub(r'https?://\S+', '[URL]', text)
            print(text[:700])


asyncio.run(main())
