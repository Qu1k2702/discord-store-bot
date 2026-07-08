import logging

import discord
from discord.ext import commands

import config
from utils import storage

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True


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
