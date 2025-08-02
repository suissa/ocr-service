import pika
import json

class RabbitMQClient:
    def __init__(self, uri):
        self.connection = pika.BlockingConnection(pika.URLParameters(uri))
        self.channel = self.connection.channel()

    def publish_event(self, exchange, routing_key, message, headers={}):
        self.channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(headers=headers, delivery_mode=2)
        )

    def subscribe_to_event(self, exchange, queue, routing_key, handler):
        self.channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)
        self.channel.queue_declare(queue=queue, durable=True,
                                   arguments={'x-dead-letter-exchange': f'{exchange}.dlq'})
        self.channel.queue_bind(exchange=exchange, queue=queue, routing_key=routing_key)

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                handler(payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(queue=queue, on_message_callback=callback)

    def publish_to_fanout(self, exchange, message):
        self.channel.exchange_declare(exchange=exchange, exchange_type='fanout', durable=True)
        self.channel.basic_publish(exchange=exchange, routing_key='', body=json.dumps(message))

    def subscribe_to_fanout(self, exchange, handler):
        self.channel.exchange_declare(exchange=exchange, exchange_type='fanout', durable=True)
        result = self.channel.queue_declare(queue='', exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange=exchange, queue=queue_name)

        def callback(ch, method, properties, body):
            payload = json.loads(body)
            handler(payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=queue_name, on_message_callback=callback)

    def handle_dead_letter(self, dlq_exchange, dlq_queue, handler):
        self.channel.exchange_declare(exchange=dlq_exchange, exchange_type='fanout', durable=True)
        self.channel.queue_declare(queue=dlq_queue, durable=True)
        self.channel.queue_bind(exchange=dlq_exchange, queue=dlq_queue)

        def callback(ch, method, properties, body):
            payload = json.loads(body)
            handler(payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=dlq_queue, on_message_callback=callback)

    def publish_to_outbox(self, event):
        print("[OUTBOX]", event)

    def start(self):
        self.channel.start_consuming()

    def close(self):
        self.connection.close()