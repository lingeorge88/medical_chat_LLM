from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from app.agent.agent import root_agent
from app.sessions.service import create_session_service
from app.api import chat, health
from app import config
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_service = create_session_service()
    runner = Runner(
        agent=root_agent,
        app_name="medical_chat",
        session_service=session_service,
    )
    chat.init(runner, session_service)
    print(f"ADK agent ready (env={config.ENVIRONMENT})")
    yield


app = FastAPI(title="Medical Lab Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)

frontend_build = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
if os.path.isdir(frontend_build):
    app.mount("/", StaticFiles(directory=frontend_build, html=True), name="static")
