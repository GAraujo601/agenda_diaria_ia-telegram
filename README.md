# Agenda diária com IA no Telegram

Bot em Python que, todo dia às 8h, lê as tarefas do dia, pede a um LLM (Gemini) para ordená-las por horário e urgência e envia o resultado no Telegram. Se a IA falhar, o bot manda a lista simples: o aviso nunca deixa de chegar.

Projeto pessoal, em uso diário.

## Como funciona

```
tarefas.txt → filtra o dia → Gemini ordena e sugere um foco → Telegram
                                  │
                                  └─ falha, limite ou demora → lista simples (fallback)
```

## Decisões de engenharia

- **Fallback:** qualquer falha da IA cai numa lista numerada simples, então a mensagem sempre chega.
- **Novas tentativas:** erros temporários (503, 429) são repetidos com espera crescente.
- **Limite de 3 minutos:** a etapa de IA roda numa thread com tempo máximo, para a tarefa agendada nunca ficar presa esperando a API.
- **Prompt com regras:** o modelo só pode reordenar as tarefas existentes, sem inventar nem remover nenhuma.
- **Segredos fora do código:** token do Telegram e chave da API vêm de variáveis de ambiente.
- **Observabilidade:** cada execução é registrada em `registro.csv` (tarefas, se a IA respondeu, tempo, tipo de erro, envio) e o `resumo.py` calcula as métricas.

## Resultados



## Como rodar

1. Clone o repositório e instale as dependências:
   ```
   pip install -r requirements.txt
   ```
2. Crie um bot no Telegram (via BotFather) e uma chave da API do Gemini (Google AI Studio). Defina as variáveis de ambiente `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` e `GEMINI_API_KEY`.
3. Copie `tarefas.exemplo.txt` para `tarefas.txt` e edite. Formato: `dia | tarefa`, com os dias sem acento (`segunda`, `terca`, `quarta`, `quinta`, `sexta`, `sabado`, `domingo`) ou `todos`.
4. Rode:
   ```
   python agenda_diaria.py
   ```
5. Para o envio diário, agende o comando no Agendador de Tarefas do Windows (todo dia às 8h).

## Estrutura

- `agenda_diaria.py`: o bot
- `resumo.py`: métricas a partir do `registro.csv`
- `tarefas.exemplo.txt`: modelo do arquivo de tarefas
- `requirements.txt`: dependências

## Ideias em mente para a próxima versão

- Adicionar tarefas pelo próprio Telegram, em linguagem natural
- Suportar um segundo provedor de LLM
