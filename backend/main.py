import os
import uuid
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer, KafkaConsumer
from cryptography.fernet import Fernet
from database import SessionLocal, engine
import models
from models import Video
from sqlalchemy.orm import Session

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

KAFKA_TOPIC = "video_topic"
KAFKA_SERVER = "localhost:9092"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Secure Video Upload + Streaming via Kafka"}


# ✅ FIXED upload_video()
@app.post("/upload")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save original uploaded file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Generate encryption key
    key = Fernet.generate_key()
    fernet = Fernet(key)
    key_base64 = base64.b64encode(key).decode()

    # Save metadata in DB
    video = Video(filename=file.filename, unique_filename=unique_filename, key_base64=key_base64)
    db.add(video)
    db.commit()
    db.refresh(video)

    # Encrypt + send to Kafka chunk by chunk
    producer = KafkaProducer(bootstrap_servers=KAFKA_SERVER)
    try:
        with open(file_path, "rb") as f:
            chunk_num = 0
            while chunk := f.read(1024 * 1024):  # 1MB
                chunk_num += 1
                encrypted_chunk = fernet.encrypt(chunk)
                producer.send(
                    KAFKA_TOPIC,
                    value=encrypted_chunk,
                    headers=[("filename", unique_filename.encode())]
                )
                print(f"✅ Sent encrypted chunk {chunk_num}")
        producer.flush()
        print(f"✅ Finished sending {chunk_num} chunks for {unique_filename}")
    finally:
        producer.close()

    return {"message": f"File {file.filename} encrypted & sent to Kafka!", "video_id": video.id}


# ✅ FIXED stream_video()
from fastapi import Request
from fastapi.responses import Response

@app.get("/stream")
def stream_video(filename: str, request: Request, db: Session = Depends(get_db)):
    video = db.query(Video).filter(
        (Video.filename == filename) | (Video.unique_filename == filename)
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    unique_filename = video.unique_filename
    key = base64.b64decode(video.key_base64)
    fernet = Fernet(key)

    # Write decrypted content temporarily to simulate byte serving
    temp_path = os.path.join(UPLOAD_DIR, f"{unique_filename}_temp.mp4")

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_SERVER,
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        group_id=None,
        consumer_timeout_ms=15000
    )

    # Reconstruct decrypted file
    with open(temp_path, "wb") as out_file:
        for msg in consumer:
            headers = {k.decode() if isinstance(k, bytes) else k: v for k, v in msg.headers}
            msg_filename = headers.get("filename", b"").decode()
            if msg_filename == unique_filename:
                try:
                    decrypted = fernet.decrypt(msg.value)
                    out_file.write(decrypted)
                except Exception as e:
                    print("decrypt error:", e)
                    continue
        consumer.close()

    file_size = os.path.getsize(temp_path)
    range_header = request.headers.get('range')
    start = 0
    end = file_size - 1

    if range_header:
        # Parse range: bytes=start-end
        range_match = range_header.strip().lower().replace("bytes=", "")
        start_end = range_match.split("-")
        if start_end[0]:
            start = int(start_end[0])
        if len(start_end) > 1 and start_end[1]:
            end = int(start_end[1])
        if end > file_size - 1:
            end = file_size - 1

    chunk_size = (end - start) + 1
    with open(temp_path, "rb") as video_file:
        video_file.seek(start)
        content = video_file.read(chunk_size)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }

    return Response(content, status_code=206 if range_header else 200, headers=headers)


@app.get("/videos")
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.uploaded_at.desc()).all()
    return [
        {
            "id": v.id,
            "filename": v.filename,
            "unique_filename": v.unique_filename,
            "key_base64": v.key_base64,
            "uploaded_at": v.uploaded_at,
        }
        for v in videos
    ] 

@app.delete("/delete/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}

