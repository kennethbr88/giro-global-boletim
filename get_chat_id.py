#!/usr/bin/env python3
"""
Ajuda a descobrir o seu TELEGRAM_CHAT_ID.

Como usar:
1. Crie o bot com o @BotFather e copie o token.
2. No Telegram, abra uma conversa com o SEU bot e mande qualquer mensagem
   (ex: "oi") — isso é obrigatório, o bot não pode te achar sem isso.
3. Rode este script:
       python get_chat_id.py SEU_TOKEN_AQUI
4. O chat_id vai aparecer no terminal. Copie e cole no seu .env.
"""

import sys
import requests


def main():
    if len(sys.argv) != 2:
        print("Uso: python get_chat_id.py SEU_TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    token = sys.argv[1]
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(url, timeout=30)
    dados = resp.json()

    if not dados.get("ok"):
        print("Erro ao falar com a API do Telegram:", dados)
        sys.exit(1)

    resultados = dados.get("result", [])
    if not resultados:
        print("Nenhuma mensagem encontrada ainda.")
        print("Abra o Telegram, mande uma mensagem para o seu bot e rode este script de novo.")
        sys.exit(0)

    vistos = set()
    for item in resultados:
        msg = item.get("message") or item.get("channel_post")
        if not msg:
            continue
        chat = msg["chat"]
        chat_id = chat["id"]
        if chat_id in vistos:
            continue
        vistos.add(chat_id)
        nome = chat.get("first_name") or chat.get("title") or "desconhecido"
        print(f"chat_id: {chat_id}  (conversa com: {nome})")

    print("\nCopie o chat_id acima para o seu arquivo .env em TELEGRAM_CHAT_ID.")


if __name__ == "__main__":
    main()
