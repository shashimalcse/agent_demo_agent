from datetime import date
import os
from typing import Type, Optional, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from utils.state_manager import state_manager
from utils.constants import FlowState, FrontendState

from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager

class FetchBookingsToolInput(BaseModel):
    """Input schema for FetchBookingsTool."""
    booking_id: Union[int, str] = Field(..., description="Id of the booking")

class FetchBookingsTool(BaseTool):
    name: str = "FetchBookingsTool"
    description: str = "Fetch a booking by id."
    args_schema: Type[BaseModel] = FetchBookingsToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self, booking_id: Union[int, str]) -> str:

        try: 
            token = asgardeo_manager.get_app_token(["read_bookings"])
        except Exception as e:
            raise Exception("Failed to get token. Retry the operation.")

        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        api_response = requests.get(f"{os.environ['HOTEL_API_BASE_URL']}/bookings/{booking_id}", headers=headers)
        rooms_data = api_response.json()

        state_manager.add_state(self.thread_id, FlowState.FETCHED_BOOKINGS)
        
        response = Response(
            chat_response=None, 
            tool_response=rooms_data
        )
        return CrewOutput(response=response, frontend_state=FrontendState.NO_STATE).model_dump_json()
