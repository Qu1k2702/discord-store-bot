import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import (
    LayoutView,
    Container,
    TextDisplay,
    Section,
    Thumbnail,
    Separator,
    ActionRow,
)

from utils import storage


def build_product_view(product_id: str, product: dict) -> "ProductView":
    """Monta a LayoutView (Components V2) de exibição de um produto,
    já com o botão de adicionar ao carrinho incluso."""
    return ProductView(product_id, product)


class CartButton(discord.ui.Button):
    def __init__(self, product_id: str):
        super().__init__(
            label="Adicionar ao Carrinho",
            style=discord.ButtonStyle.success,
            emoji="🛒",
            custom_id=f"cart_add:{product_id}",
        )
        self.product_id = product_id

    async def callback(self, interaction: discord.Interaction) -> None:
        products = storage.load_products()
        product = products.get(self.product_id)

        if not product:
            await interaction.response.send_message(
                "Este produto não está mais disponível.", ephemeral=True
            )
            return

        carts = storage.load_carts()
        user_key = str(interaction.user.id)
        cart = carts.get(user_key, {})
        cart[self.product_id] = cart.get(self.product_id, 0) + 1
        carts[user_key] = cart
        storage.save_carts(carts)

        await interaction.response.send_message(
            f"🛒 **{product['name']}** adicionado ao carrinho "
            f"(quantidade: {cart[self.product_id]}).\n"
            "Use `/carrinho ver` para revisar e finalizar seu pedido.",
            ephemeral=True,
        )


class ProductView(LayoutView):
    """LayoutView persistente (timeout=None) com as infos do produto
    em Components V2 e o botão de adicionar ao carrinho."""

    def __init__(self, product_id: str, product: dict):
        super().__init__(timeout=None)
        self.product_id = product_id

        name = product.get("name", "Produto")
        description = product.get("description") or "Sem descrição."

        container = Container(accent_color=discord.Color.blurple())

        header_text = f"## {name}\n{description}"
        if product.get("image"):
            container.add_item(
                Section(
                    TextDisplay(header_text),
                    accessory=Thumbnail(product["image"]),
                )
            )
        else:
            container.add_item(TextDisplay(header_text))

        container.add_item(Separator())

        info_lines = [f"**Preço:** R$ {product.get('price', '?')}"]
        if product.get("stock") is not None:
            info_lines.append(f"**Estoque:** {product['stock']}")
        container.add_item(TextDisplay("\n".join(info_lines)))

        container.add_item(Separator())
        container.add_item(
            ActionRow(CartButton(product_id))
        )
        container.add_item(TextDisplay(f"-# ID do produto: {product_id}"))

        self.add_item(container)


def is_staff():
    """Permite apenas quem tem 'Gerenciar Servidor' ou o cargo de moderador configurado."""

    async def predicate(interaction: discord.Interaction) -> bool:
        import config

        if interaction.user.guild_permissions.manage_guild:
            return True
        if config.STAFF_ROLE_ID and isinstance(interaction.user, discord.Member):
            if any(r.id == config.STAFF_ROLE_ID for r in interaction.user.roles):
                return True
        raise app_commands.MissingPermissions(["manage_guild"])

    return app_commands.check(predicate)


class StoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    produto_group = app_commands.Group(
        name="produto", description="Gerenciar produtos da loja"
    )

    @produto_group.command(name="criar", description="Cadastra um novo produto na loja")
    @app_commands.describe(
        nome="Nome do produto",
        preco="Preço do produto (ex: 29,90)",
        descricao="Descrição do produto",
        imagem="URL de uma imagem do produto (opcional)",
        estoque="Quantidade em estoque (opcional)",
    )
    @is_staff()
    async def criar(
        self,
        interaction: discord.Interaction,
        nome: str,
        preco: str,
        descricao: str = "Sem descrição.",
        imagem: str = None,
        estoque: int = None,
    ) -> None:
        products = storage.load_products()
        product_id = storage.next_product_id(products)

        product = {
            "name": nome,
            "description": descricao,
            "price": preco,
            "image": imagem,
            "stock": estoque,
        }

        view = build_product_view(product_id, product)

        await interaction.response.send_message(
            f"Produto **{nome}** cadastrado com ID `{product_id}`.", ephemeral=True
        )
        # Components V2 não pode ser combinado com `content=` na mesma mensagem
        message = await interaction.channel.send(view=view)

        product["channel_id"] = message.channel.id
        product["message_id"] = message.id
        products[product_id] = product
        storage.save_products(products)

    @produto_group.command(name="editar", description="Edita um produto já cadastrado")
    @app_commands.describe(
        id="ID do produto (veja em /produto listar)",
        nome="Novo nome (opcional)",
        preco="Novo preço (opcional)",
        descricao="Nova descrição (opcional)",
        imagem="Nova URL de imagem (opcional)",
        estoque="Novo estoque (opcional)",
    )
    @is_staff()
    async def editar(
        self,
        interaction: discord.Interaction,
        id: str,
        nome: str = None,
        preco: str = None,
        descricao: str = None,
        imagem: str = None,
        estoque: int = None,
    ) -> None:
        products = storage.load_products()
        product = products.get(id)

        if not product:
            await interaction.response.send_message(
                f"Nenhum produto encontrado com ID `{id}`.", ephemeral=True
            )
            return

        if nome is not None:
            product["name"] = nome
        if preco is not None:
            product["price"] = preco
        if descricao is not None:
            product["description"] = descricao
        if imagem is not None:
            product["image"] = imagem
        if estoque is not None:
            product["stock"] = estoque

        products[id] = product
        storage.save_products(products)

        # Atualiza a mensagem do produto já publicada, se ela ainda existir
        channel_id = product.get("channel_id")
        message_id = product.get("message_id")
        updated_message = False
        if channel_id and message_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(view=build_product_view(id, product))
                    updated_message = True
                except (discord.NotFound, discord.Forbidden):
                    pass

        aviso = "" if updated_message else "\n(Não foi possível localizar a mensagem original para atualizar.)"
        await interaction.response.send_message(
            f"Produto `{id}` atualizado com sucesso.{aviso}", ephemeral=True
        )

    @produto_group.command(
        name="republicar",
        description="Reenvia a mensagem de um produto (útil se a mensagem original foi apagada)",
    )
    @app_commands.describe(id="ID do produto (veja em /produto listar)")
    @is_staff()
    async def republicar(self, interaction: discord.Interaction, id: str) -> None:
        products = storage.load_products()
        product = products.get(id)

        if not product:
            await interaction.response.send_message(
                f"Nenhum produto encontrado com ID `{id}`.", ephemeral=True
            )
            return

        # Se a mensagem antiga ainda existir, apaga pra não ficar duplicada
        old_channel_id = product.get("channel_id")
        old_message_id = product.get("message_id")
        if old_channel_id and old_message_id:
            old_channel = interaction.guild.get_channel(old_channel_id)
            if old_channel:
                try:
                    old_msg = await old_channel.fetch_message(old_message_id)
                    await old_msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

        view = build_product_view(id, product)

        await interaction.response.send_message(
            f"Reenviando a mensagem do produto **{product['name']}** (ID `{id}`)...",
            ephemeral=True,
        )
        new_message = await interaction.channel.send(view=view)

        product["channel_id"] = new_message.channel.id
        product["message_id"] = new_message.id
        products[id] = product
        storage.save_products(products)

    @produto_group.command(name="deletar", description="Remove um produto da loja")
    @app_commands.describe(id="ID do produto (veja em /produto listar)")
    @is_staff()
    async def deletar(self, interaction: discord.Interaction, id: str) -> None:
        products = storage.load_products()
        product = products.pop(id, None)

        if not product:
            await interaction.response.send_message(
                f"Nenhum produto encontrado com ID `{id}`.", ephemeral=True
            )
            return

        storage.save_products(products)

        # Tenta apagar a mensagem original do produto, se ainda existir
        channel_id = product.get("channel_id")
        message_id = product.get("message_id")
        if channel_id and message_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

        await interaction.response.send_message(
            f"Produto **{product['name']}** (ID `{id}`) removido.", ephemeral=True
        )

    @produto_group.command(name="listar", description="Lista todos os produtos cadastrados")
    async def listar(self, interaction: discord.Interaction) -> None:
        products = storage.load_products()

        if not products:
            await interaction.response.send_message(
                "Nenhum produto cadastrado ainda.", ephemeral=True
            )
            return

        linhas = [
            f"`{pid}` — **{p['name']}** — R$ {p.get('price', '?')}"
            for pid, p in products.items()
        ]

        view = LayoutView()
        container = Container(accent_color=discord.Color.blurple())
        container.add_item(TextDisplay("## 📦 Produtos cadastrados"))
        container.add_item(Separator())
        container.add_item(TextDisplay("\n".join(linhas)))
        view.add_item(container)

        await interaction.response.send_message(view=view, ephemeral=True)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            msg = "Você não tem permissão para usar este comando (requer ser moderador ou ter Gerenciar Servidor)."
        else:
            msg = f"Ocorreu um erro ao executar o comando: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StoreCog(bot))