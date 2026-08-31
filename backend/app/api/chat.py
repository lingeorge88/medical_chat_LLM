from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.genai import types
import json
import uuid

router = APIRouter()

runner = None
session_service = None
APP_NAME = "medical_chat"


def init(r, ss):
    global runner, session_service
    runner = r
    session_service = ss


class ChatRequest(BaseModel):
    msg: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str


async def ensure_session(session_id: str):
    session = await session_service.get_session(
        app_name=APP_NAME, user_id="user", session_id=session_id
    )
    if session is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id="user", session_id=session_id
        )


@router.post("/get", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    await ensure_session(session_id)

    content = types.Content(role="user", parts=[types.Part(text=request.msg)])

    final_text = ""
    async for event in runner.run_async(
        user_id="user", session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text

    return ChatResponse(answer=final_text, session_id=session_id)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    await ensure_session(session_id)

    content = types.Content(role="user", parts=[types.Part(text=request.msg)])

    async def generate():
        async for event in runner.run_async(
            user_id="user", session_id=session_id, new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        yield f"data: {json.dumps({'token': part.text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
