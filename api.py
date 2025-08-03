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

@app.post("/api/ocr")
async def extract_text(file: UploadFile = File(...)):
    print(f"Recebendo arquivo: {file.filename}")
    try:
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        os.makedirs("uploads", exist_ok=True)
        print(f"Salvando arquivo em: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"Arquivo salvo em: {file_path}")
        results = reader.readtext(file_path, detail=0)
        raw_text = " ".join(results)
        os.remove(file_path)
        print(f"Arquivo removido: {file_path}")
        texto_normalizado = normalizar_texto(raw_text)
        print(f"Texto normalizado: {texto_normalizado}")
        medicamentos_match = match_medicamentos(texto_normalizado)
        # medicamentos_openai = await extract_drug_names_openai(texto_normalizado)
        print(f"Medicamentos encontrados: {medicamentos_match}")
        return {
            "texto_extraido": raw_text,
            "texto_normalizado": texto_normalizado,
            # "openai": medicamentos_openai,
            "match_medicamentos": medicamentos_match,
            "success": True
        }

    except Exception as e:
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
