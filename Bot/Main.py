import discord
from discord import app_commands, SelectOption
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
from datetime import datetime
import io

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = ""
TICKET_PANEL_CHANNEL_ID = 
PURCHASE_CATEGORY_ID = 
OTHER_CATEGORY_ID = 
TRANSCRIPT_CHANNEL_ID = 
STAFF_ROLES = [123456, 12456]# u can add multiple

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} is now online and ready!')

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! Latency is {round(bot.latency * 1000)}ms.')

@bot.tree.command(name="help", description="Show available commands.")
async def help(interaction: discord.Interaction):
    server = interaction.guild
    embed = discord.Embed(
        title="Sunfire Tickets's Commands List",
        description="Here are the available commands for managing tickets:",
        color=0xFA0000
    )
    embed.set_thumbnail(url=server.icon.url)
    embed.add_field(name="💬・chat", value="help, ping", inline=False)
    embed.add_field(name="🎫・ticket", value="add, remove, panel, rename, close, pin, alert", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="panel", description="Create the ticket panel.")
async def panel(interaction: discord.Interaction):
    if interaction.channel.id != TICKET_PANEL_CHANNEL_ID:
        await interaction.response.send_message(f'This command can only be used in the panel channel <#{TICKET_PANEL_CHANNEL_ID}>.', ephemeral=True)
        return

    embed = discord.Embed(
        title="Sunfire Tickets",
        description=("If you need support with any tools/item, open a ticket to buy or ask for help.\n\n"
                     "**How Do I Purchase?**\n"
                     "Simply press the button below and choose the option that fits your needs!\n\n"
                     "**Instant Delivery**\n"
                     "Feel free to purchase directly from our website!\n\n"
                     "**Accepted Payment Methods**\n"
                     "PayPal (Only F&F)\n"
                     "CashApp\n"
                     "ApplePay\n"
                     "Credit/Debit Card (SOON)\n"
                     "Cryptocurrency (LTC, BTC, ETH)"),
        color=0xFA0000
    )

    options = [
        SelectOption(label="Purchase Ticket", emoji="🛒", value="purchase_ticket"),
        SelectOption(label="Other Ticket", emoji="❓", value="other_ticket")
    ]

    select = Select(placeholder="Choose a ticket type...", options=options)

    async def select_callback(interaction: discord.Interaction):
        if select.values[0] == "purchase_ticket":
            await show_purchase_modal(interaction)
        elif select.values[0] == "other_ticket":
            await show_other_modal(interaction)

    select.callback = select_callback

    view = View()
    view.add_item(select)

    await interaction.response.send_message(embed=embed, view=view)

async def show_purchase_modal(interaction: discord.Interaction):
    modal = PurchaseTicketModal()
    await interaction.response.send_modal(modal)

async def show_other_modal(interaction: discord.Interaction):
    modal = OtherTicketModal()
    await interaction.response.send_modal(modal)

class PurchaseTicketModal(Modal, title="Purchase Ticket"):
    product = TextInput(label="Product", placeholder="Enter the product name", required=True)
    key_length = TextInput(label="Key Length Being Purchased", placeholder="e.g., 1 month, lifetime", required=True)
    customer = TextInput(label="Are You A Customer?", placeholder="Yes/No", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, PURCHASE_CATEGORY_ID, "purchase", self.product.value, self.key_length.value, self.customer.value)

class OtherTicketModal(Modal, title="Other Ticket"):
    help_subject = TextInput(label="Help Subject", placeholder="Enter the subject of your help request", required=True)
    help_description = TextInput(label="Help Description", placeholder="Describe your issue in detail", required=True)
    customer = TextInput(label="Are You A Customer?", placeholder="Yes/No", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, OTHER_CATEGORY_ID, "other", self.help_subject.value, self.help_description.value, self.customer.value)

async def create_ticket(interaction: discord.Interaction, category_id, ticket_type, *modal_responses):
    guild = interaction.guild
    category = discord.utils.get(guild.categories, id=category_id)

    open_tickets = [channel for channel in guild.text_channels if channel.topic == f"Ticket for {interaction.user.id}"]
    if len(open_tickets) >= 3:
        await interaction.response.send_message("You have reached the maximum of 3 open tickets.", ephemeral=True)
        return

    channel_name = f"{ticket_type}-{interaction.user.display_name}".replace(" ", "-").lower()
    ticket_channel = await category.create_text_channel(channel_name, topic=f"Ticket for {interaction.user.id}")

    embed = discord.Embed(
        title="🛠️ Support Ticket",
        description=f"Hello {interaction.user.mention}, a support member will be with you shortly!",
        color=0xFA0000
    )

    embed.add_field(name="**Are They a Customer?**", value=modal_responses[-1], inline=False)
    embed.add_field(name="**Help Subject**" if ticket_type == "other" else "**Product**", value=modal_responses[0], inline=False)
    embed.add_field(name="**Help Description**" if ticket_type == "other" else "**Key Length Being Purchased**", value=modal_responses[1], inline=False)
    embed.set_footer(text=f"Created at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

    claim_button = Button(label="Claim", style=discord.ButtonStyle.primary, emoji="✅")
    close_button = Button(label="Close", style=discord.ButtonStyle.danger, emoji="❌")

    async def claim_callback(interaction: discord.Interaction):
        await interaction.response.send_message("Ticket claimed.", ephemeral=True)
    
    async def close_callback(interaction: discord.Interaction):
        view = ConfirmClose()
        await interaction.response.send_message("Are you sure you want to close this ticket?", view=view)

    claim_button.callback = claim_callback
    close_button.callback = close_callback

    view = View()
    view.add_item(claim_button)
    view.add_item(close_button)

    await ticket_channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

    staff_mentions = ' '.join([f'<@&{role_id}>' for role_id in STAFF_ROLES])
    notification_message = await ticket_channel.send(f"New ticket created by {interaction.user.mention}. {staff_mentions}")
    await notification_message.delete(delay=3)

class ConfirmClose(View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.close_ticket(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket closure canceled.", ephemeral=True)
        self.value = False

    async def close_ticket(self, interaction: discord.Interaction):
        transcript = ""
        msg_count = 0
        user_msg_count = 0
        user_id = int(interaction.channel.topic.split("Ticket for ")[1])

        async for message in interaction.channel.history(oldest_first=True):
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            transcript += f"{timestamp} - {message.author}: {message.content}\n"
            msg_count += 1
            if message.author.id == user_id:
                user_msg_count += 1

        transcript_channel = bot.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_channel:
            transcript_embed = discord.Embed(
                title="Ticket Closed",
                description=f"**Ticket:** {interaction.channel.name}\n**Closed By:** {interaction.user.mention}\n**Opened By:** <@{user_id}>\n**Messages:** {msg_count}\n**User Messages:** {user_msg_count}",
                color=0xFA0000,
                timestamp=datetime.utcnow()
            )
            transcript_embed.set_thumbnail(url=interaction.user.display_avatar.url)

            await transcript_channel.send(embed=transcript_embed)

            with io.StringIO(transcript) as transcript_file:
                await transcript_channel.send(file=discord.File(fp=transcript_file, filename=f"{interaction.channel.name}_transcript.txt"))

        dm_embed = discord.Embed(
            title="Ticket Closed",
            description=f"Your ticket `{interaction.channel.name}` has been closed.",
            color=0xFA0000
        )
        dm_embed.add_field(name="Total Messages", value=f"{msg_count}", inline=False)
        dm_embed.set_thumbnail(url=interaction.user.display_avatar.url)

        try:
            user = await bot.fetch_user(user_id)
            await user.send(embed=dm_embed)
            with io.StringIO(transcript) as transcript_file:
                await user.send(file=discord.File(fp=transcript_file, filename=f"{interaction.channel.name}_transcript.txt"))
        except discord.Forbidden:
            await interaction.channel.send("Could not send DM to the user, they may have DMs disabled.")

        await interaction.channel.delete()

@bot.tree.command(name="close", description="Close the current ticket.")
async def close(interaction: discord.Interaction):
    if interaction.channel.topic and "Ticket for" in interaction.channel.topic:
        view = ConfirmClose()
        await interaction.response.send_message("Are you sure you want to close this ticket?", view=view)
    else:
        await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)

@bot.tree.command(name="rename", description="Rename the current ticket.")  
async def rename(interaction: discord.Interaction, name: str):
    if not interaction.channel.topic or "Ticket for" not in interaction.channel.topic:
        await interaction.response.send_message("This command can only be used inside a ticket.", ephemeral=True)
        return

    await interaction.channel.edit(name=name)
    await interaction.response.send_message(f"Ticket renamed to: {name}")

@bot.tree.command(name="alert", description="Alert the user that the ticket will auto-close in 12 hours.")
async def alert(interaction: discord.Interaction):
    if not interaction.channel.topic or "Ticket for" not in interaction.channel.topic:
        await interaction.response.send_message("This command can only be used inside a ticket.", ephemeral=True)
        return

    user_id = int(interaction.channel.topic.split("Ticket for ")[1])
    user = await bot.fetch_user(user_id)
    alert_embed = discord.Embed(
        title="Ticket Auto-Close Alert",
        description=f"Hello {user.mention}, your ticket will auto-close in 12 hours if there is no response.",
        color=0xFA0000
    )
    await interaction.response.send_message(embed=alert_embed)
    await user.send(embed=alert_embed)

bot.run(TOKEN)
