from typing import Optional
from pydantic import BaseModel, Field
from datetime import date

from utils.constants import FrontendState

class Response(BaseModel):
    chat_response: Optional[str] = Field(default=None, description="This should include the response of the chat.")
    tool_response: Optional[dict] = Field(default=None, description="This should include the response of the tool. Only set if the tool retruns json response.")

class CrewOutput(BaseModel):
    """
    Output schema for CrewOutput.

    Attributes
    ----------
    response : Response
        This should include the response of the crew.
    frontend_state : str
        This should include the frontend state come from the tool.
    """
    response: Response = Field(..., description="This should include the response of the crew.")
    frontend_state: FrontendState = Field(..., description="This should include the frontend state come from the tool.")
