# Instala bibliotecas necessárias para fuzzy matching e distância de edição
import difflib
from metaphone import doublemetaphone
from fuzzywuzzy import fuzz
import textdistance

# Carrega a lista de medicamentos já filtrada
from medicamentos_lista import remedios_lista

# Pré-processa a lista de medicamentos para uso nos matchings
medicamentos_normalizados = [m.lower() for m in remedios_lista]

# Index para lookup rápido por soundex
soundex_index = {}
for med in medicamentos_normalizados:
    key = doublemetaphone(med)[0]
    if key:
        soundex_index.setdefault(key, []).append(med)

def match_medicamentos(palavras: str) -> str:
    palavras = palavras.lower()
    palavras = palavras.split()
    print("palavras", palavras)
    drugs = []
    # 1. Threshold-Based Similarity Matching
    for med in medicamentos_normalizados:
        score = fuzz.token_set_ratio(palavras, med)
        if score >= 75:
            drugs.append(med)
        

        # 2. Soundex Matching
        soundex_key = doublemetaphone(med)
        candidatos = soundex_index.get(soundex_key, [])
        if candidatos:
            drugs.append(candidatos[0])
        

    # 3. Fuzzy Matching (ratio simples)
    melhor_score = 0
    melhor_match = None
    for med in medicamentos_normalizados:
        score = fuzz.ratio(palavras, med)
        if score > melhor_score and score >= 70:
            melhor_score = score
            melhor_match = med
    if melhor_match:
        drugs.append(melhor_match)

    # 4. Damerau-Levenshtein Distance
    for med in medicamentos_normalizados:
        dist = textdistance.damerau_levenshtein.normalized_similarity(palavras, med)
        if dist > 0.8:
            drugs.append(med)

    return drugs

# # Exemplo de uso
# exemplo = [match_medicamento(p) for p in "dipironna amoxilina paracitamol".split()]
# exemplo
