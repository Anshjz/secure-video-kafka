# backend/app.py
import os
import uuid
import base64
import json
import time
import queue
import threading
import psycopg2
from typing import AsyncGenerator
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from kafka import KafkaProducer, KafkaConsumer

# ---------------- CONFIG ----------------
KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "video-chunks"
CHUNK_SIZE = 1024 * 1024  # 1MB
ENCRYPTED_STORE = "./encrypted_store"
os.makedirs(ENCRYPTED_STORE, exist_ok=True)

# Postgres connection (container has Postgres at localhost:5432 mapped)
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "videosdb"
PG_USER = "demo"
PG_PASS = "demopw"  # use the password you set in docker-compose (demo123 or demopw as used)

# ---------------- APP ----------------
app = FastAPI(title="Secure Video Upload + Kafka")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Postgres helper ----------------
def pg_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS
    )

def save_metadata(video_id: str, filename: str, key_b64: str):
    conn = pg_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO videos (id, filename, key_base64) VALUES (%s, %s, %s)",
        (video_id, filename, key_b64),
    )
    conn.commit()
    cur.close()
    conn.close()

def get_metadata(video_id: str):
    conn = pg_conn()
    cur = conn.cursor()
    cur.execute("SELECT filename, key_base64 FROM videos WHERE id = %s", (video_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row  # (filename, key_base64) or None

# ---------------- Encryption helpers ----------------
def generate_key():
    return AESGCM.generate_key(bit_length=256)

def encrypt_chunk(key: bytes, plaintext: bytes):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 12 bytes nonce recommended for AESGCM
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext

def decrypt_chunk(key: bytes, nonce: bytes, ciphertext: bytes):
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

# ---------------- Kafka producer singleton ----------------
producer = KafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)

# ---------------- Upload endpoint ----------------
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # create id & key
    video_id = str(uuid.uuid4())
    key = generate_key()
    key_b64 = base64.b64encode(key).decode()
    filename = file.filename
    enc_path = os.path.join(ENCRYPTED_STORE, f"{video_id}.enc")

    # save metadata to Postgres
    save_metadata(video_id, filename, key_b64)

    # read file in chunks, encrypt and produce to Kafka
    chunk_index = 0
    async with aiofiles.open(enc_path, "wb") as f:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            nonce, ciphertext = encrypt_chunk(key, chunk)

            # store encrypted on disk (optional: nonce + len + ciphertext)
            await f.write(nonce)
            await f.write(len(ciphertext).to_bytes(4, "big"))
            await f.write(ciphertext)

            # send to kafka as JSON bytes (base64 fields)
            msg = {
                "video_id": video_id,
                "chunk_index": chunk_index,
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ciphertext).decode(),
            }
            producer.send(KAFKA_TOPIC, json.dumps(msg).encode())
            chunk_index += 1

    producer.flush()
    return {"video_id": video_id, "filename": filename, "chunks": chunk_index}

# ---------------- Streaming endpoint ----------------
@app.get("/stream/{video_id}")
async def stream_video(video_id: str):
    meta = get_metadata(video_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Video not found")
    filename, key_b64 = meta
    key = base64.b64decode(key_b64)

    # kafka consumer (will read from beginning)
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=5000,  # stop if no messages for a while
    )

    # We will create a thread that reads Kafka and places decrypted chunks into queue,
    # and an async generator will yield from the queue.
    q: "queue.Queue[bytes]" = queue.Queue(maxsize=10)
    stop_flag = threading.Event()

    def consume_and_decrypt():
        try:
            for msg in consumer:
                try:
                    j = json.loads(msg.value.decode())
                except Exception:
                    continue
                if j.get("video_id") != video_id:
                    continue
                nonce = base64.b64decode(j["nonce"])
                ciphertext = base64.b64decode(j["ciphertext"])
                try:
                    plain = decrypt_chunk(key, nonce, ciphertext)
                except Exception:
                    # ignore bad chunk
                    continue
                # put into queue (blocks if full)
                q.put(plain)
            # no more messages -> signal end
        finally:
            stop_flag.set()
            consumer.close()

    t = threading.Thread(target=consume_and_decrypt, daemon=True)
    t.start()

    async def generator() -> AsyncGenerator[bytes, None]:
        # yield until consumer finished and queue empty
        while not (stop_flag.is_set() and q.empty()):
            try:
                chunk = q.get(timeout=1)
                yield chunk
            except queue.Empty:
                # loop to check stop_flag again
                await asyncio_sleep(0.1)
                continue

    # helper async sleep without importing asyncio directly in top-level
    import asyncio
    async def asyncio_sleep(s):
        await asyncio.sleep(s)

    return StreamingResponse(generator(), media_type="video/mp4")
