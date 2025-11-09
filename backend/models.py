from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)          # original filename
    unique_filename = Column(String, nullable=False)   # unique name for Kafka
    key_base64 = Column(String, nullable=False)        # Fernet key in Base64
    uploaded_at = Column(DateTime, default=datetime.utcnow)
