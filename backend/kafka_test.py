from kafka import KafkaProducer, KafkaConsumer
import json

TOPIC_NAME = "video_topic"
BOOTSTRAP_SERVERS = "localhost:9092"

def send_to_kafka(video_data):
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    producer.send(TOPIC_NAME, video_data)
    producer.flush()
    producer.close()
    print("✅ Sent video metadata to Kafka")

def consume_from_kafka():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=[BOOTSTRAP_SERVERS],
        group_id='video_group',
        auto_offset_reset='earliest',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )

    print("🎥 Listening for messages...")
    for msg in consumer:
        print(f"Received: {msg.value}")

if __name__ == "__main__":
    # Example usage
    send_to_kafka({"filename": "test.mp4", "encrypted_path": "uploads/test.mp4.enc"})
    consume_from_kafka()
