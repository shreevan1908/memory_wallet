from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str

class TextToAudio(BaseModel):
    text: str