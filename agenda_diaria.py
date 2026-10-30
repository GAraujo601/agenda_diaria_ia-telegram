import os
import sys
from datetime import date, datetime
import time
import threading
import requests
from google import genai
import csv

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(PASTA, "tarefas.txt")
REGISTRO = os.path.join(PASTA, "registro.csv")


# lista de modelos: se o primeiro falhar, tenta o próximo (opcional: adicione um segundo nome da lista do AI Studio)
MODELOS_IA = ["gemini-3.8-flash"]
TENTATIVAS = 4
ESPERA_SEGUNDOS = 5
TIMEOUT_CHAMADA = 60  # segundos: limite de cada tentativa
TEMPO_MAXIMO = 180    # segundos: limite total da etapa de IA

# weekday(): segunda = 0 ... domingo = 6
DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
NOMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

PROMPT = """Você é um assistente de produtividade. Abaixo estão as tarefas de hoje ({dia}).
Reorganize-as na ordem em que devem ser feitas, considerando horários citados e urgência.

Regras:
- Use apenas as tarefas da lista. Não invente nem remova nenhuma.
- Responda em português, em texto simples, sem markdown e sem asteriscos.
- Formato: lista numerada na ordem sugerida, seguida de uma linha
  "Foco do dia: ..." com no máximo 15 palavras.

Tarefas:
{tarefas}
"""


def ler_tarefas(dia_atual):
    """Devolve a lista de tarefas do dia. Formato de cada linha: dia | tarefa"""
    tarefas = []
    with open(ARQUIVO, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "|" not in linha:
                continue
            dia, tarefa = (parte.strip() for parte in linha.split("|", 1))
            if dia.lower() in (dia_atual, "todos"):
                tarefas.append(tarefa)
    return tarefas


def _chamar_ia(tarefas, nome_dia):
    """Chama o Gemini, com novas tentativas em falhas temporárias."""
    client = genai.Client()  # lê GEMINI_API_KEY
    lista = "\n".join(f"- {t}" for t in tarefas)
    prompt = PROMPT.format(dia=nome_dia, tarefas=lista)
    ultimo_erro = RuntimeError("nenhum modelo configurado")

    for modelo in MODELOS_IA:
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                resposta = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config={"http_options": {"timeout": TIMEOUT_CHAMADA * 1000}},
                )
                texto = (resposta.text or "").strip()
                if texto:
                    return texto
                ultimo_erro = ValueError("resposta vazia do modelo")
            except Exception as erro:
                ultimo_erro = erro
                print(f"[IA] {modelo}, tentativa {tentativa}/{TENTATIVAS} falhou: {erro}")
                temporario = any(c in str(erro) for c in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED"))
                if not temporario:
                    break  # erro permanente: pula para o próximo modelo
            if tentativa < TENTATIVAS:
                time.sleep(ESPERA_SEGUNDOS * tentativa)

    raise ultimo_erro


def priorizar_com_ia(tarefas, nome_dia):
    """Roda a IA em segundo plano e desiste ao passar de TEMPO_MAXIMO segundos."""
    resultado = {}

    def trabalho():
        try:
            resultado["texto"] = _chamar_ia(tarefas, nome_dia)
        except Exception as erro:
            resultado["erro"] = erro

    fio = threading.Thread(target=trabalho, daemon=True)
    fio.start()
    fio.join(TEMPO_MAXIMO)

    if fio.is_alive():
        raise TimeoutError(f"IA passou de {TEMPO_MAXIMO}s")
    if "erro" in resultado:
        raise resultado["erro"]
    return resultado["texto"]


def registrar(dados):
    """Acrescenta uma linha ao registro.csv. Se falhar, só avisa: o bot não pode parar por isso."""
    try:
        novo = not os.path.exists(REGISTRO)
        with open(REGISTRO, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["data_hora", "tarefas", "usou_ia", "segundos_ia", "erro", "enviado"])
            w.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                dados["tarefas"],
                int(dados["usou_ia"]),
                round(dados["segundos_ia"], 1),
                dados["erro"],
                dados["enviado"],
            ])
    except Exception as erro:
        print(f"[registro] não consegui gravar: {erro}")

def montar_mensagem():
    hoje = date.today()
    indice = hoje.weekday()
    tarefas = ler_tarefas(DIAS[indice])
    dados = {"tarefas": len(tarefas), "usou_ia": False, "segundos_ia": 0.0, "erro": "", "enviado": 0}

    cabecalho = f"Bom dia! Agenda de {NOMES[indice]}, {hoje.strftime('%d/%m')}:"
    if not tarefas:
        return cabecalho + "\n\nNenhuma tarefa cadastrada para hoje.", dados

    inicio = time.time()
    try:
        corpo = priorizar_com_ia(tarefas, NOMES[indice])
        dados["usou_ia"] = True
        print("[IA] priorização aplicada")
    except Exception as erro:  # qualquer falha da IA cai no modo simples
        # guarda só o tipo e o código do erro (ex.: ServerError:503), nunca a mensagem inteira
        dados["erro"] = f"{type(erro).__name__}:{getattr(erro, 'code', '')}"
        print(f"[IA] indisponível, enviando lista simples: {erro}")
        corpo = "\n".join(f"{i}. {t}" for i, t in enumerate(tarefas, start=1))
    dados["segundos_ia"] = time.time() - inicio

    return f"{cabecalho}\n\n{corpo}", dados


def enviar(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resposta = requests.post(url, data={"chat_id": CHAT_ID, "text": texto}, timeout=15)
    resposta.raise_for_status()


def main():
    if not TOKEN or not CHAT_ID:
        sys.exit("Defina TELEGRAM_TOKEN e TELEGRAM_CHAT_ID antes de rodar.")
    if not os.path.exists(ARQUIVO):
        sys.exit(f"Arquivo de tarefas não encontrado: {ARQUIVO}")

    mensagem, dados = montar_mensagem()
    print(mensagem)  # útil para testar no terminal
    try:
        enviar(mensagem)
        dados["enviado"] = 1
    finally:
        registrar(dados)  # grava mesmo se o envio falhar (enviado = 0)
    print("\nMensagem enviada com sucesso.")


if __name__ == "__main__":
    main()