from datetime import date
from typing import Type, Optional, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from utils.chat_history import chat_history_manager, ChatHistory

from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager

class FetchChatHistoryToolInput(BaseModel):
    """Input schema for FetchChatHistoryTool."""

class FetchChatHistoryTool(BaseTool):
    name: str = "FetchChatHistoryTool"
    description: str = "Fetches all hotels."
    args_schema: Type[BaseModel] = FetchChatHistoryToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self) -> str:

        chat_history: ChatHistory = chat_history_manager.get_chat_history(self.thread_id)
        return chat_history.get_messages_as_string()
