#config.py
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "events"
KAFKA_GROUP_ID = "my-group"

#kafka producer.py
import json
from aiokafka import AIOKafkaProducer
from app.config import KAFKA_BOOTSTRAP_SERVERS

producer = None

async def start_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
    )
    await producer.start()

async def stop_producer():
    await producer.stop()

async def send_event(topic: str, data: dict):
    await producer.send_and_wait(
        topic,
        json.dumps(data).encode("utf-8")
    )


#consumer.py

import json
import asyncio
from aiokafka import AIOKafkaConsumer
from app.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_GROUP_ID

consumer = None

async def start_consumer():
    global consumer
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True
    )
    await consumer.start()

    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
            print(f"Received: {data}")
            # process_event(data)
    finally:
        await consumer.stop()    



#main.py
from fastapi import FastAPI
import asyncio
from app.kafka_producer import start_producer, stop_producer, send_event
from app.kafka_consumer import start_consumer
from app.config import KAFKA_TOPIC

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await start_producer()
    asyncio.create_task(start_consumer())  # background consumer

@app.on_event("shutdown")
async def shutdown_event():
    await stop_producer()

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/publish")
async def publish_event(payload: dict):
    await send_event(KAFKA_TOPIC, payload)
    return {"message": "Event sent"}