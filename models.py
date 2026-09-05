from pydantic import BaseModel
# Запрос клиент -> серверу
class MessageRequest(BaseModel):
    chat_ids: list[int]
    text: str
# Ответ сервер -> клиенту  
class MessageResponse(BaseModel):
    status: str
    message: str