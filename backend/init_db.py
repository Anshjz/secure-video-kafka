# init_db.py
from database import engine, Base
import models  # ensures models are imported so tables get registered

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Done!")
