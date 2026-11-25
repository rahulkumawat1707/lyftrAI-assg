"""List supported Gemini model identifiers without printing credentials."""
from pathlib import Path
import httpx
from dotenv import dotenv_values

values = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
key = values['LLM_API_KEYS'].split(',')[0].strip()
response = httpx.get('https://generativelanguage.googleapis.com/v1beta/models', headers={'x-goog-api-key':key}, timeout=30)
print('Model listing status:', response.status_code)
if response.is_success:
    for model in response.json().get('models', []):
        if 'generateContent' in model.get('supportedGenerationMethods', []):
            print(model['name'])
