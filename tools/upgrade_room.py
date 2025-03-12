from datetime import date
import logging
import os
from typing import Type, Optional, Union
import threading
import time
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from utils.state_manager import state_manager
from utils.email_manager import email_manager
from utils.constants import FlowState, FrontendState
import requests
from schemas import CrewOutput, Response
from utils.asgardeo_manager import asgardeo_manager

class RoomUpgradeToolInput(BaseModel):
    """Input schema for RoomUpgradeTool."""
    booking_id: Union[int, str] = Field(..., description="Id of the hotel")
    room_id: Union[int, str] = Field(..., description="Id of the room")

class RoomUpgradeTool(BaseTool):
    name: str = "RoomUpgradeTool"
    description: str = "Fetche a single hotel by id."
    args_schema: Type[BaseModel] = RoomUpgradeToolInput
    thread_id: Optional[str] = None

    def __init__(self, thread_id: str = None):
        super().__init__()
        self.thread_id = thread_id
    
    def _process_upgrade_in_background(self, booking_id: Union[int, str], room_id : Union[int, str]):
        """Process the room upgrade request in background."""
        try:
            time.sleep(30)
            auth_req_id = asgardeo_manager.initiate_ciba(self.thread_id, ["openid", "booking_upgrade"])
            # Poll for token with retries
            max_retries = 60
            retry_interval = 15  # Set to 15 seconds
            retries = 0
            time.sleep(retry_interval)
            
            while retries < max_retries:
                response = asgardeo_manager.get_ciba_token(auth_req_id)
                if response.get("state") == "success":
                    # Upgrade room with the obtained token
                    access_token = response.get("access_token")
                    user_id = asgardeo_manager.get_user_id_from_thread_id(self.thread_id)
                    user_claims = asgardeo_manager.get_user_claims(user_id)
                    username = user_claims.get("username")
                    email = user_claims.get("email")
                    email_content = self.get_email(booking_id, room_id, username)
                    email_manager.send_html_email(email, "Room Upgrade", email_content)
                    print(f"Upgrading room with booking_id: {booking_id}")
                    return
                
                elif response.get("state") == "pending" or response.get("state") == "slow_down":
                    # Continue polling
                    print("Polling for token...")
                    retries += 1
                    time.sleep(retry_interval)  # Sleep for 15 seconds
                    continue
                
                else:
                    print(f"Failed to get token for booking_id: {booking_id}")
                    return
        
            
        except Exception as e:
            print(f"Error in background thread: {str(e)}")

    def get_email(self, booking_id: Union[int, str], room_id : Union[int, str], username: str) -> str:        

        try: 
            token = asgardeo_manager.get_app_token(["read_bookings"])
        except Exception as e:
            raise Exception("Failed to get token. Retry the operation.")

        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        api_response = requests.get(f"{os.environ['HOTEL_API_BASE_URL']}/bookings/{booking_id}", headers=headers)
        rooms_data = api_response.json()
        booking_preview_data = {
            "room_id": room_id,
            "check_in": rooms_data.get("check_in"),
            "check_out": rooms_data.get("check_out")
        }
        try: 
            token = asgardeo_manager.get_app_token(["read_rooms"])
        except Exception as e:
            raise

        headers = {
            'Authorization': f'Bearer {token}'
        }
        api_response = requests.post(f"{os.environ['HOTEL_API_BASE_URL']}/bookings/preview", json=booking_preview_data, headers=headers)
        booking_preview_data = api_response.json()
        html = f"<h1>Room Upgrade</h1><p>Dear {username},</p><p>Your room upgrade request has been successfully processed. Your new room details are as follows:</p><p>Room Type: {booking_preview_data.get('room_type')}</p><p>Price: {booking_preview_data.get('total_price')}</p><p>Check-in: {booking_preview_data.get('check_in')}</p><p>Check-out: {booking_preview_data.get('check_out')}</p><p>Thank you for choosing our hotel.</p>"
        return html

    def _run(self, booking_id: Union[int, str], room_id: Union[int, str]) -> str:
        if not booking_id:
            raise ValueError("booking_id is required. If you don't have a booking_id, you need to create a booking first.")
        
        # Start a background thread for processing
        bg_thread = threading.Thread(
            target=self._process_upgrade_in_background,
            args=(booking_id, room_id),
            daemon=True
        )
        bg_thread.start()
        state_manager.add_state(self.thread_id, FlowState.PROCCESING_UPGRADE)
        response = Response(
            chat_response="Currently, the room you've requested is not available. As soon as it becomes available, we will upgrade your reservation and notify you via email.", 
            tool_response={"status": "processing", "booking_id": booking_id}
        )
        
        return CrewOutput(response=response, frontend_state=FrontendState.PROCCESING_UPGRADE).model_dump_json()
