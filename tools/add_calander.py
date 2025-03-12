from datetime import date, timedelta
import os
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests

from schemas import CrewOutput, Response
from utils.state_manager import state_manager
from utils.asgardeo_manager import asgardeo_manager
from utils.constants import FlowState, FrontendState

class AddCalanderToolInput(BaseModel):
    """Input schema for AddCalanderTool."""
    title: str = Field(..., description="Title of the booking")
    start: date = Field(..., description="Start date of the booking")
    end: date = Field(..., description="End date of the booking")

class AddCalanderTool(BaseTool):
    name: str = "AddCalanderTool"
    description: str = "Adds a booking to the calander."
    args_schema: Type[BaseModel] = AddCalanderToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id

    def _run(self, title: str, start: date, end: date) -> str:
        try:
            # Get the access token for authentication
            user_id = asgardeo_manager.get_user_id_from_thread_id(self.thread_id)
            access_token = asgardeo_manager.get_user_google_token(user_id, ["openid", "create_bookings"])

            # Format dates as 'YYYY-MM-DD'
            start_date = start.isoformat()
            # Add 1 day to end date since Google Calendar's end.date is exclusive
            end_date = (end + timedelta(days=1)).isoformat()

            # Construct the event body
            event = {
                "summary": title,
                "start": {"date": start_date},
                "end": {"date": end_date}
            }

            # Set up headers with the access token
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            # Make the API request
            response = requests.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers=headers,
                json=event
            )

            # Check the response
            if response.status_code == 200:
                message = f"Event created successfully in your calendar"
                frontend_state = FrontendState.ADDED_TO_CALENDAR
                state_manager.add_state(self.thread_id, FlowState.ADDED_TO_CALENDAR)
            else:
                message = "An error occurred while adding the event to the calendar. Please try the Add to Calendar tool again."
                frontend_state = FrontendState.CALENDAR_ERROR
                
            response = Response(
                chat_response=message,
                tool_response={}
            )
            return CrewOutput(response=response, frontend_state=frontend_state).model_dump_json()

        except requests.exceptions.RequestException as e:
            error_response = Response(
                chat_response=f"An error occurred while adding the event to the calendar, please try again.",
                tool_response={}
            )
            return CrewOutput(response=error_response, frontend_state=FrontendState.CALENDAR_ERROR).model_dump_json()
        except Exception as e:
            error_response = Response(
                chat_response=f"An error occurred while adding the event to the calendar, please try again.",
                tool_response={}
            )
            return CrewOutput(response=error_response, frontend_state=FrontendState.CALENDAR_ERROR).model_dump_json()


