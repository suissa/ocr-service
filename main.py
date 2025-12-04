import base64
from fastapi import FastAPI, UploadFile, File
import easyocr
import shutil
import uuid
import asyncio
import unidecode
import re
from metaphone import doublemetaphone
from openai import OpenAI
from match_drugs import match_medicamentos
from dotenv import load_dotenv
import os
from rabbitq_client import RabbitMQClient

load_dotenv() 





client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY") ,
)
app = FastAPI(title="API OCR com IA Farmacêutica")

reader = easyocr.Reader(['pt', 'en'])

# Dicionário básico para fallback local (pode ser expandido)
KNOWN_MEDICAMENTOS = [
    "dipirona", "paracetamol", "ibuprofeno", "omeprazol", "amoxicilina", "losartana",
    "nimesulida", "buscopan", "dorflex", "novalgina", "neosa", "benegrip", "benevon", "engov"
]
KNOWN_METAPHONES = {doublemetaphone(med)[0]: med for med in KNOWN_MEDICAMENTOS}


def normalizar_texto(texto: str) -> str:
    texto = unidecode.unidecode(texto.lower())
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()

def fallback_regex(texto: str) -> list[str]:
    return [med for med in KNOWN_MEDICAMENTOS if med in texto]

def fallback_fonetico(texto: str) -> list[str]:
    palavras = set(texto.split())
    resultados = []
    for palavra in palavras:
        chave = doublemetaphone(palavra)[0]
        if chave in KNOWN_METAPHONES:
            resultados.append(KNOWN_METAPHONES[chave])
    return list(set(resultados))

async def extract_drug_names_openai(texto_normalizado: str) -> list[str]:
    prompt = f"""
        Você é um sistema de farmácia. Leia o seguinte texto e retorne apenas os nomes de medicamentos detectados, separados por vírgula.

        Texto:
        {texto_normalizado}
        """
    try:
        response = client.responses.create(
            model="gpt-4o",
            instructions="Você é um assistente farmacêutico. Extraia apenas nomes de medicamentos de um texto.",
            input=prompt,
            temperature=0.3
        )
        output_text = response.output[0].content[0].text
        print(output_text)
        return output_text
    except Exception as e:
        return [f"Erro OpenAI: {e}"]



def extract_text_base64(payload: dict):
    print(f"Extracting text for base64: {payload['base64_string']}", flush=True)
    print(f"Extracting text for number: {payload['number']}", flush=True)
    try:
        # Garante que o diretório existe
        os.makedirs("uploads", exist_ok=True)

        # Gera um nome único
        filename = f"{uuid.uuid4().hex}.jpg"
        file_path = os.path.join("uploads", filename)
        print(f"Salvando arquivo em: {file_path}", flush=True)
        # Decodifica e salva
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(payload['base64_string']))
        print(f"Arquivo salvo em: {file_path}", flush=True)
        # Extrai o texto
        results = reader.readtext(file_path, detail=0)
        raw_text = " ".join(results)
        print(f"Texto extraído: {raw_text}", flush=True)
        # Remove o arquivo temporário
        os.remove(file_path)
        print(f"Arquivo removido: {file_path}", flush=True)
        # Se você já tiver essas funções implementadas:
        texto_normalizado = normalizar_texto(raw_text)
        medicamentos_match = match_medicamentos(texto_normalizado)
        print(f"Medicamentos encontrados: {medicamentos_match}", flush=True)
        responseData = {
            "number": payload['number'],
            "texto_extraido": raw_text,
            "texto_normalizado": texto_normalizado,
            "match_medicamentos": medicamentos_match,
        }
        print(f"Response data: {responseData}", flush=True)
        rabbitmq_client.publish_event(
        "ocr.response", payload['number'], responseData)
        print(f"Evento publicado: {payload['number']}", flush=True)
    except Exception as e:
        return {"error": str(e), "success": False}

rabbitmq_uri = os.getenv("RABBITMQ_URI") or "amqp://localhost:5672"
rabbitmq_client = RabbitMQClient(rabbitmq_uri)

print("Subscribing to event", flush=True)
rabbitmq_client.subscribe_to_event(
    "ocr.request", "ocr.queue", "extract_text_base64", extract_text_base64)
print("Event subscribed", flush=True)


print("Starting RabbitMQ client", flush=True)
rabbitmq_client.start()

print("RabbitMQ client started", flush=True)