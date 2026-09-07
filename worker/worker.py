import os
import json
import time
import pika
from datetime import datetime, timezone
from pymongo import MongoClient
from netmiko import ConnectHandler


def get_mongo_collection():
    mongo_uri = os.environ.get("MONGO_URI")
    db_name = os.environ.get("DB_NAME")
    client = MongoClient(mongo_uri)
    db = client[db_name]
    return db["interface_status"]


def ssh_and_get_interfaces(ip, username, password):
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "timeout": 10,
    }
    with ConnectHandler(**device) as conn:
        output = conn.send_command("show ip interface brief", use_textfsm=True)
    return output  # list of dict อัตโนมัติ


def store_to_mongo(collection, ip, interfaces):
    timestamp = datetime.now(timezone.utc)
    document = {
        "router_ip": ip,
        "timestamp": timestamp,
        "interfaces": interfaces,
    }
    collection.insert_one(document)
    print(f"Stored interface status for {ip}")


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        ip = data["ip"]
        username = data["username"]
        password = data["password"]

        print(f"Received job for router {ip}")
        interfaces = ssh_and_get_interfaces(ip, username, password)
        print(json.dumps(interfaces, indent=2))

        collection = get_mongo_collection()
        store_to_mongo(collection, ip, interfaces)

        # ถ้ารันมาถึงตรงนี้แปลว่าสำเร็จ ค่อยส่ง Ack
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error processing job: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def worker():
    RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
    RABBITMQ_USER = os.environ.get("RABBITMQ_USER")
    RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS")

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)

    connection = None
    for attempt in range(10):
        try:
            print(f"Connecting to RabbitMQ (try {attempt})...")
            connection = pika.BlockingConnection(parameters)
            break
        except Exception as e:
            print(f"Failed: {e}")
            time.sleep(3)

    if connection is None:
        print("Could not connect to RabbitMQ. Exiting.")
        return

    channel = connection.channel()

    channel.exchange_declare(exchange="jobs", exchange_type="direct")
    channel.queue_declare(queue="router_jobs")
    channel.queue_bind(
        queue="router_jobs", exchange="jobs", routing_key="check_interfaces"
    )

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="router_jobs", on_message_callback=callback)

    print("Worker is waiting for jobs...")
    channel.start_consuming()


if __name__ == "__main__":

    worker()
