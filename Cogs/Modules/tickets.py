from discord.ext import commands, tasks
import os
import discord
from datetime import datetime, timedelta
from utils.emojis import *
from Cogs.Configuration.Components.EmbedBuilder import DisplayEmbed
from motor.motor_asyncio import AsyncIOMotorClient
import typing
from Cogs.Events.on_ticket import TicketPermissions
from discord import app_commands
import string
import random
from utils.permissions import has_admin_role
import asyncio
from utils.Module import ModuleCheck
from utils.HelpEmbeds import ModuleNotEnabled, Support, ModuleNotSetup, BotNotConfigured



MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
# db = client["astro"]
# Panels = db["Panels"]
# T = db["Tickets"]
# Blacklists = db["Ticket Blacklists"]


async def AccessControl(interaction: discord.Interaction, Panel: dict):
    if not Panel:
        return True
    if not Panel.get("AccessControl"):
        return True
    for role in Panel.get("AccessControl"):
        if role in [r.id for r in interaction.user.roles]:
            return True


class ButtonHandler(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def add_buttons(self, buttons: typing.Union[list, dict]):
        if isinstance(buttons, list):
            for button in buttons:
                if isinstance(button, dict):
                    self.add_item(Button(button))

        elif isinstance(buttons, dict):
            self.add_item(Button(buttons))


class Button(discord.ui.Button):
    def __init__(self, button: dict):
        custom_id = button.get("custom_id")
        Styles = {
            "Grey": discord.ButtonStyle.grey,
            "Blurple": discord.ButtonStyle.blurple,
            "Green": discord.ButtonStyle.green,
            "Red": discord.ButtonStyle.red,
            "Secondary": discord.ButtonStyle.secondary,
        }

        style = Styles.get(button.get("style"), discord.ButtonStyle.secondary)
        emoji = button.get("emoji")
        if emoji:
            try:
                emoji = discord.PartialEmoji.from_str(emoji)
            except ValueError:
                emoji = None

        super().__init__(
            label=button.get("label"),
            style=style,
            emoji=button.get("emoji"),
            url=button.get("url"),
            custom_id=custom_id,
        )
        self.custom_id = custom_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        AlreadyOpen = await interaction.client.db["Tickets"].count_documents(
            {"UserID": interaction.user.id, "closed": None, "panel": {"$exists": True}}
        )
        Blacklisted = await interaction.client.db["Ticket Blacklists"].find_one(
            {"user": interaction.user.id, "guild": interaction.guild.id}
        )
        if Blacklisted:
            return await interaction.followup.send(
                content=f"{no} **{interaction.user.display_name}**, you're blacklisted from this servers tickets.",
                ephemeral=True,
            )
        Cli = await interaction.guild.fetch_member(interaction.client.user.id)
        if not Cli.guild_permissions.manage_channels:
            return await interaction.followup.send(
                content=f"{no} **{interaction.user.display_name}**, I don't have permission to manage channels.",
                ephemeral=True,
            )
        if AlreadyOpen > 3:
            return await interaction.followup.send(
                content=f"{no} **{interaction.user.display_name}**, you already have a max of 3 tickets open! If this is a mistake contact a developer.\n-# If this is a mistake (actually a mistake) press the debug button. (Abusing it'll can lead to a blacklist)",
                ephemeral=True,
                view=Debug(),
            )

        TPanel = None
        panel = (
            await interaction.client.db["Panels"]
            .find({"guild": interaction.guild.id})
            .to_list(length=None)
        )
        for p in panel:
            button = p.get("Button")
            if button:
                if button.get("custom_id") == self.custom_id:
                    TPanel = p
                    break
        if not await AccessControl(interaction, TPanel):
            return await interaction.followup.send(
                content=f"{no} **{interaction.user.display_name}**, you don't have permission to use this panel.",
                ephemeral=True,
            )

        if TPanel:
            t = await interaction.client.db["Tickets"].insert_one(
                {
                    "_id": "".join(
                        random.choices(string.ascii_letters + string.digits, k=10)
                    ),
                    "GuildID": interaction.guild.id,
                    "UserID": interaction.user.id,
                    "opened": interaction.created_at.timestamp(),
                    "closed": None,
                    "claimed": {"claimer": None, "claimedAt": None},
                    "transcript": [],
                    "type": self.type,
                    "panel": TPanel.get("name"),
                    "panel_id": self.custom_id,
                }
            )
            interaction.client.dispatch(
                "pticket_open", t.inserted_id, TPanel.get("name")
            )
            await interaction.followup.send(
                content=f"{tick} **{interaction.user.display_name}**, I've opened a ticket for you!",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                content=f"{crisis} **{interaction.user.display_name}**, no matching panel found for the given custom ID.",
                ephemeral=True,
                view=Debug(),
            )


class Debug(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Debug Issue", style=discord.ButtonStyle.red)
    async def debug(self, interaction: discord.Interaction, button: discord.ui.Button):
        R = await interaction.client.db["Tickets"].find_one(
            {"UserID": interaction.user.id, "closed": None}
        )
        if not R:
            return await interaction.response.send_message(
                f"{no} **{interaction.user.display_name}**, no open ticket found to debug.",
                ephemeral=True,
            )

        view = Debug()
        view.debug.disabled = True
        await interaction.response.edit_message(
            view=view,
            content=f"{tick} **{interaction.user.display_name}**, your ticket has been purged.",
        )
        interaction.client.dispatch(
            "pticket_close",
            R.get("_id"),
            "Ticket Opener hit the debug button",
            interaction.user,
        )
        await asyncio.sleep(3)
        New = await interaction.client.db["Tickets"].find_one(
            {"UserID": interaction.user.id, "closed": None}
        )
        if New:
            print(f"[Debug Issue] Ticket {R.get('_id')} has been purged.")
            await interaction.client.db["Tickets"].delete_one({"_id": R.get("_id")})


class TicketsPub(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    tickets = app_commands.Group(name="tickets", description="Ticket Commands")

    async def PanelAutoComplete(
        ctx: commands.Context, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        try:
            choices = []
            P = (
                await interaction.client.db["Panels"]
                .find(
                    {"guild": interaction.guild.id, "type": {"$ne": "Welcome Message"}}
                )
                .to_list(length=None)
            )
            for Panel in P:
                choices.append(
                    app_commands.Choice(
                        name=f"{Panel.get('name')} ({'Single' if Panel.get('type') == 'single' else 'Multi'})",
                        value=Panel.get("name"),
                    )
                )
                if len(choices) == 25:
                    break
            return choices

        except (ValueError, discord.HTTPException, discord.NotFound, TypeError):
            return [app_commands.Choice(name="Error", value="Error")]
        


    @tickets.command(description="Send the panel to a channel.")
    @app_commands.autocomplete(panel=PanelAutoComplete)
    async def panel(self, interaction: discord.Interaction, panel: str):
        await interaction.response.defer()

        if not await has_admin_role(interaction):
            return
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Panel = await interaction.client.db["Panels"].find_one(
            {
                "guild": interaction.guild.id,
                "name": panel,
                "type": {"$ne": "Welcome Message"},
            }
        )
        if not Panel:
            return await interaction.followup.send(
                f"{no} **{interaction.user.display_name},** this panel does not exist!",
                ephemeral=True,
            )
        if not Panel.get("Panel"):
            return await interaction.followup.send(
                f"{no} **{interaction.user.display_name},** this panel does not have an embed!",
                ephemeral=True,
            )
        embed = await DisplayEmbed(Panel.get("Panel"))
        if not embed:
            return await interaction.followup.send(
                f"{crisis} **{interaction.user.display_name},** I failed to load the panel embed.",
                ephemeral=True,
            )
        buttons = []
        if Panel.get("type") == "multi":
            for panel_name in Panel.get("Panels"):
                sub = await interaction.client.db["Panels"].find_one(
                    {
                        "guild": interaction.guild.id,
                        "name": panel_name,
                        "type": "single",
                    }
                )
                if not sub:
                    continue
                sub = sub.get("Button")
                buttons.append(
                    {
                        "label": sub.get("label"),
                        "style": sub.get("style"),
                        "emoji": sub.get("emoji"),
                        "custom_id": sub.get("custom_id"),
                    }
                )
                view = ButtonHandler()
                view.add_buttons(buttons)
        else:
            view = ButtonHandler()
            view.add_buttons(Panel.get("Button"))

        if Panel.get("MsgID") and Panel.get("ChannelID"):
            try:
                channel = interaction.guild.get_channel(Panel.get("ChannelID"))
                if channel:
                    last = await channel.fetch_message(Panel.get("MsgID"))
                    await last.delete()
            except discord.NotFound:
                pass
        try:
            msg = await interaction.channel.send(embed=embed, view=view)
        except discord.Forbidden:
            return await interaction.followup.send(
                f"{no} **{interaction.user.display_name},** I don't have permission to send messages in this channel.",
                ephemeral=True,
            )
        await interaction.followup.send(
            f"{tick} **{interaction.user.display_name},** I've sent the panel.",
            ephemeral=True,
        )

        await interaction.client.db["Panels"].update_one(
            {"guild": interaction.guild.id, "name": panel},
            {"$set": {"MsgID": msg.id, "ChannelID": interaction.channel.id}},
        )

    @tickets.command(description="Rename a ticket.")
    async def rename(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        await interaction.client.db["Tickets"].update_one(
            {"ChannelID": interaction.channel.id}, {"$set": {"name": name}}
        )
        try:
            await interaction.channel.edit(name=name)
        except discord.Forbidden:
            return await interaction.followup.send(
                content=f"{no} I don't have permission to rename this ticket."
            )
        await interaction.followup.send(
            content=f"{tick} Successfully renamed ticket to {name}"
        )

    @tickets.command(description="Close a ticket.")
    async def close(self, interaction: discord.Interaction, reason: str = None):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        self.client.dispatch(
            "pticket_close", Result.get("_id"), reason, interaction.user
        )
        await interaction.followup.send(content=f"{tick} Ticket closed.")

    @tickets.command(description="Blacklist a user from the ticket system.")
    async def blacklist(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        if not await has_admin_role(interaction):
            return
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've blacklisted **@{user.display_name}** from the ticket system!"
        )
        await interaction.client.db["Ticket Blacklists"].insert_one(
            {"user": user.id, "guild": interaction.guild.id}
        )

    @tickets.command(description="Unblacklist a user from the ticket system.")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()

        if not await has_admin_role(interaction):
            return
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've unblacklisted **@{user.display_name}** from the ticket system!"
        )
        await interaction.client.db["Ticket Blacklists"].delete_one(
            {"user": user.id, "guild": interaction.guild.id}
        )

    @tickets.command(description="Request to close a ticket.")
    async def closerequest(self, interaction: discord.Interaction, reason: str = None):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        embed = discord.Embed(
            title="Close Request",
            description=f"{interaction.user.mention}, is requesting to close the ticket.\n-# Click Confirm to close this ticket.",
            color=discord.Color.green(),
        )
        try:
            User = await interaction.guild.fetch_member(Result.get("UserID"))
        except (discord.NotFound, discord.HTTPException):
            return await interaction.followup.send(
                content=f"{no} I can't find the user that opened this ticket."
            )

        await interaction.followup.send(
            embed=embed, view=CloseRequest(User, reason), content=User.mention
        )

    @tickets.command(description="Add a user to a ticket.")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        await interaction.channel.set_permissions(
            user,
            read_messages=True,
            send_messages=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            external_emojis=True,
            connect=True,
            speak=True,
        )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've added **@{user.display_name}** to the ticket!"
        )

    @tickets.command(description="Remove a user from a ticket.")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        try:
            await interaction.channel.set_permissions(user, overwrite=None)
        except discord.Forbidden:
            return await interaction.followup.send(
                content=f"{no} I don't have permission to remove this user from the ticket."
            )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've removed **@{user.display_name}** to the ticket!"
        )

    @tickets.command(description="Claim a ticket.")
    async def claim(self, interaction: discord.Interaction):
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        if Result.get("claimed").get("claimer"):
            return await interaction.followup.send(
                content=f"{no} This ticket is already claimed."
            )
        await interaction.client.db["Tickets"].update_one(
            {"ChannelID": interaction.channel.id},
            {
                "$set": {
                    "claimed": {
                        "claimer": interaction.user.id,
                        "claimedAt": interaction.created_at.timestamp(),
                    }
                }
            },
        )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've claimed the ticket!"
        )
        self.client.dispatch("pticket_claim", Result.get("_id"), interaction.user)

    @tickets.command(description="Unclaim a ticket.")
    async def unclaim(self, interaction: discord.Interaction):
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        if not Result.get("claimed").get("claimer"):
            return await interaction.followup.send(
                content=f"{no} This ticket isn't claimed."
            )
        await interaction.response.defer()
        await interaction.client.db["Tickets"].update_one(
            {"ChannelID": interaction.channel.id},
            {"$set": {"claimed": {"claimer": None, "claimedAt": None}}},
        )
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name},** you've unclaimed the ticket!"
        )
        self.client.dispatch("unclaim", Result.get("_id"))

    @tickets.command(description="Toggle automations in the ticket.")
    async def automation(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not await TicketPermissions(interaction):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )
        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                content=f"{no} This isn't a ticket channel."
            )
        Config = await interaction.client.db["Config"].find_one(
            {"_id": interaction.guild.id}
        )
        if not Config:
            return await interaction.followup.send(
                embed=BotNotConfigured(),
                view=Support(),
                ephemeral=True,
            )
        if not Config.get("Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotSetup(),
                view=Support(),
                ephemeral=True,
            )
        if not Config.get("Tickets").get("Automations"):
            return await interaction.followup.send(
                content=f"{no} Automations are disabled for this server."
            )
        if Result.get("automations"):
            await interaction.client.db["Tickets"].update_one(
                {"ChannelID": interaction.channel.id}, {"$set": {"automations": False}}
            )
            await interaction.followup.send(
                content=f"{tick} Automations stopped.",
            )
        else:
            await interaction.client.db["Tickets"].update_one(
                {"ChannelID": interaction.channel.id}, {"$set": {"automations": True}}
            )
            await interaction.followup.send(
                content=f"{tick} Automations started.",
            )


    @tickets.command(description="View a users ticket stats.", name="stats")
    async def stats(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        time: str = None,
    ):
        await interaction.response.defer()
        from utils.format import strtotime

        if not await ModuleCheck(interaction.guild.id, "Tickets"):
            return await interaction.followup.send(
                embed=ModuleNotEnabled(),
                view=Support(),
                ephemeral=True,
            )
        if not await has_admin_role(interaction):
            return
        if not user:
            user = interaction.user
        Tickets = (
            await interaction.client.db["Tickets"]
            .find({"GuildID": interaction.guild.id})
            .to_list(length=None)
        )
        if time:
            time = await strtotime(time)
            Tickets = [
                ticket for ticket in Tickets if ticket.get("opened") >= time.timestamp()
            ]
        if not Tickets:
            return await interaction.followup.send(
                content=f"{no} **{interaction.user.display_name}**, no tickets found for this user.",
            )
        ClaimedTickets = [
            ticket
            for ticket in Tickets
            if ticket.get("claimed", {}).get("claimer") == user.id
        ]

        TotalResponseTime = timedelta(0)
        TotalClaimed = len(ClaimedTickets)
        TotalMessagesSent = 0
        for Ticket in ClaimedTickets:
            OpenedTime = datetime.fromtimestamp(Ticket["opened"])
            ClaimedTime = Ticket["claimed"]["claimedAt"]
            TotalResponseTime += ClaimedTime - OpenedTime
            Transcript = Ticket.get("transcript", [])
            for entry in Transcript:
                CompactMessages = entry.get("compact", [])
                TotalMessagesSent += sum(
                    1
                    for message in CompactMessages
                    if str(message.get("author_id", {})) == str(user.id)
                )

        AverageResponseTime = (
            TotalResponseTime / TotalClaimed if TotalClaimed > 0 else timedelta(0)
        )

        hours, remainder = divmod(AverageResponseTime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        FormattedResponseTime = ""
        if hours > 0:
            FormattedResponseTime += f"{int(hours)}h "
        if minutes > 0:
            FormattedResponseTime += f"{int(minutes)}m "
        FormattedResponseTime += f"{int(seconds)}s"

        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_author(
            name=f"@{user.name}",
            icon_url=user.display_avatar,
        )
        embed.add_field(
            name="Ticket Stats",
            value=(
                f"> **Claimed Tickets:** {TotalClaimed}\n"
                f"> **Average Response Time:** {FormattedResponseTime.strip()}\n"
                f"> **Messages Sent in Tickets:** {TotalMessagesSent}"
            ),
        )
        embed.set_thumbnail(url=user.display_avatar)

        await interaction.followup.send(embed=embed)


class Automations(discord.ui.View):
    def __init__(self, TicketID: str):
        super().__init__(timeout=None)
        self.TicketID = TicketID

    @discord.ui.button(label="Stop Automations", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            return await interaction.response.send_message(
                f"{no} You can't stop this automation.", ephemeral=True
            )
        await interaction.response.defer()
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                f"{no} This isn't a ticket channel.", ephemeral=True
            )
        await interaction.client.db["Tickets"].update_one(
            {"ChannelID": interaction.channel.id}, {"$set": {"automations": False}}
        )
        view = Automations(Result.get("_id"))
        view.stop.disabled = True
        await interaction.response.edit_message(
            content=f"{tick} Automation stopped.", view=view, embed=None
        )


class CloseRequest(discord.ui.View):
    def __init__(self, member: discord.Member, reason: str):
        super().__init__(timeout=None)
        self.member = member
        self.reason = reason

    @discord.ui.button(label="Close", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.member:
            return await interaction.response.send_message(
                f"{no} You can't close this ticket.", ephemeral=True
            )
        await interaction.response.defer()
        Result = await interaction.client.db["Tickets"].find_one(
            {"ChannelID": interaction.channel.id}
        )
        if not Result:
            return await interaction.followup.send(
                f"{no} This isn't a ticket channel.", ephemeral=True
            )
        await interaction.message.delete()
        interaction.client.dispatch(
            "pticket_close", Result.get("_id"), self.reason, interaction.user
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            return await interaction.response.send_message(
                f"{no} You can't close this ticket.", ephemeral=True
            )
        await interaction.response.edit_message(
            view=None, content=f"{no} Cancelled.", embed=None
        )


async def setup(client: commands.Bot) -> None:

    await client.add_cog(TicketsPub(client))
