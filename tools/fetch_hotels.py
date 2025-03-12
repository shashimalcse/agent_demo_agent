from datetime import date
import logging
import os
from typing import Type, Optional, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from utils.constants import FlowState, FrontendState

from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager
from utils.state_manager import state_manager

logger = logging.getLogger('agentLogger')

class FetchHotelsToolInput(BaseModel):
    """Input schema for FetchHotelsTool."""

class FetchHotelsTool(BaseTool):
    name: str = "FetchHotelsTool"
    description: str = "Fetches all hotels."
    args_schema: Type[BaseModel] = FetchHotelsToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self) -> str:
        try: 
            scopes = ["read_hotels"]
            token = asgardeo_manager.get_app_token(scopes)
            logger.info(f"Successfully fetched token with scopes: {scopes} using agent credentials.")
        except Exception as e:
            raise Exception("Failed to get token. Retry the operation.")

        headers = {
            'Authorization': f'Bearer {token}'
        }
        api_response = requests.get(f"{os.environ['HOTEL_API_BASE_URL']}/hotels", headers=headers)
        hotels_data = api_response.json()

        state_manager.add_state(self.thread_id, FlowState.FETCHED_HOTELS)
        response = Response(
            chat_response=None, 
            tool_response=hotels_data
        )
        return CrewOutput(response=response, frontend_state=FrontendState.NO_STATE).model_dump_json()
