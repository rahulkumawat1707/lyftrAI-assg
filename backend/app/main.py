import asyncio
from collections import OrderedDict
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import Settings
from .gateway import Gateway, ProvidersUnavailable
from .storage import Storage


class ChatRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=8000)

    @field_validator('session_id', 'message', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class SessionLocks:
    """Bounded idle lock pool; never evicts locks with active or waiting users."""
    def __init__(self):
        self.entries = OrderedDict()

    @asynccontextmanager
    async def hold(self, session_id):
        entry = self.entries.get(session_id)
        if entry is None:
            entry = [asyncio.Lock(), 0]
            self.entries[session_id] = entry
        entry[1] += 1
        self.entries.move_to_end(session_id)
        try:
            async with entry[0]:
                yield
        finally:
            entry[1] -= 1
            if len(self.entries) > 1024:
                for key, item in list(self.entries.items()):
                    if item[1] == 0:
                        del self.entries[key]
                    if len(self.entries) <= 1024:
                        break


def create_app(settings=None, gateway=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.storage = Storage(settings.database_url)
        app.state.gateway = gateway or Gateway(settings)
        app.state.locks = SessionLocks()
        yield

    app = FastAPI(title='Lyftr Chat API', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.origins),
                       allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type', 'X-Simulate-Failure'])

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return JSONResponse(status_code=503, content={'detail':'service temporarily unavailable'})

    @app.get('/health')
    async def health(request: Request):
        request.app.state.storage.healthy()
        if not request.app.state.gateway.configured():
            raise HTTPException(503, 'at least two LLM API keys must be configured')
        return {'status':'ok', 'keys_configured':len(settings.keys), 'cache_enabled':True}

    @app.post('/chat')
    async def chat(body: ChatRequest, request: Request, x_simulate_failure: str = Header(default='')):
        started = perf_counter()
        state = request.app.state
        async with state.locks.hold(body.session_id):
            prompt = body.system_prompt if body.system_prompt is not None else state.storage.session(body.session_id)
            prompt = prompt if prompt is not None else settings.system_prompt
            history = state.storage.messages(body.session_id)
            messages = [{'role':'system', 'content':prompt},
                        *[{'role':m['role'], 'content':m['content']} for m in history],
                        {'role':'user', 'content':body.message}]
            try:
                result = await state.gateway.answer(messages, x_simulate_failure)
            except ProvidersUnavailable:
                raise HTTPException(503, 'all providers unavailable') from None
            metadata = {k:v for k,v in result.items() if k != 'reply'}
            metadata['latency_ms'] = int((perf_counter()-started)*1000)
            state.storage.save_turn(body.session_id, prompt, body.message, result['reply'], metadata)
            return {'session_id':body.session_id, 'reply':result['reply'], 'metadata':metadata}

    @app.get('/sessions/{session_id}/messages')
    async def history(session_id: str, request: Request):
        storage = request.app.state.storage
        if storage.session(session_id) is None:
            raise HTTPException(404, 'session not found')
        return {'session_id':session_id, 'messages':storage.messages(session_id)}

    return app


app = create_app()
