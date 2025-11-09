from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Replace USER, PASSWORD, HOST, PORT, DB with your Postgres info
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:demo123@localhost:5432/videos_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
