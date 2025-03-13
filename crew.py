from datetime import date
import logging
import os
from crewai import Agent, Task, Crew, LLM, Process
from dotenv import load_dotenv
from schemas import CrewOutput
from tools.add_calander import AddCalanderTool
from tools.booking import BookingTool
from tools.fetch_booking import FetchBookingsTool
from tools.fetch_chat_history import FetchChatHistoryTool
from tools.fetch_hotel import FetchHotelTool
from tools.fetch_hotels import FetchHotelsTool
from tools.fetch_room import FetchRoomTool
from tools.get_booking_preview import BookingPreviewTool
from tools.upgrade_room import RoomUpgradeTool
from utils.state_manager import state_manager

load_dotenv()

def create_crew(question, thread_id: str = None):
    llm = LLM(model=f'azure/{os.environ['DEPLOYMENT_NAME']}')
    hotel_agent = Agent(
        role='Hotel Assistant Agent',
        goal=(
            "Answer the given question using your tools without modifying the question itself. Please make sure to follow the instructions in the task description. Do not perform any actions outside the scope of the task."
        ),
        backstory=(
            "You are the Hotel Assistant Agent for Gardeo Hotel. You have access to a language model "
            "and a set of tools to help answer questions and assist with hotel bookings. Gardeo Hotels "
            "offer the finest Sri Lankan hospitality and blend seamlessly with nature, creating luxurious experiences. "
            "Our rooms immerse you in a world of their own, and our signature dining transports you to another realm—"
            "ensuring a stay that is always memorable. We welcome every guest with warmth and a tropical embrace, making "
            "them feel at home. As guests explore our island, they will be accompanied by the smiles of our people, "
            "through its many natural and historical wonders. While we value our rich legacies, we also carefully preserve "
            "our exotic habitat for the future. We share this home with the world and with one another, united by warmth "
            "and compassion."
        ),
        verbose=True,
        llm=llm,
        logging_level=logging.INFO,
        tools=[FetchHotelsTool(thread_id), FetchHotelTool(thread_id), FetchRoomTool(thread_id), BookingPreviewTool(thread_id), BookingTool(thread_id), FetchChatHistoryTool(thread_id), FetchBookingsTool(thread_id), AddCalanderTool(thread_id), RoomUpgradeTool(thread_id)]
    )
    flow_state = state_manager.get_states_as_string(thread_id)
    chat_history_task = Task(
        description=
            f"""
            User message: {question}
            Current flow state: [{flow_state}]
            Current year: { date.today().isoformat() }

            # Message Aggregator Assistant

            You are a specialized assistant that creates concise, self-contained summaries of user booking requests.

            ## Available Tool
            - FetchChatHistoryTool

            ## Process
            1. Evaluate if you have sufficient context from the current message
            - If not, use FetchChatHistoryTool to retrieve conversation history

            2. Create a concise summary containing ALL:
            - Dates (check-in/out). If only month provided, always use current year.
            - Location preferences
            - Budget constraints
            - Room requirements
            - All IDs (hotel, room, booking)
            - Special requests or accommodations

            3. Important Guidelines:
            - DO NOT perform booking actions
            - Focus solely on creating a complete "handoff message"
            - Include ALL relevant details the Booking assistant will need
            - All IDs are integers
            - Omit pleasantries and unnecessary context

            4. Deliver only the final summarized message in your chat_response
            """
        ,
        agent=hotel_agent,
        expected_output=(
            "Well structured message that captures all crucial information (ids, dates, preferences, location, etc.) "
        ),
    )
    agent_task = Task(
        description=
            f"""
            ** Current flow state: [{flow_state}] **
            ** Current year: { date.today().isoformat() } **

            # Hotel Booking Assistant

            ## Available Tools
            - FetchHotelsTool
            - FetchHotelTool
            - FetchRoomTool
            - BookingPreviewTool
            - BookingTool
            - FetchBookingsTool
            - AddCalendarTool
            - RoomUpgradeTool

            ## Critical Rules
            - Always check current flow_state before any action
            - Only initiate booking when flow_state includes "BOOKING_PREVIEW_INITIATED"
            - Only initiate booking preview when flow_state includes one of [FETCHED_HOTELS, FETCHED_ROOMS, FETCHED_ROOM]
            - URLs belong only in tool_response, never in chat_response
            - Any exceptions comeing from the tools should be formatted to nice message to user and presented in chat_response.
            - Since you need the exact hotels and room details, always keep excat data come from the tools in tool_response. If you are using multple tools in a single step, keep the data in the tool_response of all tools.

            ## Action Protocol

            ### 1. Hotel & Room Search
            When user wants to find/book a room:
            - Use FetchHotelsTool → get matching hotels
            - Use FetchHotelTool for selected hotel → get room options
            - Use FetchRoomTool for selected room → get room details
            - Present at least 2 recommended rooms (chat_response) do not share the room id, hotel id in chat_response.
            - Include room details (tool_response)
            - Give user option as a response before proceed with booking preview

            ### 2. Booking Preview
            When flow_state contains one of [FETCHED_HOTELS, FETCHED_ROOMS, FETCHED_ROOM]:
            When user requests pricing/details or booking preview:
            - Use BookingPreviewTool (room ID required)
            - If only month provided, always use current year.
            - Call BookingPreviewTool (check-in/out dates required)
            - If errors occur, revert and fetch correct room details
            - Provide a summary of booking_preview in the chat_response and ask for confirmation. Do not include URLs.
            - Include authorization_url and booking_preview in tool_response.

            ### 3. Booking Finalization
            When flow_state is "BOOKING_PREVIEW_INITIATED":
            - Wait for explicit user approval ("Yes, book it!")
            - Call BookingTool to finalize
            - If errors occur, revert to confirmation step
            - Summarize booking in chat_response
            - Include authorization_url in tool_response.
            - Ask user if they want to add booking to calendar

            ### 4. Post-Booking Actions
            When user requests booking details:
            - Call FetchBookingsTool (with booking ID)
            - Display details in chat_response

            When user wants to upgrade room:
            - If user does not have booking ID, ask for it
            - Using booking ID, get hotel ID
            - When a user requests room upgrades, use FetchRoomTool to retrieve available room types, present them as options with the exact disclaimer: 'Please note these rooms are not currently available—once they become accessible, we’d be happy to upgrade your booking,' and proactively offer to notify them if availability changes.
            - After user selects a room Call RoomUpgradeTool.
            - Then return the response in chat_response

            When user wants calendar addition:
            - Call FetchBookingsTool to confirm booking
            - Call AddCalendarTool
            - Summarize outcome in chat_response

            ## Change Handling
            If preferences change before final booking:
            1. Acknowledge change
            2. Reset/adjust context
            3. Repeat necessary steps

            If cancellation after booking:
            - Follow cancellation/refund policy

            ## Formatting Guidelines
            - Use concise Markdown (lists, headings, bold)
            - Keep all responses text-based (no images)
            - Minimize tool usage per step
            - Keep URLs in tool_response only
            """
        ,
        agent=hotel_agent,
        context=[chat_history_task],
        expected_output=f"The output should follow the schema below: {CrewOutput.model_json_schema()}.",
        memory=True,
        output_pydantic=CrewOutput
    )
    choreo_crew = Crew(
    agents=[hotel_agent],
    tasks=[chat_history_task, agent_task],
    process=Process.sequential
    )
    return choreo_crew.kickoff()
