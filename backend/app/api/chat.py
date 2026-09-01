from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from google.genai import types
from app.rate_limit.service import RateLimitService
from app.observability.events import (
    status_event, tool_start_event, tool_result_event,
    generation_start_event, token_event, done_event, error_event,
    TOOL_MESSAGES,
)
from app.observability.logging import RequestContext
import hashlib
import json
import uuid

router = APIRouter()

runner = None
session_service = None
rate_limiter = None
APP_NAME = "medical_chat"


def init(r, ss):
    global runner, session_service, rate_limiter
    runner = r
    session_service = ss
    rate_limiter = RateLimitService()


class ChatRequest(BaseModel):
    msg: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    quota: dict | None = None


def _get_client_id(request: Request, session_id: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{ip}:{session_id}".encode()).hexdigest()[:16]


async def ensure_session(session_id: str):
    session = await session_service.get_session(
        app_name=APP_NAME, user_id="user", session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id="user", session_id=session_id
        )


def _quota_dict(state):
    return {
        "used": state.used,
        "limit": state.limit,
        "remaining": state.remaining,
        "reset_at": state.reset_at,
    }


@router.get("/sessions")
async def list_sessions():
    result = await session_service.list_sessions(app_name=APP_NAME, user_id="user")
    return [
        {
            "session_id": s.id,
            "last_update": s.last_update_time,
            "message_count": len(s.events) if s.events else 0,
        }
        for s in result.sessions
    ]


@router.get("/quota")
async def get_quota(request: Request, session_id: str = "default"):
    client_id = _get_client_id(request, session_id)
    state = rate_limiter.get_quota(client_id)
    return _quota_dict(state)


@router.post("/get", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    client_id = _get_client_id(request, session_id)

    quota_result = rate_limiter.check_and_increment(client_id, session_id)
    if not quota_result.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": quota_result.reason,
                **_quota_dict(quota_result.state),
            },
        )

    ctx = RequestContext(session_id=session_id)
    rate_limiter.mark_active(session_id)
    try:
        await ensure_session(session_id)
        content = types.Content(role="user", parts=[types.Part(text=body.msg)])

        final_text = ""
        async for event in runner.run_async(
            user_id="user", session_id=session_id, new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text

        ctx.log_complete()
        return ChatResponse(
            answer=final_text,
            session_id=session_id,
            quota=_quota_dict(quota_result.state),
        )
    finally:
        rate_limiter.mark_done(session_id)


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    client_id = _get_client_id(request, session_id)

    quota_result = rate_limiter.check_and_increment(client_id, session_id)
    if not quota_result.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": quota_result.reason,
                **_quota_dict(quota_result.state),
            },
        )

    rate_limiter.mark_active(session_id)
    await ensure_session(session_id)
    content = types.Content(role="user", parts=[types.Part(text=body.msg)])

    async def generate():
        ctx = RequestContext(session_id=session_id)
        tools_used = []
        generating = False

        try:
            yield status_event("Understanding your request…")

            async for event in runner.run_async(
                user_id="user", session_id=session_id, new_message=content
            ):
                if hasattr(event, "actions") and event.actions:
                    for action in event.actions.function_calls if hasattr(event.actions, "function_calls") and event.actions.function_calls else []:
                        tool_name = action.name if hasattr(action, "name") else str(action)
                        if tool_name not in tools_used:
                            tools_used.append(tool_name)
                            ctx.tools_used.append(tool_name)
                            message = TOOL_MESSAGES.get(tool_name, f"Using {tool_name}…")
                            yield tool_start_event(tool_name, message)

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            if not generating and event.is_final_response():
                                generating = True
                                yield generation_start_event()
                            yield token_event(part.text)

            ctx.log_complete()
            yield done_event(tools_used, _quota_dict(quota_result.state))
        except Exception as e:
            yield error_event(str(e))
        finally:
            rate_limiter.mark_done(session_id)

    return StreamingResponse(generate(), media_type="text/event-stream")
