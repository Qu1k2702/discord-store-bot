import discord
from discord import app_commands
from discord.ext import commands

from utils import pricing, storage


def build_cart_embed(cart: dict, products: dict) -> tuple[discord.Embed, float]:
    embed = discord.Embed(title="🛒 Seu carrinho", color=discord.Color.blurple())
    total = 0.0
    linhas = []

    for product_id, qty in cart.items():
        product = products.get(product_id)
        if not product:
            continue
        try:
            price = pricing.parse_price(str(product.get("price", "0")))
        except ValueError:
            price = 0.0
        subtotal = price * qty
        total += subtotal
        linhas.append(
            f"`{product_id}` **{product['name']}** — {qty}x R$ {price:.2f} = R$ {subtotal:.2f}"
        )

    embed.description = "\n".join(linhas) if linhas else "Seu carrinho está vazio."
    embed.add_field(name="Total", value=f"R$ {total:.2f}", inline=False)
    return embed, total


class CartView(discord.ui.View):
    """Botões para finalizar ou esvaziar o carrinho. Só o dono pode usar."""

    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Este carrinho não é seu.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Finalizar Pedido", style=discord.ButtonStyle.success, emoji="✅")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        from cogs.tickets import create_ticket_for_cart

        carts = storage.load_carts()
        user_key = str(self.user_id)
        cart = carts.get(user_key)

        if not cart:
            await interaction.response.send_message("Seu carrinho está vazio.", ephemeral=True)
            return

        products = storage.load_products()
        cart = {pid: qty for pid, qty in cart.items() if pid in products}

        if not cart:
            await interaction.response.send_message(
                "Os produtos do seu carrinho não estão mais disponíveis.", ephemeral=True
            )
            return

        opened = await create_ticket_for_cart(interaction, cart, products)

        if opened:
            carts.pop(user_key, None)
            storage.save_carts(carts)

        self.stop()

    @discord.ui.button(label="Esvaziar Carrinho", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def esvaziar(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        carts = storage.load_carts()
        carts.pop(str(self.user_id), None)
        storage.save_carts(carts)
        await interaction.response.send_message("Carrinho esvaziado.", ephemeral=True)
        self.stop()


class CartCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    carrinho_group = app_commands.Group(
        name="carrinho", description="Gerenciar seu carrinho de compras"
    )

    @carrinho_group.command(name="ver", description="Mostra os itens do seu carrinho")
    async def ver(self, interaction: discord.Interaction) -> None:
        carts = storage.load_carts()
        cart = carts.get(str(interaction.user.id), {})
        products = storage.load_products()

        embed, _ = build_cart_embed(cart, products)
        view = CartView(interaction.user.id) if cart else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @carrinho_group.command(name="remover", description="Remove um produto do seu carrinho")
    @app_commands.describe(id="ID do produto a remover do carrinho")
    async def remover(self, interaction: discord.Interaction, id: str) -> None:
        carts = storage.load_carts()
        user_key = str(interaction.user.id)
        cart = carts.get(user_key, {})

        if id not in cart:
            await interaction.response.send_message(
                "Esse produto não está no seu carrinho.", ephemeral=True
            )
            return

        del cart[id]
        if cart:
            carts[user_key] = cart
        else:
            carts.pop(user_key, None)
        storage.save_carts(carts)

        await interaction.response.send_message("Produto removido do carrinho.", ephemeral=True)

    @carrinho_group.command(name="limpar", description="Esvazia todo o seu carrinho")
    async def limpar(self, interaction: discord.Interaction) -> None:
        carts = storage.load_carts()
        carts.pop(str(interaction.user.id), None)
        storage.save_carts(carts)
        await interaction.response.send_message("Carrinho esvaziado.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CartCog(bot))