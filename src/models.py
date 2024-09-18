from pydantic import BaseModel

class VideoRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    url: str
    question: str
    chat_history: list

class ActionRequest(BaseModel):
    url: str
    action: str