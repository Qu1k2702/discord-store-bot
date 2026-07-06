import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Opcional: se definido, os comandos são sincronizados instantaneamente
# apenas neste servidor (ótimo para testes). Se vazio, sincroniza global
# (pode levar até 1h para aparecer em todos os servidores).
GUILD_ID = os.getenv("GUILD_ID") or None

# Categoria onde os canais de ticket serão criados
_ticket_category = os.getenv("TICKET_CATEGORY_ID", "0")
TICKET_CATEGORY_ID = int(_ticket_category) if _ticket_category.isdigit() and _ticket_category != "0" else None

# Cargo de atendentes que terá acesso aos tickets
_staff_role = os.getenv("STAFF_ROLE_ID", "0")
STAFF_ROLE_ID = int(_staff_role) if _staff_role.isdigit() and _staff_role != "0" else None
