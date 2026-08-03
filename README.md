# Boletim Econômico Diário 📈

Todo dia útil, de manhã, este robô:
1. Coleta as principais notícias de **Renda Fixa/Tesouro Direto**, **Fundos
   Imobiliários (FIIs)**, **economia e bolsa do Brasil**, **política do
   Brasil** e **mercado global** (só o que afeta o investidor brasileiro);
2. Pede para o Claude organizar tudo em um boletim curto, pensado para um
   **investidor iniciante** — com explicações de termos técnicos na primeira
   vez que aparecem, e uma linha "📌 na prática" conectando a notícia ao que
   ela significa para quem tem ações, FIIs ou Tesouro Direto;
3. Anexa uma lista fixa das 10 empresas mais influentes do Brasil (não é
   gerada por IA — é uma lista editável no próprio código, já que isso não
   muda de um dia para o outro);
4. Manda o resultado pra você no Telegram.

> O boletim é puramente informativo — ele explica o que aconteceu e o que
> isso costuma significar, mas nunca recomenda comprar, vender ou manter um
> ativo específico. Isso é proposital (veja `ESTILO_BOLETIM` no código).

> Nota sobre custo: como agora são coletadas notícias de 5 categorias, o
> gasto de tokens por execução é um pouco maior que nas versões anteriores
> — ainda assim, na faixa de poucos centavos de dólar por dia.

Depois de configurado uma vez, ele roda sozinho — você não precisa executar nada manualmente.

---

## O que você vai precisar

- Uma conta no [Telegram](https://telegram.org) (é onde o boletim vai chegar)
- Uma chave de API da Anthropic (https://console.anthropic.com) — precisa ter créditos/billing ativado
- Uma conta no [GitHub](https://github.com) (gratuita) — é o que vai "rodar" o robô todo dia, sem precisar deixar seu computador ligado
- Python 3.10+ instalado na sua máquina, só para o teste inicial

O custo da API é bem baixo para esse uso: cada execução usa poucos milhares de tokens, o que dá algo em torno de **1 a 2 centavos de dólar por dia** com o Claude Sonnet 5 (preços em vigor em ago/2026 — confira valores atualizados em https://docs.claude.com/en/docs/about-claude/pricing, pois podem mudar).

---

## Passo 1 — Criar o bot no Telegram

1. No Telegram, procure por **@BotFather** e inicie uma conversa.
2. Envie `/newbot` e siga as instruções (escolha um nome e um "username" terminado em `bot`).
3. O BotFather vai te dar um **token**, algo como `123456789:AAExemplo...`. Guarde-o.
4. Agora procure pelo **seu próprio bot** (pelo username que você escolheu) e mande qualquer mensagem, tipo "oi". Isso é necessário para o bot saber quem é você.

## Passo 2 — Descobrir seu `chat_id`

Com o projeto já baixado no seu computador (veja Passo 4), rode:

```bash
python get_chat_id.py SEU_TOKEN_AQUI
```

Isso vai imprimir seu `chat_id`. Guarde esse número também.

## Passo 3 — Gerar sua chave da API Anthropic

1. Acesse https://console.anthropic.com/settings/keys
2. Crie uma nova chave de API e copie o valor (começa com `sk-ant-...`).
3. Confirme que sua conta tem créditos/billing ativado em "Billing".

## Passo 4 — Baixar e testar o projeto localmente

```bash
# 1. Extraia os arquivos e entre na pasta
cd boletim-economico

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as variáveis de ambiente
cp .env.example .env
# abra o .env num editor de texto e preencha as 3 variáveis:
#   ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 4. Rode o boletim manualmente para testar
python boletim.py
```

Se tudo estiver certo, em alguns segundos você recebe o boletim no Telegram. 🎉

Se der erro, o próprio terminal vai indicar o motivo (variável faltando, token inválido, etc.).

## Passo 5 — Automatizar (rodar sozinho todo dia)

### Opção recomendada: GitHub Actions (gratuito, sem precisar de servidor)

1. Crie um repositório novo no GitHub (pode ser **privado**, já que ele guarda o código, mas não as chaves).
2. Suba todos os arquivos deste projeto para o repositório (incluindo a pasta `.github/workflows`, que já vem pronta).
   - **Não** suba o arquivo `.env` — ele é só para teste local. As chaves reais vão em "Secrets" (próximo passo).
3. No repositório, vá em **Settings → Secrets and variables → Actions → New repository secret** e crie três segredos:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Pronto! O workflow em `.github/workflows/boletim-diario.yml` já está configurado para rodar **de segunda a sexta, às 8h30 (horário de Brasília)**.
5. Para testar sem esperar o horário, vá na aba **Actions** do repositório → **Boletim Econômico Diário** → **Run workflow**.

### Alternativa: cron no seu próprio computador/servidor (Linux/Mac)

Se preferir não usar GitHub, você pode manter um computador ou servidor (ex: uma VPS barata) sempre ligado e usar `cron`:

```bash
crontab -e
```

E adicionar a linha (roda de segunda a sexta às 8h30, horário local):

```
30 8 * * 1-5 cd /caminho/completo/para/boletim-economico && /usr/bin/python3 boletim.py >> boletim.log 2>&1
```

No Windows, use o **Agendador de Tarefas** apontando para `boletim.py` com o mesmo horário.

---

## Personalizando

Tudo fica no topo do arquivo `boletim.py`:

- **`RSS_FEEDS`** — agora com 5 categorias (`renda_fixa_tesouro`, `fundos_imobiliarios`, `economia_br`, `politica_br`, `mercado_global`). Adicione, remova ou troque fontes dentro de cada uma.
- **`COTA_POR_CATEGORIA`** — quantas notícias brutas coletar por categoria antes do resumo (o Claude escolhe as mais relevantes dentro desse total).
- **`EMPRESAS_MAIS_INFLUENTES`** — a lista fixa de empresas enviada no fim do boletim. Edite os nomes à vontade; não precisa mexer em mais nada.
- **`ENVIAR_EMPRESAS_TODO_DIA`** — `True` manda a lista de empresas todo dia; `False` manda só às segundas-feiras (útil se achar repetitivo).
- **`AVISO_LEGAL`** — o aviso fixo colado no fim de toda mensagem, deixando claro que o conteúdo é informativo e não é recomendação de investimento. Não é gerado por IA (texto fixo, sem custo de API). Importante manter se você for compartilhar o boletim com mais gente.
- **`ESTILO_BOLETIM`** — o "prompt de sistema" que define o tom e formato do boletim, incluindo quantos bullets cada seção deve ter. Edite à vontade.
- **`JANELA_HORAS`** — quantas horas "para trás" contam como notícia de hoje.
- **Horário de envio** — edite a linha `cron` em `.github/workflows/boletim-diario.yml` (formato: minuto hora dia mês dia-da-semana, sempre em UTC).

### Sobre os feeds RSS

Sites de notícia às vezes trocam a URL do feed RSS sem aviso. Se um dia o boletim vier vazio ou incompleto, é provável que algum feed tenha mudado. Para testar um feed isoladamente:

```bash
python -c "import feedparser; f = feedparser.parse('URL_DO_FEED'); print(len(f.entries), f.entries[0].title if f.entries else 'vazio')"
```

Se vier vazio, procure no Google por `"nome do site" rss feed` para achar a URL atualizada e troque no `RSS_FEEDS`.

---

## Compartilhando com mais gente (canal do Telegram)

Hoje o `TELEGRAM_CHAT_ID` aponta para uma conversa pessoal (você e o bot). Para
compartilhar o boletim com uma comunidade inteira, o jeito mais simples é
transformar isso num **canal do Telegram** — o mesmo código de envio funciona
sem nenhuma mudança, só troca o destino.

**Passo a passo:**

1. No Telegram, crie um **canal** novo (não é um "grupo" — é a opção
   "Canal"/"Channel"), público ou privado, com o nome que quiser.
2. Adicione seu bot (o mesmo do `.env`) como **administrador** do canal
   (Configurações do canal → Administradores → Adicionar administrador).
3. Descubra o identificador do canal para colocar no `TELEGRAM_CHAT_ID`:
   - Se o canal for **público**, use o próprio `@nomedocanal` (com arroba) —
     não precisa descobrir número nenhum.
   - Se o canal for **privado**, mande uma mensagem qualquer nele e rode
     `python get_chat_id.py SEU_TOKEN` de novo — o chat_id do canal aparece
     na lista (geralmente um número negativo, tipo `-1001234567890`).
4. Atualize o `TELEGRAM_CHAT_ID` (no `.env` local e no Secret do GitHub) com
   esse novo valor.
5. Pronto — todo mundo que entrar no canal passa a receber o boletim
   automaticamente, sem custo adicional de API (o Claude gera o texto uma
   vez só por dia, independente de quantas pessoas estão no canal).

**Sobre monetizar:** se pensar em cobrar (mesmo que um valor simbólico), vale
conversar com um contador sobre as obrigações de declarar essa renda (ex:
MEI). E não deixe de manter o `AVISO_LEGAL` visível — ele existe justamente
para deixar claro que o boletim é informativo, não uma recomendação de
investimento.

---

## Arquivos do projeto

| Arquivo | Para que serve |
|---|---|
| `boletim.py` | Script principal (coleta → resume → envia) |
| `get_chat_id.py` | Ajuda a descobrir seu `chat_id` do Telegram (pessoal ou de canal) |
| `requirements.txt` | Dependências Python |
| `.env.example` | Modelo de configuração local |
| `.github/workflows/boletim-diario.yml` | Agendamento automático via GitHub Actions |
