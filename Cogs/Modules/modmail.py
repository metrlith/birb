import discord
from discord.ext import commands
import discord.http
from utils.emojis import *
import os
import utils.Paginator as Paginator
import traceback

import typing
from motor.motor_asyncio import AsyncIOMotorClient
from discord import app_commands
from utils.Module import ModuleCheck
from Cogs.Events.modmail import Close
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
environment = os.getenv('ENVIRONMENT')
# client = AsyncIOMotorClient(MONGO_URL)
# db = client["astro"]
# modmail = db["modmail"]
# modmailalerts = db["modmailalerts"]
# modmailblacklists = db["modmailblacklists"]
# modmailcategory = db["modmailcategory"]
# modmailsnippets = db["Modmail Snippets"]
# transcriptschannel = db["transcriptschannel"]
# transcripts = db["Transcripts"]
# Configuration = db["Config"]
from utils.permissions import has_admin_role, has_staff_role
from utils.HelpEmbeds import (
    BotNotConfigured,
    ModuleNotEnabled,
    Support,
)


class Modmail(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client



    async def snippet_autocomplete(
        ctx: commands.Context, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        filter = {"guild_id": interaction.guild_id}

        tag_names = await interaction.client.db['Modmail Snippets'].distinct("name", filter)

        filtered_names = [name for name in tag_names if current.lower() in name.lower()]
        filtered_names = filtered_names[:25]

        choices = [
            app_commands.Choice(name=name, value=name) for name in filtered_names
        ]

        return choices

    @commands.hybrid_group(alias="m", description="Modmail commands")
    async def modmail(self, ctx: commands.Context):
        return

    @modmail.command(description="Pings you for the next message")
    async def alert(self, ctx: commands.Context):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the modmail module isn't enabled."
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        await ctx.send(
            f"{tick} **{ctx.author.display_name},** you will be alerted for the next message.",
            ephemeral=True,
        )
        await self.client.db['modmailalerts'].update_one(
            {"channel_id": ctx.channel.id},
            {"$set": {"alert": ctx.author.id}},
            upsert=True,
        )

    @modmail.command(description="Blacklist someone from using modmail")
    @app_commands.describe(member="The member you want to blacklist from using modmail")
    async def blacklist(self, ctx: commands.Context, member: discord.Member):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the modmail module isn't enabled."
            )
            return
        if not await has_admin_role(ctx, "Modmail Permissions"):
            return
        blacklist = await self.client.db['modmailblacklists'].find_one({"guild_id": ctx.guild.id})
        if blacklist and member.id in blacklist["blacklist"]:
            await ctx.send(f"{no} **{member.display_name}** is already blacklisted.")
            return
        await self.client.db['modmailblacklists'].update_one(
            {"guild_id": ctx.guild.id}, {"$push": {"blacklist": member.id}}, upsert=True
        )
        await ctx.send(
            f"{tick} **{member.display_name}** has been blacklisted from using modmail."
        )

    @modmail.command(description="Unblacklist someone from using modmail")
    @app_commands.describe(
        member="The member you want to unblacklist from using modmail"
    )
    async def unblacklist(self, ctx: commands.Context, member: discord.Member):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_admin_role(ctx, "Modmail Permissions"):
            return
        blacklist = await self.client.db['modmailblacklists'].find_one({"guild_id": ctx.guild.id})
        if blacklist and member.id not in blacklist["blacklist"]:
            await ctx.send(
                f"{no} **{member.display_name}** is not blacklisted.",
            )
            return
        await self.client.db['modmailblacklists'].update_one(
            {"guild_id": ctx.guild.id}, {"$pull": {"blacklist": member.id}}, upsert=True
        )
        await ctx.send(
            f"{tick} **{member.display_name}** has been unblacklisted from using modmail.",
        )

    @modmail.command(description="Reply to a modmail")
    @app_commands.describe(
        content="The message you want to send to the user.",
        media="The media you want to send to the user.",
    )
    async def reply(
        self,
        ctx: commands.Context,
        *,
        content,
        annonymous: bool = None,
        media: discord.Attachment = None,
    ):
        await ctx.defer(ephemeral=True)
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return

        await self.Reply(ctx, content, media, annonymous)

    @modmail.group()
    async def snippets(self, ctx):
        pass

    @snippets.command(description="Create a modmail snippet")
    @app_commands.describe(
        name="The name of the snippet", content="The content of the snippet"
    )
    async def create(
        self,
        ctx: commands.Context,
        name,
        *,
        content: discord.ext.commands.Range[str, 1, 1800],
    ):
        await ctx.defer()

        if not await has_admin_role(ctx, "Modmail Permissions"):
            return
        result = await self.client.db['Modmail Snippets'].find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if result:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, a snippet with that name already exists.",
            )
            return
        await self.client.db['Modmail Snippets'].insert_one(
            {"guild_id": ctx.guild.id, "name": name, "content": content}
        )
        await ctx.send(
            f"{tick} **{ctx.author.display_name}**, I've created the snippet succesfully!",
        )

    @snippets.command(description="Delete a modmail snippet")
    @app_commands.describe(name="The name of the snippet")
    @app_commands.autocomplete(name=snippet_autocomplete)
    async def delete(self, ctx: commands.Context, *, name):
        await ctx.defer()
        if not await has_admin_role(ctx, "Modmail Permissions"):
            return
        result = await self.client.db['Modmail Snippets'].find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if not result:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, a snippet with that name doesn't exist.",
            )
            return
        await self.client.db['Modmail Snippets'].delete_many({"guild_id": ctx.guild.id, "name": name})
        await ctx.send(
            f"{tick} **{ctx.author.display_name}**, I've deleted the snippet succesfully!",
        )

    @snippets.command(description="Edit a modmail snippet")
    @app_commands.describe(
        name="The name of the snippet", content="The new content of the snippet"
    )
    @app_commands.autocomplete(name=snippet_autocomplete)
    async def edit(self, ctx: commands.Context, name, *, content):
        await ctx.defer()
        if not await has_admin_role(ctx, "Modmail Permissions"):
            return
        result = await self.client.db['Modmail Snippets'].find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if not result:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, a snippet with that name doesn't exist.",
            )
            return
        await self.client.db['Modmail Snippets'].update_one(
            {"guild_id": ctx.guild.id, "name": name}, {"$set": {"content": content}}
        )
        await ctx.send(
            f"{tick} **{ctx.author.display_name}**, I've edited the snippet succesfully!",
        )

    @snippets.command(description="Send a modmail snippet in a modmail")
    @app_commands.describe(name="The name of the snippet")
    @app_commands.autocomplete(name=snippet_autocomplete)
    async def send(self, ctx: commands.Context, *, name):
        await ctx.defer(ephemeral=True)
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        result = await self.client.db['Modmail Snippets'].find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if not result:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, a snippet with that name doesn't exist.",
            )
            return
        await self.Reply(ctx, content=result.get("content"))

    @snippets.command(description="List all available modmail snippets")
    async def all(self, ctx: commands.Context):
        await ctx.defer()
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return

        filter = {"guild_id": ctx.guild.id}

        result = self.client.db['Modmail Snippets'].find(filter)
        if result is None:
            await ctx.send(
                f"{no} {ctx.author.display_name}, there are no snippets in the server.\n{arrow} To create a new snippet, use </modmail snippets create:1226670215740264483>",
            )
            return
        result = await result.to_list(length=750)

        if os.getenv("ENVIRONMENT") == "custom":
            msg = await ctx.send(
                embed=discord.Embed(
                    description="Loading...", color=discord.Color.dark_embed()
                )
            )

        else:
            msg = await ctx.send(
                embed=discord.Embed(
                    description="<a:astroloading:1245681595546079285>",
                    color=discord.Color.dark_embed(),
                )
            )

        def Embed():
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(
                name="Snippets",
                icon_url="https://cdn.discordapp.com/emojis/1234994806829355169.webp?size=32",
            )
            embed.set_image(url="https://www.astrobirb.dev/invisble.png")
            return embed

        embeds = []
        embed = Embed()

        count = 0

        for snippet in result:
            name = snippet["name"]
            content = snippet["content"]
            if len(content) > 1024:
                content = content[:1021] + "..."
                break

            embed.add_field(name=name, value=f"{content}", inline=False)
            count += 1

            if count % 5 == 0 or count == len(result):
                embeds.append(embed)
                embed = Embed()
        if count == 0:
            await msg.edit(
                content=f"{no} **{ctx.author.display_name}**, there are no snippets in the server.\n{arrow} To create a new snippet, use </modmail snippets create:1226670215740264483>",
                embed=None,
            )
            return

        paginator = Paginator.Simple(
            PreviousButton=discord.ui.Button(
            emoji="<:chevronleft:1220806425140531321>" if environment != "custom" else None,
            label="<<" if environment == "custom" else None
            ),
            NextButton=discord.ui.Button(
            emoji="<:chevronright:1220806430010118175>" if environment != "custom" else None,
            label=">>" if environment == "custom" else None
            ),
            FirstEmbedButton=discord.ui.Button(
            emoji="<:chevronsleft:1220806428726661130>" if environment != "custom" else None,
            label="<<" if environment == "custom" else None
            ),
            LastEmbedButton=discord.ui.Button(
            emoji="<:chevronsright:1220806426583371866>" if environment != "custom" else None,
            label=">>" if environment == "custom" else None
            ),
            InitialPage=0,
            timeout=360,
        )

        await paginator.start(ctx, pages=embeds[:45], msg=msg)

    @modmail.command(description="View the modmail logs for a member")
    @app_commands.describe(member="The member you want to view the modmail logs for")
    async def logs(self, ctx: commands.Context, member: discord.User):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(embed=ModuleNotEnabled(), view=Support())
            return
        if not await has_admin_role(ctx, "Modmail Permissions"):
            return

        result = await self.client.db['Transcripts'].find({"author": member.id, "guild_id": ctx.guild.id}).to_list(None)
        if not result:
            await ctx.send(f"{no} No modmail logs found for this user.")
            return

        embeds = []
        current_embed = discord.Embed(
            title=f"{(member.name).capitalize()}'s Modmail Logs",
            color=discord.Color.dark_embed(),
        )
        current_embed.set_thumbnail(url=member.display_avatar)
        current_embed.set_author(name=member.name, icon_url=member.display_avatar)
        
        embeds.append(current_embed)
        total_chars = len(current_embed.title)  

        if os.getenv("ENVIRONMENT") == "custom":
            msg = await ctx.send(embed=discord.Embed(description="Loading...", color=discord.Color.dark_embed()))
        else:
            msg = await ctx.send(embed=discord.Embed(description="", color=discord.Color.dark_embed()))

        for i, logs in enumerate(result):
            value = f"> **Transcript:** [View Online]({logs.get('transcriptlink')})\n> **Closed By:** <@{logs.get('closedby')}>\n> **Date:** <t:{int(logs.get('timestamp').timestamp())}:d>\n> **Closure Reason:** {logs.get('reason')}"
            if len(value) > 1024:
                value = value[:1021] + "..."
            
            field_chars = len(f"#{logs.get('transcriptid')}") + len(value)
            
            if total_chars + field_chars > 5800 or len(current_embed.fields) >= 25:
                current_embed = discord.Embed(
                    title=f"{(member.name).capitalize()}'s Modmail Logs",
                    color=discord.Color.dark_embed(),
                )
                current_embed.set_thumbnail(url=member.display_avatar)
                current_embed.set_author(name=member.name, icon_url=member.display_avatar)
                embeds.append(current_embed)
                total_chars = len(current_embed.title)

            current_embed.add_field(name=f"#{logs.get('transcriptid')}", value=value, inline=False)
            total_chars += field_chars

        paginator = Paginator.Simple(
            PreviousButton=discord.ui.Button(
                label="<<" if environment == "custom" else "Previous"
            ),
            NextButton=discord.ui.Button(
                label=">>" if environment == "custom" else "Next"
            ),
            FirstEmbedButton=discord.ui.Button(
                label="<<" if environment == "custom" else "First"
            ),
            LastEmbedButton=discord.ui.Button(
                label=">>" if environment == "custom" else "Last"
            ),
            InitialPage=0,
            timeout=360,
        )

        await paginator.start(ctx, pages=embeds[:45], msg=msg)


    @commands.command(description="Send a snippet", aliases=["s"])
    async def snippet(self, ctx: commands.Context, *, name):
        await ctx.defer(ephemeral=True)
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        result = await self.client.db['Modmail Snippets'].find_one(
            {"guild_id": ctx.guild.id, "name": name}
        )
        if not result:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, a snippet with that name doesn't exist.",
            )
            return
        await self.Reply(ctx, content=result.get("content"))

    @commands.command(description="Reply to a modmail channel.", aliases=["r"])
    async def mreply(self, ctx: commands.Context, *, content):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        await self.Reply(ctx, content, ctx.message.attachments)

    @commands.command(
        description="Close a modmail channel.", name="mclose", aliases=["c"]
    )
    async def close2(self, ctx: commands.Context, *, reason=None):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        await Close(ctx.interaction, reason=reason)

    async def Reply(
        self,
        ctx: commands.Context,
        content: str,
        media: discord.Attachment = None,
        annonymous: bool = None,
    ):
        try:
            if not isinstance(ctx.channel, (discord.TextChannel, discord.Thread)):

                return await ctx.send(
                    content=f"{no} **{ctx.author.display_name},** this isn't a modmail channel."
                )
            if not isinstance(media, discord.Attachment):
                media = None
            ChannelID = ctx.channel.id
            Modmail = await self.client.db['modmail'].find_one({"channel_id": ChannelID})
            Config = await self.client.config.find_one({"_id": ctx.guild.id})
            if not Config:
                return await ctx.send(
                    embed=BotNotConfigured(),
                    view=Support(),
                )
            if not Modmail:
                return await ctx.send(
                    content=f"{no} **{ctx.author.display_name},** this isn't a modmail channel."
                )
            Server = await self.client.fetch_guild(Modmail.get("guild_id"))
            if not Server:
                return await ctx.send(
                    content=f"{no} **{ctx.author.display_name},** no idea how but the guild can't be found from the modmail????"
                )
            user = await self.client.fetch_user(Modmail.get("user_id"))
            if not user:
                return await ctx.send(
                    content=f"{no} **{ctx.author.display_name},** the user can't be found from the modmail????"
                )
            author_name = "Anonymous" if annonymous else ctx.author.name

            embed = discord.Embed(
                color=discord.Color.dark_embed(),
                title=f"**(Staff)** {author_name}",
                description=f"```{content}```",
            )
            embed.set_author(name=Server.name, icon_url=Server.icon)
            embed.set_thumbnail(url=Server.icon)
            if Config.get("Module Options", {}):
                if Config.get("Module Options").get("MessageFormatting") == "Messages":
                    try:
                        await ctx.channel.send(
                            f"<:messagereceived:1201999712593383444> **(Staff)** {author_name}: {content}"
                        )
                        await user.send(
                            f"<:messagereceived:1201999712593383444> **(Staff)** {author_name}: {content}"
                        )
                    except (discord.Forbidden, discord.HTTPException):
                        await ctx.send(
                            f"{no} **{ctx.author.display_name},** I can't send a message to this user.",
                            ephemeral=True,
                        )
                        return
                    if ctx.interaction:
                        return await ctx.message.delete()
                    else:
                        return await ctx.send(
                            content=f"{tick} **{ctx.author.display_name}**, I've sent the message to the user.",
                            ephemeral=True,
                        )

            try:
                if media:
                    file = await media.to_file()
                    try:
                        await user.send(embed=embed, file=file)
                        await ctx.channel.send(embed=embed, file=file)
                    except (discord.Forbidden, discord.HTTPException):
                        await ctx.send(
                            f"{no} **{ctx.author.display_name},** I can't send a message to this user.",
                            ephemeral=True,
                        )
                else:
                    try:
                        await user.send(embed=embed)
                        await ctx.channel.send(embed=embed)
                    except (discord.Forbidden, discord.HTTPException):
                        await ctx.send(
                            f"{no} **{ctx.author.display_name},** I can't send a message to this user.",
                            ephemeral=True,
                        )
                if ctx.interaction:
                    await ctx.send(
                        content=f"{tick} **{ctx.author.display_name},** i've sent the message."
                    )
                else:
                    await ctx.message.delete()

            except discord.Forbidden:
                await ctx.send(
                    f"{no} **{ctx.author.display_name},** I can't send a message to this user.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            traceback.print_exc(e)

    @modmail.command(description="Close a modmail channel.")
    @app_commands.describe(reason="The reason for closing the modmail channel.")
    async def close(self, ctx: commands.Context, *, reason=None):
        if not await ModuleCheck(ctx.guild.id, "Modmail"):
            await ctx.send(
                embed=ModuleNotEnabled(),
                view=Support(),
            )
            return
        if not await has_staff_role(ctx, "Modmail Permissions"):
            return
        await ctx.defer()
        await Close(ctx.interaction, reason=reason)


class Links(discord.ui.View):
    def __init__(self, url):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Transcript", url=url, style=discord.ButtonStyle.blurple
            )
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Modmail(client))
