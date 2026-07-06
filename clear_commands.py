"""
Execute este script UMA VEZ para limpar comandos slash antigos ou duplicados
(tanto globais quanto os registrados em um servidor específico via GUILD_ID).

Depois de rodar isso, rode o bot.py normalmente para repopular apenas
com os comandos atuais definidos no código.

Uso:
    python clear_commands.py
"""

import asyncio

import discord
from discord.ext import commands

import config

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Conectado como {bot.user}")

    # Limpa e ressincroniza os comandos GLOBAIS (remove qualquer coisa
    # que tenha sido sincronizada sem GUILD_ID em algum momento)
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    print("Comandos globais limpos. (a remoção pode levar até 1h para propagar)")

    # Limpa e ressincroniza os comandos do servidor específico, se configurado
    if config.GUILD_ID:
        guild = discord.Object(id=int(config.GUILD_ID))
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"Comandos do servidor {config.GUILD_ID} limpos.")

    print("Concluído. Agora rode 'python bot.py' normalmente.")
    await bot.close()


if __name__ == "__main__":
    if not config.TOKEN:
        raise RuntimeError("Defina DISCORD_TOKEN no .env")
    bot.run(config.TOKEN)