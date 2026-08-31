from google.adk.sessions import InMemorySessionService
from app import config


def create_session_service():
    return InMemorySessionService()
