"""Diagnóstico da chave do Gemini.

Separa três perguntas que o erro 429 não distingue:

1. Quais modelos a chave enxerga?
2. Uma chamada simples, sem ferramenta nenhuma, funciona?
3. E com grounding de Google Search ligado?

Se (2) passa e (3) falha, o problema é o grounding, não a cota do modelo — e a
correção é buscar sem grounding em vez de trocar de plano.

Uso: GEMINI_API_KEY=... python scripts/diagnostico_gemini.py
"""

import os
import sys

from google import genai
from google.genai import types

CANDIDATOS = ("gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest")


def main() -> int:
    cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    print("=== 1. Modelos visiveis para esta chave ===")
    try:
        nomes = [m.name for m in cliente.models.list()]
        for n in nomes:
            if "flash" in n or "pro" in n:
                print("   ", n)
        print(f"   (total: {len(nomes)})")
    except Exception as erro:
        print("   FALHOU:", type(erro).__name__, str(erro)[:300])

    for modelo in CANDIDATOS:
        print(f"\n=== 2. {modelo} — chamada simples, sem ferramenta ===")
        try:
            r = cliente.models.generate_content(model=modelo, contents="Diga apenas: ok")
            print("   OK:", (r.text or "").strip()[:60])
        except Exception as erro:
            print("   FALHOU:", str(erro)[:280])

        print(f"=== 3. {modelo} — com grounding de Google Search ===")
        try:
            r = cliente.models.generate_content(
                model=modelo,
                contents="Cite uma vaga de estagio aberta hoje no Brasil, com URL.",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
            )
            print("   OK:", (r.text or "").strip()[:120])
        except Exception as erro:
            print("   FALHOU:", str(erro)[:280])

    return 0


if __name__ == "__main__":
    sys.exit(main())
