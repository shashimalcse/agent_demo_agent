from datetime import date
import logging
import os
from typing import Type, Optional, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from utils.state_manager import state_manager
from utils.constants import FlowState, FrontendState

from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager

logger = logging.getLogger('agentLogger')

class FetchRoomToolInput(BaseModel):
    """Input schema for FetchRoomTool."""
    room_id: Union[int, str] = Field(..., description="Id of the room")

class FetchRoomTool(BaseTool):
    name: str = "FetchHotelTool"
    description: str = "Fetch a single room by id."
    args_schema: Type[BaseModel] = FetchRoomToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self, room_id: Union[int, str]) -> str:

        if not room_id:
            raise ValueError("room_id is required. If you don't have a room_id, you can fetch all rooms using the FetchHotelTool.")

        try: 
            scopes = ["read_rooms"]
            token = asgardeo_manager.get_app_token(scopes)
            logger.info(f"Successfully fetched token with scopes: {scopes} using agent credentials.")
        except Exception as e:
            raise Exception("Failed to get token. Retry the operation.")

        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        api_response = requests.get(f"{os.environ['HOTEL_API_BASE_URL']}/rooms/{room_id}", headers=headers)
        rooms_data = api_response.json()

        state_manager.add_state(self.thread_id, FlowState.FETCHED_ROOM)
        
        response = Response(
            chat_response=None, 
            tool_response=rooms_data
        )
        return CrewOutput(response=response, frontend_state=FrontendState.NO_STATE).model_dump_json()
