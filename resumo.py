import csv
import os
from collections import Counter
from datetime import datetime, timedelta

PASTA = os.path.dirname(os.path.abspath(__file__))
REGISTRO = os.path.join(PASTA, "registro.csv")

# Minha Estimativa de quantos minutos a agenda pronta economiza por dia.
# No README, deixe claro que é uma estimativa e não uma medição.
MINUTOS_POR_DIA = 5


def main():
    if not os.path.exists(REGISTRO):
        raise SystemExit("registro.csv não encontrado. Rode o bot ao menos uma vez.")
    with open(REGISTRO, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        raise SystemExit("registro.csv está vazio.")

    enviadas = [l for l in linhas if l["enviado"] == "1"]
    com_tarefas = [l for l in linhas if int(l["tarefas"]) > 0]
    com_ia = [l for l in com_tarefas if l["usou_ia"] == "1"]
    tempos = [float(l["segundos_ia"]) for l in com_ia]
    erros = Counter(l["erro"] for l in linhas if l["erro"])

    dias = sorted({
        datetime.strptime(l["data_hora"], "%Y-%m-%d %H:%M:%S").date()
        for l in enviadas
    })

    # sequência atual de dias seguidos com mensagem enviada
    sequencia = 0
    if dias:
        sequencia = 1
        for i in range(len(dias) - 1, 0, -1):
            if dias[i] - dias[i - 1] == timedelta(days=1):
                sequencia += 1
            else:
                break

    print("## Resultados\n")
    print(f"- Execuções registradas: {len(linhas)}")
    if dias:
        print(f"- Dias com mensagem enviada: {len(dias)} (de {dias[0]:%d/%m/%Y} a {dias[-1]:%d/%m/%Y})")
        print(f"- Sequência atual de dias seguidos: {sequencia}")
    print(f"- Taxa de envio: {len(enviadas) / len(linhas):.0%}")
    if com_tarefas:
        print(f"- IA respondeu em {len(com_ia)} de {len(com_tarefas)} execuções com tarefas ({len(com_ia) / len(com_tarefas):.0%})")
    if tempos:
        print(f"- Tempo médio da IA quando respondeu: {sum(tempos) / len(tempos):.1f} s")
    if erros:
        print("- Falhas da IA (tratadas pelo fallback): " + ", ".join(f"{e} x{n}" for e, n in erros.most_common()))
    if dias:
        horas = len(dias) * MINUTOS_POR_DIA / 60
        print(f"- Tempo economizado (estimativa de {MINUTOS_POR_DIA} min/dia): ~{horas:.1f} h")


if __name__ == "__main__":
    main()