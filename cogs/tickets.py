import asyncio

import discord
from discord.ext import commands

import config
from utils import storage, pricing


async def create_ticket_for_cart(
    interaction: discord.Interaction, cart: dict, products: dict
) -> bool:
    """Cria um canal de ticket privado com TODOS os itens do carrinho do usuário.

    `cart` é {product_id: quantidade}. `products` é o catálogo completo.

    Regra de negócio: cada usuário só pode ter UMA solicitação (ticket)
    aberta por vez — mas esse ticket pode conter vários produtos.

    Retorna True se o ticket foi criado, False se foi bloqueado
    (ex: usuário já tem ticket aberto).
    """
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "Este botão só pode ser usado dentro de um servidor.", ephemeral=True
        )
        return False

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
            return False
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

    total = 0.0
    embed = discord.Embed(
        title="🎫 Novo pedido de compra",
        description=(
            f"Olá {interaction.user.mention}! Recebemos seu pedido com "
            f"{len(cart)} item(ns). Um atendente vai te ajudar por aqui em breve."
        ),
        color=discord.Color.green(),
    )
    for product_id, qty in cart.items():
        product = products[product_id]
        try:
            price = pricing.parse_price(str(product.get("price", "0")))
        except ValueError:
            price = 0.0
        subtotal = price * qty
        total += subtotal
        valor_txt = f"{qty}x R$ {price:.2f} = R$ {subtotal:.2f}"
        if product.get("description"):
            valor_txt += f"\n{product['description']}"
        embed.add_field(
            name=f"{product.get('name', 'Produto')} (ID {product_id})",
            value=valor_txt,
            inline=False,
        )
    embed.add_field(name="Total do pedido", value=f"R$ {total:.2f}", inline=False)
    embed.set_footer(text=f"Cliente: {interaction.user}")

    staff_mention = f"<@&{config.STAFF_ROLE_ID}>" if config.STAFF_ROLE_ID else ""
    await ticket_channel.send(content=staff_mention or None, embed=embed, view=CloseTicketView())

    tickets[user_key] = {"channel_id": ticket_channel.id, "items": cart}
    storage.save_tickets(tickets)

    try:
        await interaction.edit_original_response(
            content=f"Seu ticket foi criado: {ticket_channel.mention}"
        )
    except discord.NotFound:
        pass

    return True


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
