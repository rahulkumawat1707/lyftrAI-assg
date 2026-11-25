import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./data/app.db')
    keys: tuple = tuple(k.strip() for k in os.getenv('LLM_API_KEYS', '').split(',') if k.strip())
    model: str = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
    origins: tuple = tuple(x.strip() for x in os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',') if x.strip())
    simulate: bool = os.getenv('ENABLE_FAILURE_SIMULATION', 'false').lower() == 'true'
    system_prompt: str = os.getenv('DEFAULT_SYSTEM_PROMPT', 'You are a helpful, clear and concise assistant.')
    timeout: float = float(os.getenv('LLM_TIMEOUT_SECONDS', '25'))
    cache_ttl: int = int(os.getenv('CACHE_TTL_SECONDS', '3600'))
