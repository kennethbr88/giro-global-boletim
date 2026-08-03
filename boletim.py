#!/usr/bin/env python3
"""
Boletim Econômico Diário
-------------------------
Coleta manchetes de economia (Brasil + mercado global), pede para o Claude
resumir tudo num boletim curto e envia o resultado por Telegram.

Uso:
    python boletim.py

Configuração: veja o arquivo .env.example / README.md
"""

import os
import sys
import time
import textwrap
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from anthropic import Anthropic

# Carrega variáveis de um arquivo .env se ele existir (uso local).
# No GitHub Actions, as variáveis já vêm do ambiente (via Secrets).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ---------------------------------------------------------------------------
# 1. CONFIGURAÇÃO — edite à vontade
# ---------------------------------------------------------------------------

# Fontes RSS, organizadas por categoria. Cada categoria vira uma seção
# separada no boletim, com sua própria cota de notícias (veja COTA_POR_CATEGORIA
# logo abaixo). Sinta-se livre para adicionar/remover/trocar feeds. Sites às
# vezes mudam a URL do feed; se uma fonte parar de trazer notícias, veja o
# README para como testar e substituir.
RSS_FEEDS = {
    "renda_fixa_tesouro": {
        "Money Times - Renda Fixa": "https://www.moneytimes.com.br/renda-fixa/feed/",
        "InfoMoney - Onde Investir": "https://www.infomoney.com.br/onde-investir/feed/",
    },
    "fundos_imobiliarios": {
        "Money Times - Fundos Imobiliários": "https://www.moneytimes.com.br/fundos-imobiliarios/feed/",
    },
    "economia_br": {
        "InfoMoney - Mercados": "https://www.infomoney.com.br/mercados/feed/",
        "InfoMoney - Economia": "https://www.infomoney.com.br/economia/feed/",
        "Money Times - Mercados": "https://www.moneytimes.com.br/mercados/feed/",
        "Folha - Mercado": "https://feeds.folha.uol.com.br/mercado/rss091.xml",
        # "Estadão - Economia": removido — o Estadão migrou o RSS para uma
        # URL nova (formato arc/outboundfeeds) e a antiga parou de funcionar.
        # Se quiser essa fonte de volta, procure a URL atual e adicione aqui.
    },
    "politica_br": {
        "Poder360": "https://www.poder360.com.br/feed/",
        "Folha - Poder": "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "Estadão - Política": "https://www.estadao.com.br/rss/politica.xml",
    },
    "mercado_global": {
        "MarketWatch - Top Stories": "http://feeds.marketwatch.com/marketwatch/topstories/",
        "CNBC - World Markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    },
}

# Nomes "bonitos" de cada categoria, usados nas seções do boletim. A ordem
# aqui também define a ordem das seções na mensagem final.
NOME_CATEGORIA = {
    "renda_fixa_tesouro": "🏦 Renda Fixa e Tesouro Direto",
    "fundos_imobiliarios": "🏢 Fundos Imobiliários (FIIs)",
    "economia_br": "📊 Economia e Bolsa Brasil",
    "politica_br": "🏛️ Política Brasil",
    "mercado_global": "🌎 Mercado Global (impacto no Brasil)",
}

# Quantas horas "para trás" considerar uma notícia como "de hoje".
# 30h dá uma margem de segurança para feeds que atualizam devagar, sem
# duplicar demais entre execuções diárias.
JANELA_HORAS = 30

# Máximo de itens por feed individual, para nenhuma fonte sozinha dominar a
# categoria.
MAX_POR_FEED = 8

# Máximo de itens brutos coletados por categoria (antes do resumo). O Claude
# depois escolhe e resume os mais relevantes dentro de cada seção — por isso
# aqui vale coletar um pouco mais do que o número final de bullets desejado.
COTA_POR_CATEGORIA = {
    "renda_fixa_tesouro": 10,
    "fundos_imobiliarios": 8,
    "economia_br": 14,
    "politica_br": 14,
    "mercado_global": 8,
}

# Modelo usado para o resumo. Trocar para "claude-haiku-4-5-20251001" reduz o
# custo por execução, com resumos um pouco mais simples.
MODEL = "claude-sonnet-5"

# Lista fixa e editável — não é gerada pelo Claude nem muda sozinha, porque a
# posição das maiores empresas do Brasil não muda de um dia para o outro.
# Atualize esta lista manualmente de vez em quando (ex: 1x por ano) se quiser.
EMPRESAS_MAIS_INFLUENTES = [
    "Petrobras — petróleo e gás",
    "Vale — mineração",
    "Itaú Unibanco — banco",
    "Banco Bradesco — banco",
    "Banco do Brasil — banco",
    "Ambev — bebidas",
    "B3 — bolsa de valores",
    "WEG — bens de capital/energia",
    "JBS — alimentos",
    "Nubank (Nu Holdings) — fintech/banco digital",
]

# Se True, a lista de empresas mais influentes é enviada todo dia. Se False,
# só é enviada às segundas-feiras (para não repetir o mesmo bloco toda hora,
# já que ele quase não muda). Ajuste conforme sua preferência.
ENVIAR_EMPRESAS_TODO_DIA = True

# Aviso fixo, colado no fim de toda mensagem — texto simples, sem custo de
# API (não passa pelo Claude). Importante se você for compartilhar o boletim
# com outras pessoas, não só usar sozinho.
AVISO_LEGAL = (
    "⚠️ Conteúdo informativo gerado por IA a partir de notícias públicas. "
    "Não é recomendação de investimento, análise ou consultoria financeira. "
    "Sempre confirme as informações e avalie seu próprio perfil antes de "
    "tomar qualquer decisão."
)

# Estilo do boletim (ajuste a vontade — isso vai direto no prompt do Claude).
ESTILO_BOLETIM = """
Você escreve um boletim diário para um investidor INICIANTE no Brasil, que tem
ou está começando a montar uma carteira com ações, Fundos Imobiliários (FIIs)
e Tesouro Direto/renda fixa. A pessoa quer entender o que aconteceu no Brasil
e no mundo, e como isso pode afetar a carteira dela — sem jargão sem
explicação e sem recomendações de compra/venda.

Em português do Brasil, para ser lido em poucos minutos no celular. Tom:
direto, didático, um pouco descontraído, sem ser bobo.

As notícias fornecidas vêm organizadas em categorias. Estruture o boletim em
5 seções, NESTA ORDEM, cada uma com seu próprio cabeçalho:

1. "🏦 Renda Fixa e Tesouro Direto" — até 6 bullets: Selic, decisões e atas do
   Copom, IPCA/inflação, curva de juros, novidades de CDB/LCI/LCA/Tesouro
   Direto. É a seção mais importante para quem tem Tesouro na carteira.
2. "🏢 Fundos Imobiliários (FIIs)" — até 5 bullets: variação do IFIX,
   distribuições de dividendos, vacância/ocupação de shoppings e galpões
   logísticos, novos fundos, fusões/vendas de ativos.
3. "📊 Economia e Bolsa Brasil" — até 8 bullets: Ibovespa, câmbio, resultados
   de empresas, decisões do Banco Central, indicadores econômicos.
4. "🏛️ Política Brasil" — até 6 bullets: só o que tem repercussão econômica ou
   de mercado real (reformas, arcabouço fiscal, decisões do Congresso/STF com
   peso econômico) — não é preciso cobrir toda a política, só o que move
   dinheiro.
5. "🌎 Mercado Global (impacto no Brasil)" — até 4 bullets: SÓ inclua algo
   aqui se tiver conexão clara com o investidor brasileiro (decisões do Fed,
   petróleo, dólar, commodities, crises que mexem com capital estrangeiro na
   B3). Ignore notícias globais que não afetam o Brasil, mesmo que sejam
   grandes (ex: fusão de empresas americanas sem ligação com o mercado
   brasileiro), a menos que sejam mesmo o destaque do dia.

Regras gerais:
- Cada bullet tem 1-2 frases, começando com um emoji relevante ao tema.
- Sempre que fizer sentido, adicione uma linha curta abaixo do bullet
  começando com "📌 na prática:" explicando o que isso significa para quem
  tem ações, FIIs ou Tesouro Direto (ex: "📌 na prática: Tesouro prefixado que
  você já tem tende a subir de preço"). Não force essa linha em bullets onde
  não há uma implicação prática clara — é melhor omitir do que forçar.
- Na primeira vez que um termo técnico aparecer no dia (CDI, marcação a
  mercado, come-cotas, vacância, dividend yield, etc.), explique em poucas
  palavras entre parênteses logo depois do termo. Não repita a explicação se
  o termo aparecer de novo no mesmo boletim.
- Se uma seção tiver poucas notícias relevantes nesse dia, é normal trazer
  menos bullets do que o máximo (inclusive zero) — não invente ou repita
  conteúdo para completar a cota.
- Não invente números ou fatos que não estejam nas notícias fornecidas.
- NUNCA recomende comprar, vender ou manter um ativo específico. O boletim é
  informativo, não é indicação de investimento — a decisão é sempre do
  leitor.
- Termine com uma linha curta e opcional de "o que ficar de olho amanhã".
- Não use markdown de tabela nem HTML. Use apenas texto simples e emojis.
"""


# ---------------------------------------------------------------------------
# 2. COLETA DE NOTÍCIAS
# ---------------------------------------------------------------------------

def coletar_noticias():
    """Busca itens recentes em cada feed RSS configurado, por categoria.

    Retorna um dict {categoria: [itens...]}, respeitando a cota de cada
    categoria definida em COTA_POR_CATEGORIA.
    """
    limite = datetime.now(timezone.utc) - timedelta(hours=JANELA_HORAS)
    itens_por_categoria = {categoria: [] for categoria in RSS_FEEDS}

    for categoria, feeds in RSS_FEEDS.items():
        cota_categoria = COTA_POR_CATEGORIA.get(categoria, 10)

        for nome_fonte, url in feeds.items():
            if len(itens_por_categoria[categoria]) >= cota_categoria:
                break  # já bateu a cota dessa categoria, pula pros próximos feeds

            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    print(f"[aviso] Não consegui ler o feed '{nome_fonte}' ({url}): {feed.bozo_exception}")
                    continue

                count_fonte = 0
                for entry in feed.entries:
                    if count_fonte >= MAX_POR_FEED:
                        break
                    if len(itens_por_categoria[categoria]) >= cota_categoria:
                        break

                    publicado = _extrair_data(entry)
                    # Se não der para saber a data, inclui mesmo assim (melhor
                    # arriscar incluir do que perder notícia relevante).
                    if publicado is not None and publicado < limite:
                        continue

                    titulo = entry.get("title", "").strip()
                    resumo = entry.get("summary", "") or entry.get("description", "")
                    resumo = _limpar_html(resumo)[:400]

                    if not titulo:
                        continue

                    itens_por_categoria[categoria].append({
                        "fonte": nome_fonte,
                        "titulo": titulo,
                        "resumo": resumo,
                        "link": entry.get("link", ""),
                    })
                    count_fonte += 1

            except Exception as e:
                print(f"[erro] Falha ao processar '{nome_fonte}': {e}")
                continue

    return itens_por_categoria


def _extrair_data(entry):
    for campo in ("published_parsed", "updated_parsed"):
        valor = entry.get(campo)
        if valor:
            return datetime(*valor[:6], tzinfo=timezone.utc)
    return None


def _limpar_html(texto):
    import re
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# ---------------------------------------------------------------------------
# 3. RESUMO COM CLAUDE
# ---------------------------------------------------------------------------

def montar_prompt(itens_por_categoria):
    hoje = datetime.now().strftime("%d/%m/%Y")
    linhas = [f"Data de hoje: {hoje}", ""]

    for categoria, itens in itens_por_categoria.items():
        nome_bonito = NOME_CATEGORIA.get(categoria, categoria)
        linhas.append(f"### Categoria: {nome_bonito} ###")
        if not itens:
            linhas.append("(nenhuma notícia coletada nesta categoria hoje)")
        for i, item in enumerate(itens, 1):
            linhas.append(f"{i}. [{item['fonte']}] {item['titulo']} — {item['resumo']}")
        linhas.append("")

    return "\n".join(linhas)


def gerar_boletim(itens_por_categoria):
    total_itens = sum(len(v) for v in itens_por_categoria.values())
    if total_itens == 0:
        return ("⚠️ Não consegui coletar notícias hoje (os feeds RSS podem estar "
                "fora do ar ou sem publicações recentes). Confira manualmente.")

    client = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente automaticamente
    prompt = montar_prompt(itens_por_categoria)

    resposta = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=ESTILO_BOLETIM,
        messages=[{"role": "user", "content": prompt}],
    )

    partes_texto = [bloco.text for bloco in resposta.content if bloco.type == "text"]
    boletim = "\n".join(partes_texto).strip()

    if ENVIAR_EMPRESAS_TODO_DIA or datetime.now().weekday() == 0:  # 0 = segunda-feira
        boletim += "\n\n🏢 As 10 empresas mais influentes do Brasil (lista fixa, atualizada periodicamente):\n"
        boletim += "\n".join(f"{i}. {nome}" for i, nome in enumerate(EMPRESAS_MAIS_INFLUENTES, 1))

    boletim += f"\n\n{AVISO_LEGAL}"

    return boletim


# ---------------------------------------------------------------------------
# 4. ENVIO PELO TELEGRAM
# ---------------------------------------------------------------------------

def enviar_telegram(mensagem):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Telegram tem limite de ~4096 caracteres por mensagem. Divide em pedaços
    # se precisar, tentando não cortar no meio de uma linha.
    for pedaco in _dividir_em_pedacos(mensagem, 3800):
        _post_com_retry(url, {
            "chat_id": chat_id,
            "text": pedaco,
            "disable_web_page_preview": True,
        })
        time.sleep(0.5)  # evita rate limit se houver múltiplos pedaços


def _post_com_retry(url, dados, tentativas=3, timeout=60):
    """Faz um POST com algumas tentativas, para tolerar lentidão de rede
    pontual (ex: timeout ocasional ao falar com a API do Telegram)."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.post(url, data=dados, timeout=timeout)
            if resp.status_code == 200:
                return resp
            ultimo_erro = RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        except requests.exceptions.RequestException as e:
            ultimo_erro = e

        if tentativa < tentativas:
            espera = 5 * tentativa  # espera um pouco mais a cada tentativa
            print(f"[aviso] Tentativa {tentativa} falhou ({ultimo_erro}). Tentando de novo em {espera}s...")
            time.sleep(espera)

    raise RuntimeError(f"Falha ao enviar mensagem no Telegram após {tentativas} tentativas: {ultimo_erro}")


def _dividir_em_pedacos(texto, tamanho_max):
    if len(texto) <= tamanho_max:
        return [texto]

    pedacos = []
    linhas = texto.split("\n")
    atual = ""
    for linha in linhas:
        if len(atual) + len(linha) + 1 > tamanho_max:
            pedacos.append(atual)
            atual = linha
        else:
            atual = f"{atual}\n{linha}" if atual else linha
    if atual:
        pedacos.append(atual)
    return pedacos


# ---------------------------------------------------------------------------
# 5. ORQUESTRAÇÃO
# ---------------------------------------------------------------------------

def main():
    obrigatorias = ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    faltando = [v for v in obrigatorias if not os.environ.get(v)]
    if faltando:
        print(f"[erro] Faltam variáveis de ambiente: {', '.join(faltando)}")
        print("Veja o .env.example / README.md para configurar.")
        sys.exit(1)

    print("Coletando notícias...")
    itens_por_categoria = coletar_noticias()
    for categoria, itens in itens_por_categoria.items():
        print(f"  {NOME_CATEGORIA.get(categoria, categoria)}: {len(itens)} notícias")

    print("Gerando resumo com Claude...")
    boletim = gerar_boletim(itens_por_categoria)
    print("\n----- BOLETIM GERADO -----\n")
    print(boletim)
    print("\n---------------------------\n")

    print("Enviando pelo Telegram...")
    enviar_telegram(boletim)
    print("Enviado com sucesso!")


if __name__ == "__main__":
    main()
