import discord
from discord.ext import commands
import platform
import psutil
import logging
from bson import ObjectId
import datetime
from utils.emojis import *
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
T = db["Tickets"]


class TicketOpen(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ticket_open(self, ObjectID: ObjectId):

        Category = self.client.get_channel(1284918362559873126)
        if not Category:
            return logging.CRITICAL(
                "[TICKETS] The main ticket category isn't there buddy"
            )

        Ticket = await db["Tickets"].find_one({"_id": ObjectID})
        Guild = self.client.get_guild(Ticket.get("GuildID"))
        if not Guild:
            return logging.critical(
                f"[TICKETS] Guild with ID {Ticket.get('GuildID')} not found"
            )
        Member = Guild.get_member(Ticket.get("UserID"))
        if not Member:
            return logging.critical(
                f"[TICKETS] Member with ID {Ticket.get('UserID')} not found"
            )
        Embeds = {
            0: discord.Embed(
                description="Welcome to Birb Support! Please include information about what issue you are experiencing.",
                color=discord.Color.dark_embed(),
            )
            .add_field(
                name="` 👤 ` User Info",
                value=f"{replytop} `User:` {Member.mention} (`{Member.id}`)\n {replymiddle} `Created:` <t:{int(Member.created_at.timestamp())}:R>\n {replybottom} `Joined:` <t:{int(Member.joined_at.timestamp())}:R>",
            )
            .set_author(name="Birb Support", icon_url=self.client.user.display_avatar)
            .add_field(name="` 📝 ` Reason", value=f"```\n{Ticket.get('reason')}\n```"),
        }
        Type = Ticket.get("type")
        Support = {
            0: Guild.get_role(1257815758977765558),
            1: Guild.get_role(1092977378638188594),
        }
        Roles = [
            Guild.get_role(1092977224501710848),
            Guild.get_role(1127223190616289430),
        ]
        Overwrites = {
            Guild.default_role: discord.PermissionOverwrite(read_messages=False),
            Member: discord.PermissionOverwrite(read_messages=True),
            Guild.me: discord.PermissionOverwrite(read_messages=True),
            Support.get(Type): discord.PermissionOverwrite(read_messages=True),
        }
        for role in Roles:
            Overwrites[role] = discord.PermissionOverwrite(read_messages=True)
        Channel = await Guild.create_text_channel(
            name=f"{'support' if Type == 0 else 'dev'}-{Member.display_name}",
            overwrites=Overwrites,
            category=Category,
            topic=f"Ticket opened by @{Member.display_name}",
        )
        await T.update_one({"_id": ObjectID}, {"$set": {"channel": Channel.id}})
        view = TicketControl()
        await Channel.send(
            embed=Embeds.get(Type),
            content=f"{Member.mention}, {Support.get(Type).mention}, <@&1127223190616289430>",
            view=view,
            allowed_mentions=discord.AllowedMentions.all(),
        )

    @commands.Cog.listener()
    async def on_ticket_close(
        self, ObjectID: ObjectId, reason: str, member: discord.Member
    ):
        Result = await T.find_one({"_id": ObjectID})
        if not Result:
            return logging.critical(f"[TICKETS] Ticket with ID {ObjectID} not found")

        Guild = self.client.get_guild(Result.get("GuildID"))
        if not Guild:
            return logging.critical(
                f"[TICKETS] Guild with ID {Result.get('GuildID')} not found"
            )

        Channel = Guild.get_channel(Result.get("channel"))
        if not Channel:
            return logging.critical(
                f"[TICKETS] Channel with ID {Result.get('channel')} not found"
            )
        try:
            user = await Guild.fetch_member(Result.get("UserID"))
        except (discord.NotFound, discord.HTTPException):
            user = None
        await Channel.send(f"<a:Loading:1167074303905386587> Ticket closing...")
        messages = []
        compact = []
        async for message in Channel.history(limit=None):
            messages.append(
                f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {message.content}"
            )
            compact.append(
                {
                    "author_id": message.author.id,
                    "content": message.content,
                    "author_name": message.author.name,
                    "message_id": message.id,
                    "author_avatar": str(
                        message.author.avatar.url if message.author.avatar else ""
                    ),
                    "attachments": [
                        attachment.url for attachment in message.attachments
                    ],
                    "embeds": [embed.to_dict() for embed in message.embeds],
                    "timestamp": message.created_at.timestamp(),
                }
            )
        await T.update_one(
            {"_id": ObjectID},
            {
                "$push": {"transcript": {"messages": messages, "compact": compact}},
                "$set": {"closed": datetime.datetime.utcnow()},
            },
        )

        embed = discord.Embed(
            title="Ticket Closed",
            color=discord.Color.dark_embed(),
        )
        embed.set_author(name=Guild.name, icon_url=Guild.icon.url)
        embed.add_field(name="ID", value=Result.get("_id"), inline=True)
        embed.add_field(
            name="Opened By", value=f"<@{Result.get('UserID')}>", inline=True
        )
        embed.add_field(name="Closed By", value=member.mention, inline=True)
        embed.add_field(
            name="Time Created",
            value=f"<t:{int(Result.get('opened'))}:R>",
            inline=True,
        )
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Channel", value=Channel.name)

        TranscriptChannel = self.client.get_channel(1340774041895571579)
        ButtonLink = discord.ui.View()
        ButtonLink.add_item(
            discord.ui.Button(
                label="View Transcript",
                url=f"https://astrobirb.dev/transcript/{Result.get('_id')}",
                emoji="<:Website:1132252914082127882>",
                style=discord.ButtonStyle.blurple,
            )
        )
        if user:
            await user.send(embed=embed)
        await TranscriptChannel.send(embed=embed, view=ButtonLink)
        await Channel.delete()


class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.AllowedRoles = [
            1257815758977765558,
            1092977224501710848,
            1092977378638188594,
            1127223190616289430,
        ]
        self.Developers = [795743076520820776]

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        custom_id="TICKET:CLOSE",
        emoji="🔒",
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in self.AllowedRoles for role in interaction.user.roles):
            return await interaction.response.send_message(
                "You don't have permission to claim this ticket.", ephemeral=True
            )
        await interaction.response.defer()

        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.followup.send(
                "This isn't a ticket channel.", ephemeral=True
            )
        interaction.client.dispatch(
            "ticket_close", Result.get("_id"), "No reason provided", interaction.user
        )

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.green,
        custom_id="TICKET:CLAIM",
        emoji="✋",
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in self.AllowedRoles for role in interaction.user.roles):
            return await interaction.response.send_message(
                "You don't have permission to claim this ticket.", ephemeral=True
            )
        await interaction.response.defer()

        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.followup.send(
                "This isn't a ticket channel.", ephemeral=True
            )
        if Result.get("claimed").get("claimer"):
            return await interaction.followup.send(
                "This ticket is already claimed.", ephemeral=True
            )
        await T.update_one(
            {"channel": interaction.channel.id},
            {
                "$set": {
                    "claimed": {
                        "claimer": interaction.user.id,
                        "claimedAt": datetime.datetime.now(),
                    }
                }
            },
        )
        embed = discord.Embed(
            color=discord.Color.green(),
            title="Ticket Claimed",
            description=f"This ticket has been claimed by {interaction.user.mention}!",
        ).set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar
        )
        view = TicketControl()
        view.claim.disabled = True
        view.claim.label = f"Claimed by @{interaction.user.name}"
        await interaction.followup.send(embed=embed)
        await interaction.edit_original_response(view=view)

    @discord.ui.button(
        label="Escalate",
        style=discord.ButtonStyle.red,
        custom_id="TICKET:ESCALATE",
        emoji="🔰",
    )
    async def escalate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not any(role.id in self.AllowedRoles for role in interaction.user.roles):
            return await interaction.response.send_message(
                "You don't have permission to escalate this ticket.", ephemeral=True
            )
        await interaction.response.defer()
        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.followup.send(
                "This isn't a ticket channel.", ephemeral=True
            )
        await T.update_one(
            {"channel": interaction.channel.id},
            {
                "$set": {
                    "escalated": {
                        "escalatedBy": interaction.user.id,
                        "escalatedAt": datetime.datetime.now(),
                    }
                }
            },
        )
        embed = discord.Embed(
            color=discord.Color.green(),
            title="Ticket Escalated",
            description=f"This ticket has been escalated by **{interaction.user.display_name}**!",
        ).set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar
        )
        for devs in self.Developers:
            try:
                embed.description = f"{interaction.channel.mention} has been escalated by **{interaction.user.display_name}**!"
                await interaction.client.get_user(devs).send(embed=embed)
            except (discord.NotFound, discord.HTTPException):
                pass
        view = TicketControl()
        view.escalate.disabled = True
        view.escalate.label = f"Escalated by @{interaction.user.name}"
        await interaction.followup.send(embed=embed)
        await interaction.edit_original_response(view=view)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TicketOpen(client))
