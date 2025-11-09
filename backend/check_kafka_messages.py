from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "video_topic",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    enable_auto_commit=False
)

print("📡 Listening for Kafka messages...")
for msg in consumer:
    print(f"Received message — size: {len(msg.value)} bytes, headers: {msg.headers}")
