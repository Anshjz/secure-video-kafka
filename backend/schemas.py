# schemas.py
from pydantic import BaseModel
from datetime import datetime

class VideoBase(BaseModel):
    filename: str
    encrypted_path: str

class VideoCreate(VideoBase):
    pass

class VideoResponse(VideoBase):
    id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True
