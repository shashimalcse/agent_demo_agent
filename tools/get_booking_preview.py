from datetime import date
import json
import os
from typing import Type, Optional, Union
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from utils.state_manager import state_manager
from utils.constants import FlowState, FrontendState

from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager

class BookingPreviewToolInput(BaseModel):
    """Input schema for BookingPreviewTool."""
    room_id: Union[int, str] = Field(..., description="Room ID")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")


class BookingPreviewTool(BaseTool):
    name: str = "BookingPreviewTool"
    description: str = "Get booking preview."
    args_schema: Type[BaseModel] = BookingPreviewToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self, room_id: Union[int, str], check_in: date, check_out: date) -> str:
        try:

            if not room_id:
                raise Exception("room_id is required. If you don't have a room_id, you can fetch all rooms using the FetchHotelTool.")
            
            if not check_in:
                raise Exception("check_in is required. Uf you don't have a check_in date, you can find them is the chat context or ask the user for the check-in date.")
            
            if not check_out:
                raise Exception("check_out is required. Uf you don't have a check_out date, you can find them is the chat context or ask the user for the check-out date.")

            user_id = asgardeo_manager.get_user_id_from_thread_id(self.thread_id)

            authorization_url = asgardeo_manager.get_authorization_url(self.thread_id, user_id, ["openid", "create_bookings"])

            try: 
                access_token = asgardeo_manager.get_app_token(["read_rooms"])
            except Exception as e:
                raise Exception("Failed to get token. Retry the BookingPreview operation.")

            # Prepare the booking request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            booking_preview_data = {
                "room_id": room_id,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }

            try: 
                token = asgardeo_manager.get_app_token(["read_rooms"])
            except Exception as e:
                raise

            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            api_response = requests.post(f"{os.environ['HOTEL_API_BASE_URL']}/bookings/preview", json=booking_preview_data, headers=headers)
            
            if (api_response.status_code == 200):
                booking_preview = api_response.json()
                if booking_preview.get("is_available") == False:
                    raise Exception("Room not available for the selected dates. Please ask user to select different dates or room.")
                message = json.dumps(booking_preview)+ " Please confirm the booking"
                frontend_state = FrontendState.BOOKING_PREVIEW
                state_manager.add_state(self.thread_id, FlowState.BOOKING_PREVIEW_INITIATED)
            else:
                message = f"Failed to get booking preview: Please try the operation again"
                frontend_state = FrontendState.BOOKING_PREVIEW_ERROR

            response = Response(
                chat_response=message,
                tool_response={
                    "booking_preview": booking_preview,
                    "authorization_url": authorization_url
                }
            )
            return CrewOutput(response=response, frontend_state=frontend_state).model_dump_json()

        except Exception as e:
            error_response = Response(
                chat_response=f"{str(e)}",
                tool_response={},
            )
            return CrewOutput(response=error_response, frontend_state=FrontendState.BOOKING_PREVIEW_ERROR).model_dump_json()
