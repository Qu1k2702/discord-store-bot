import asyncio

import discord
from discord.ext import commands

import config
from utils import storage


async def create_ticket_for_product(
    interaction: discord.Interaction, product_id: str, product: dict
) -> None:
    """Cria um canal de ticket privado já informando o produto selecionado.

    Regra de negócio: cada usuário só pode ter UMA solicitação (ticket)
    aberta por vez, independente do produto.
    """
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "Este botão só pode ser usado dentro de um servidor.", ephemeral=True
        )
        return

    tickets = storage.load_tickets()
    user_key = str(interaction.user.id)

    existing = tickets.get(user_key)
    if existing:
        existing_channel = guild.get_channel(existing.get("channel_id"))
        if existing_channel:
            await interaction.response.send_message(
                "Você já possui uma solicitação em aberto. Finalize-a antes de "
                f"abrir uma nova: {existing_channel.mention}",
                ephemeral=True,
            )
            return
        # Canal não existe mais (foi apagado manualmente) -> limpa o registro órfão
        del tickets[user_key]
        storage.save_tickets(tickets)

    await interaction.response.send_message("Abrindo seu ticket... 🎫", ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }

    # Apenas o cargo de moderador (configurado) enxerga os tickets, além do
    # próprio cliente e do bot.
    if config.STAFF_ROLE_ID:
        staff_role = guild.get_role(config.STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

    category = None
    if config.TICKET_CATEGORY_ID:
        maybe_category = guild.get_channel(config.TICKET_CATEGORY_ID)
        if isinstance(maybe_category, discord.CategoryChannel):
            category = maybe_category

    raw_name = f"ticket-{interaction.user.name}"
    channel_name = "".join(c for c in raw_name.lower() if c.isalnum() or c == "-")[:90] or "ticket"

    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket de compra aberto por {interaction.user} ({interaction.user.id})",
    )

    embed = discord.Embed(
        title="🎫 Novo pedido de compra",
        description=(
            f"Olá {interaction.user.mention}! Recebemos seu interesse de compra.\n"
            "Um atendente vai te ajudar por aqui em breve."
        ),
        color=discord.Color.green(),
    )
    embed.add_field(name="Produto", value=product.get("name", "Desconhecido"), inline=True)
    embed.add_field(name="Preço", value=f"R$ {product.get('price', '?')}", inline=True)
    if product.get("stock") is not None:
        embed.add_field(name="Estoque", value=str(product["stock"]), inline=True)
    if product.get("description"):
        embed.add_field(name="Descrição", value=product["description"], inline=False)
    if product.get("image"):
        embed.set_thumbnail(url=product["image"])
    embed.set_footer(text=f"ID do produto: {product_id} • Cliente: {interaction.user}")

    staff_mention = f"<@&{config.STAFF_ROLE_ID}>" if config.STAFF_ROLE_ID else ""
    await ticket_channel.send(content=staff_mention or None, embed=embed, view=CloseTicketView())

    tickets[user_key] = {"channel_id": ticket_channel.id, "product_id": product_id}
    storage.save_tickets(tickets)

    try:
        await interaction.edit_original_response(
            content=f"Seu ticket foi criado: {ticket_channel.mention}"
        )
    except discord.NotFound:
        pass


class CloseTicketView(discord.ui.View):
    """View persistente com o botão de fechar ticket."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="close_ticket",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        # Só o dono do ticket ou um moderador pode fechar
        is_owner = False
        tickets = storage.load_tickets()
        owner_key = next(
            (k for k, v in tickets.items() if v.get("channel_id") == interaction.channel_id),
            None,
        )
        if owner_key and str(interaction.user.id) == owner_key:
            is_owner = True

        is_staff = False
        if config.STAFF_ROLE_ID and isinstance(interaction.user, discord.Member):
            is_staff = any(r.id == config.STAFF_ROLE_ID for r in interaction.user.roles)

        if not (is_owner or is_staff or interaction.user.guild_permissions.manage_guild):
            await interaction.response.send_message(
                "Você não tem permissão para fechar este ticket.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Fechando este ticket em 5 segundos...", ephemeral=False
        )

        if owner_key:
            del tickets[owner_key]
            storage.save_tickets(tickets)

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(
                reason=f"Ticket fechado por {interaction.user}"
            )
        except discord.NotFound:
            pass


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketsCog(bot))
