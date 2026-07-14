import logging

import discord
from discord.ext import commands

import config
from utils import storage

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

_last_ephemeral = {}
_ephemeral_tokens = {}
_send_message = discord.InteractionResponse.send_message
_followup_send = discord.Webhook.send


async def _delete_last_ephemeral(user_id: int) -> None:
    previous = _last_ephemeral.pop(user_id, None)
    if previous is None:
        return
    try:
        if isinstance(previous, discord.Interaction):
            await previous.delete_original_response()
        else:
            await previous.delete()
    except discord.HTTPException:
        pass


async def _tracked_send_message(self, *args, **kwargs):
    interaction = self._parent
    _ephemeral_tokens[interaction.token] = interaction.user.id
    if kwargs.get("ephemeral", False):
        kwargs.setdefault("delete_after", 5)
    response = await _send_message(self, *args, **kwargs)
    if kwargs.get("ephemeral", False):
        await _delete_last_ephemeral(interaction.user.id)
        _last_ephemeral[interaction.user.id] = interaction
    return response


async def _tracked_followup_send(self, *args, **kwargs):
    user_id = _ephemeral_tokens.get(self.token)
    message = await _followup_send(self, *args, **kwargs)
    if kwargs.get("ephemeral", False) and user_id is not None:
        await _delete_last_ephemeral(user_id)
        _last_ephemeral[user_id] = message
        await message.delete(delay=5)
    return message


discord.InteractionResponse.send_message = _tracked_send_message
discord.Webhook.send = _tracked_followup_send


class StoreBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="?", intents=intents)

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.store")
        await self.load_extension("cogs.cart")
        await self.load_extension("cogs.tickets")

        # Registra as views persistentes (botões continuam funcionando
        # mesmo depois de o bot reiniciar).
        from cogs.store import ProductView
        from cogs.tickets import CloseTicketView

        products = storage.load_products()
        for product_id, product in products.items():
            self.add_view(ProductView(product_id, product))

        self.add_view(CloseTicketView())

        if config.GUILD_ID:
            guild = discord.Object(id=int(config.GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.info("Comandos sincronizados no servidor %s", config.GUILD_ID)
        else:
            await self.tree.sync()
            logging.info("Comandos sincronizados globalmente (pode levar até 1h para propagar).")

    async def on_ready(self) -> None:
        logging.info("Bot conectado como %s (ID: %s)", self.user, self.user.id)


bot = StoreBot()


if __name__ == "__main__":
    if not config.TOKEN:
        raise RuntimeError(
            "Defina a variável DISCORD_TOKEN no arquivo .env antes de iniciar o bot."
        )
    bot.run(config.TOKEN)
