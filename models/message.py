from pydantic import BaseModel
from typing import List


class MessageRequest(BaseModel):
    text: str
    chat_ids: List[str]


class MessageResponse(BaseModel):
    status: str
    message: str
