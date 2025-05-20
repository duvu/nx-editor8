#!/usr/bin/env python3
import os
import pika
import argparse
import sys
from dotenv import load_dotenv


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Skip messages in RabbitMQ queue')
    parser.add_argument('-n', type=int, default=1, help='Number of messages to skip (default: 1)')
    args = parser.parse_args()

    # Get RabbitMQ connection parameters from environment variables
    host = os.environ.get('RABBITMQ_HOST', 'localhost')
    port = int(os.environ.get('RABBITMQ_PORT', '5672'))
    user = os.environ.get('RABBITMQ_USER', 'guest')
    password = os.environ.get('RABBITMQ_PASS', 'guest')
    vhost = os.environ.get('RABBITMQ_VHOST', '/')
    queue_name = os.environ.get('INPUT_QUEUE', 'nx_01_ai_queue')

    print(f"Connecting to RabbitMQ at {host}:{port}, vhost: {vhost}")
    print(f"Will skip {args.n} messages from queue: {queue_name}")

    # Connect to RabbitMQ
    credentials = pika.PlainCredentials(user, password)
    connection_params = pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=vhost,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        # Check if queue exists and get message count
        try:
            queue_info = channel.queue_declare(queue=queue_name, passive=True)
            message_count = queue_info.method.message_count
            print(f"Queue '{queue_name}' has {message_count} messages")
        except pika.exceptions.ChannelClosedByBroker:
            print(f"Queue '{queue_name}' does not exist")
            connection.close()
            return

        skipped = 0
        for i in range(args.n):
            method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=False)
            if method_frame:
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                skipped += 1
                print(f"Skipped message {i+1}/{args.n}")
            else:
                print(f"No more messages in queue. Skipped {skipped} messages.")
                break

        if skipped == args.n:
            print(f"Successfully skipped {skipped} messages from queue '{queue_name}'")

        connection.close()

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Failed to connect to RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
