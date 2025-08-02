import pika
import json
import base64

# Ajuste a URI conforme seu ambiente
rabbitmq_uri = "amqp://127.0.0.1:5672"
exchange = "ocr.exchange"
routing_key = "extract_text"

# Gera um base64 fake só pra testar (uma string qualquer, não precisa ser imagem real pro teste chegar!)
base64_teste = base64.b64encode(b'TESTE DE IMAGEM').decode()

# Monta o payload do evento conforme esperado pelo seu handler
payload = {
    "base64_string": base64_teste,
    "number": "5521999999999"  # Manda um número fictício
}

connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_uri))
channel = connection.channel()
channel.exchange_declare(exchange=exchange, exchange_type='topic', durable=True)

channel.basic_publish(
    exchange=exchange,
    routing_key=routing_key,
    body=json.dumps(payload),
    properties=pika.BasicProperties(delivery_mode=2)  # Mensagem persistente
)

print("Evento enviado com sucesso! Confira se chegou do outro lado.")
connection.close()
