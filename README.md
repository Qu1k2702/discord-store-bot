# Bot de Loja para Discord

Bot escrito em Python com `discord.py` (API moderna: slash commands + Views/Buttons persistentes) para gerenciar uma loja com sistema de tickets de compra.

## Funcionalidades

- Cadastro de produtos via slash command, publicados como **embed** com botão **Comprar**.
- Ao clicar em Comprar, um **ticket** (canal privado) é criado automaticamente, já com as informações do produto selecionado para o atendente.
- **Regras de negócio implementadas:**
  - Cada usuário só pode ter **uma solicitação (ticket) aberta por vez**, independente do produto.
  - Apenas o **cargo de moderador** configurado (+ o próprio cliente dono do ticket) consegue visualizar o canal do ticket.
  - Comandos `/produto criar`, `/produto editar`, `/produto deletar` e `/produto listar`, restritos a moderadores (exceto listar).
- Botões e tickets persistem mesmo se o bot reiniciar (Views persistentes).

## Estrutura do projeto

```
discord-loja-bot/
├── bot.py                 # ponto de entrada
├── config.py               # variáveis de ambiente
├── requirements.txt
├── .env.example
├── cogs/
│   ├── store.py            # comandos de produto + embed + botão de compra
│   └── tickets.py          # criação/fechamento de tickets
├── utils/
│   └── storage.py          # persistência em JSON
└── data/                    # products.json e tickets.json (criados automaticamente)
```

## Instalação

1. **Crie o bot no Discord Developer Portal**
   - https://discord.com/developers/applications → New Application → Bot.
   - Em "Privileged Gateway Intents", ative **Server Members Intent**.
   - Copie o token do bot.

2. **Convide o bot para o servidor** com as permissões:
   - `applications.commands` (slash commands)
   - `Manage Channels` (criar canais de ticket)
   - `View Channels`, `Send Messages`, `Embed Links`, `Attach Files`

3. **Instale as dependências**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure o `.env`**
   ```bash
   cp .env.example .env
   ```
   Preencha:
   - `DISCORD_TOKEN`: token do bot.
   - `GUILD_ID`: (opcional, recomendado em desenvolvimento) ID do seu servidor, para os comandos aparecerem instantaneamente.
   - `TICKET_CATEGORY_ID`: ID da categoria onde os tickets serão criados (clique direito na categoria > Copiar ID, com o Modo Desenvolvedor ativado).
   - `STAFF_ROLE_ID`: ID do cargo de moderador/atendente.

5. **Rode o bot**
   ```bash
   python bot.py
   ```

## Uso

- `/produto criar nome preco descricao imagem estoque` — cadastra um produto e publica a embed com o botão de compra no canal atual.
- `/produto editar id [campos]` — edita um produto e atualiza a embed já publicada.
- `/produto deletar id` — remove o produto e apaga a embed publicada.
- `/produto listar` — lista os produtos cadastrados (resposta privada).
- Botão **Comprar** — abre um ticket privado com o produto já identificado para o atendente.
- Botão **Fechar Ticket** — fecha e apaga o canal (usável pelo dono do ticket ou por moderadores).

## Notas de implementação

- Os dados ficam em `data/products.json` e `data/tickets.json`. Para um ambiente de produção com mais tráfego, considere migrar para SQLite/PostgreSQL — a camada `utils/storage.py` foi isolada exatamente para facilitar essa troca sem alterar a lógica dos cogs.
- Os `custom_id` dos botões de compra incluem o ID do produto (`buy_product:<id>`), o que permite que a Views seja **persistente**: ao reiniciar o bot, `bot.py` recarrega uma view para cada produto salvo, então os botões antigos continuam funcionando.
