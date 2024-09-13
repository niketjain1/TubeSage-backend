from pydantic import BaseModel

class VideoRequest(BaseModel):
    url: str

class QuestionRequest(BaseModel):
    url: str
    question: str
