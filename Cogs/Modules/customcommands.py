import discord
from discord.ext import commands
from utils.emojis import *
from discord import app_commands
import os
import typing
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from utils.permissions import has_admin_role
import random
import re
from utils.Module import ModuleCheck
import asyncio
from Cogs.Configuration.Components.EmbedBuilder import DisplayEmbed, HandleButton
from utils.format import Replace
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]

custom_commands = db["Custom Commands"]
CustomVoting = db["Commands Voting"]
commandslogging = db["Commands Logging"]
prefixdb = db["prefixes"]
modules = db["Modules"]


async def run(
    ctx: discord.Interaction,
    cmd: str = None,
    data: dict = None,
    channel: discord.TextChannel = None,
):
    await ctx.response.defer(ephemeral=True)
    client = ctx.client

    if client.customcommands_maintenance:
        await ctx.followup.send(
            f"{no} **{ctx.user.display_name}**, the custom commands module is currently under maintenance. Please try again later.",
            ephemeral=True,
        )
        return

    if not await ModuleCheck(ctx.guild.id, "customcommands"):
        await ctx.followup.send(
            f"{no} **{ctx.user.display_name}**, the custom commands module isn't enabled.",
            ephemeral=True,
        )
        return
    if not data:
        command_data = await custom_commands.find_one(
            {
                "Command" if not cmd else "name": (
                    cmd if not ctx.command else ctx.command.name
                ),
                "guild_id": ctx.guild.id,
            }
        )

        if command_data is None:
            await ctx.followup.send(
                f"{no} **{ctx.user.display_name},** That command does not exist.",
                ephemeral=True,
            )
            return
        command = cmd if not ctx.command else ctx.command.name
    else:
        command_data = data
        command = data.get("Command")

    if not await has_customcommandrole(ctx, command):
        return

    view = None
    if command_data.get("components"):
        view = await HandleButton(command_data)

    timestamp = datetime.utcnow().timestamp()
    replacements = {
        "{author.mention}": ctx.user.mention,
        "{author.name}": ctx.user.display_name,
        "{author.id}": str(ctx.user.id),
        "{timestamp}": f"<t:{int(timestamp)}:F>",
        "{guild.name}": ctx.guild.name,
        "{guild.id}": str(ctx.guild.id),
        "{guild.owner.mention}": ctx.guild.owner.mention if ctx.guild.owner else "",
        "{guild.owner.name}": (ctx.guild.owner.display_name if ctx.guild.owner else ""),
        "{guild.owner.id}": str(ctx.guild.owner.id) if ctx.guild.owner else "",
        "{random}": str(random.randint(1, 1000000)),
        "{guild.members}": str(ctx.guild.member_count),
        "{channel.name}": channel.name if channel else ctx.channel.name,
        "{channel.id}": str(channel.id) if channel else str(ctx.channel.id),
        "{channel.mention}": channel.mention if channel else ctx.channel.mention,
    }

    content = Replace(command_data.get("content", ""), replacements)
    embed = None
    if command_data.get("embed"):
        embed = await DisplayEmbed(command_data, None, replacements)
    target_channel = channel or ctx.channel
    try:
        if not cmd:
            msg = await target_channel.send(
                content,
                embed=embed,
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True
                ),
            )
            await ctx.followup.send(
                f"{tick} **{ctx.user.display_name},** The command has been sent",
                ephemeral=True,
            )
        else:
            await ctx.followup.send(
                content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=True, users=True, roles=True
                ),
                ephemeral=True,
            )

    except discord.Forbidden:
        await ctx.followup.send(
            f"{no} **{ctx.user.display_name},** I do not have permission to send messages in that channel.",
            ephemeral=True,
        )
        return

    loggingdata = await commandslogging.find_one({"guild_id": ctx.guild.id})
    if loggingdata:
        loggingchannel = client.get_channel(loggingdata["channel_id"])
        if loggingchannel:
            log_embed = discord.Embed(
                title="Custom Command Usage",
                description=f"Command **{command}** was used by {ctx.user.mention} in {ctx.channel.mention}",
                color=discord.Color.dark_embed(),
            )
            log_embed.set_author(
                name=ctx.user.display_name, icon_url=ctx.user.display_avatar
            )
            try:
                await loggingchannel.send(embed=log_embed)
            except (discord.Forbidden, discord.HTTPException):
                print(
                    f"I could not send the log message in the specified channel (guild: {ctx.guild.name})"
                )

    if command_data.get("buttons") == "Voting Buttons":
        voting_data = {
            "guild_id": ctx.guild.id,
            "message_id": msg.id,
            "author": ctx.user.id,
            "votes": 0,
            "Voters": [],
        }
        await CustomVoting.insert_one(voting_data)


async def SyncCommand(self: commands.Bot, name: str, guild: int):
    Stripped = name.strip().lower()
    Stripped = Stripped.lstrip("/")
    Stripped = re.sub(r"[^a-z0-9\-_]", "", name.replace(" ", "_"))
    if not (1 <= len(Stripped) <= 32):
        return

    async def command_callback(interaction: discord.Interaction):
        await run(interaction)

    try:
        Command = app_commands.Command(
            name=Stripped, description="[Custom CMD]", callback=command_callback
        )
        await self.customcommands.update_one(
            {"name": name, "guild_id": guild},
            {
                "$set": {
                    "Command": Stripped,
                }
            },
        )
        self.tree.add_command(Command, guild=discord.Object(id=guild))
        await self.tree.sync(guild=discord.Object(id=guild))
    except discord.app_commands.errors.CommandAlreadyRegistered:
        return
    return


async def Unsync(self: commands.Bot, name: str, guild: int):
    try:
        self.tree.remove_command(name, guild=discord.Object(id=guild))
        await self.tree.sync(guild=discord.Object(id=guild))
    except discord.errors.NotFound:
        pass
    return


class CustomCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await self.RegisterCustomCommands()

    async def commands_auto_complete(
        ctx: commands.Context, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        try:
            filter = {"guild_id": interaction.guild_id}

            tag_names = await custom_commands.distinct("name", filter)

            filtered_names = [
                name for name in tag_names if current.lower() in name.lower()
            ]

            choices = [
                app_commands.Choice(name=name, value=name)
                for name in filtered_names[:25]
            ]

            return choices
        except Exception as e:
            print(f"Error in commands_auto_complete: {e}")
            return []

    @commands.command()
    async def prefix(self, ctx: commands.Context, prefix: str = None):
        result = await prefixdb.find_one({"guild_id": ctx.guild.id})
        if result:

            currentprefix = result.get("prefix", "!!")
        else:
            currentprefix = "!!"

        if prefix is None:

            await ctx.send(
                f"<:command1:1223062616872583289> **{ctx.author.display_name},** the prefix is `{currentprefix}`",
            )
        else:
            if ctx.author.guild_permissions.manage_guild:

                await prefixdb.update_one(
                    {"guild_id": ctx.guild.id},
                    {"$set": {"prefix": prefix}},
                    upsert=True,
                )
                await ctx.send(
                    f"<:whitecheck:1190819388941668362> **{ctx.author.display_name},** I've set the prefix to `{prefix}`",
                )
            else:
                await ctx.send(
                    f"<:command1:1223062616872583289> **{ctx.author.display_name},** the prefix is `{currentprefix}`",
                )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if message.content is None:
            return

        if self.client.customcommands_maintenance is True:
            return

        try:

            result = await custom_commands.find({"guild_id": message.guild.id}).to_list(
                length=None
            )
            module = await ModuleCheck(message.guild.id, "customcommands")
            if not module:
                return

            prefixes = await self.client.get_prefix(message)
            if prefixes is None:
                return
            for prefix in prefixes:
                if message.content.startswith(prefix):
                    try:
                        command = message.content[len(prefix) :]
                    except:
                        return
                    command = re.sub(r"^[^a-zA-Z0-9]+", "", command)
                    break
            else:

                return

            for command_data in result:

                if command_data.get("name") == command:

                    if not await has_customcommandrole2(message, command):
                        return
                    if "buttons" in command_data:
                        if command_data["buttons"] == "Voting Buttons":
                            view = Voting()
                        elif command_data["buttons"] == "Link Button":
                            view = URL(
                                command_data["url"], command_data["button_label"]
                            )
                        elif command_data["buttons"] == "Embed Button":
                            label = command_data["button_label"]
                            colour = command_data["colour"]
                            name = command_data["cmd"]
                            view = ButtonEmbed(name)
                            view.button_callback.label = label

                            if colour == "Blurple":
                                view.button_callback.style = discord.ButtonStyle.blurple
                            elif colour == "Green":
                                view.button_callback.style = discord.ButtonStyle.green
                            elif colour == "Red":
                                view.button_callback.style = discord.ButtonStyle.red
                            elif colour == "Grey":
                                view.button_callback.style = discord.ButtonStyle.grey
                            else:
                                view.button_callback.style = discord.ButtonStyle.grey

                            emoji_data = command_data.get("emoji", None)

                            if emoji_data:
                                if ":" in emoji_data:
                                    emoji_id_str = emoji_data.split(":")[2][:-1]
                                    emoji_id = int(emoji_id_str)
                                    emoji = message.guild.get_emoji(emoji_id)
                                    if emoji:
                                        view.button_callback.emoji = command_data.get(
                                            "emoji", None
                                        )

                                else:
                                    view.button_callback.emoji = command_data.get(
                                        "emoji", None
                                    )

                        else:
                            view = None
                    else:
                        view = None
                    try:
                        guild = message.guild
                        owner = await guild.fetch_member(guild.owner_id)
                        ownermention = owner.mention
                        ownername = owner.name
                        ownerid = owner.id
                    except discord.NotFound:
                        ownermention = None
                        ownername = None
                        ownerid = None

                    timestamp = datetime.utcnow().timestamp()
                    timestampformat = f"<t:{int(timestamp)}:F>"
                    replacements = {
                        "{author.mention}": message.author.mention,
                        "{author.name}": message.author.display_name,
                        "{author.id}": str(message.author.id),
                        "{timestamp}": timestampformat,
                        "{guild.name}": message.guild.name if message.guild else "",
                        "{guild.id}": str(message.guild.id) if message.guild else "",
                        "{guild.owner.mention}": (
                            ownermention if message.guild and ownermention else ""
                        ),
                        "{guild.owner.name}": (
                            ownername if message.guild and owner else ""
                        ),
                        "{guild.owner.id}": (
                            str(ownerid) if message.guild and owner else ""
                        ),
                        "{random}": int(random.randint(1, 1000000)),
                        "{guild.members}": int(message.guild.member_count),
                        "{channel.name}": (
                            message.channel.name
                            if message.channel
                            else message.channel.name
                        ),
                        "{channel.id}": (
                            str(message.channel.id)
                            if message.channel
                            else str(message.channel.id)
                        ),
                        "{channel.mention}": (
                            message.channel.mention
                            if message.channel
                            else message.channel.mention
                        ),
                    }

                    content = await self.replace_variables(
                        command_data.get("content", ""), replacements
                    )
                    if content == "":
                        content = ""

                    if "embed" in command_data and command_data["embed"]:
                        embed = await DisplayEmbed(command_data, None, replacements)
                        try:
                            if content or embed or view:
                                try:
                                    msg = await message.channel.send(
                                        content, embed=embed, view=view
                                    )
                                except discord.Forbidden:
                                    print(
                                        "[ERROR] I couldn't send a custom command in a command trigger"
                                    )
                                    return
                                try:
                                    await message.delete()
                                except discord.Forbidden:
                                    print("[ERROR] I couldn't delete a command trigger")

                                loggingdata = await commandslogging.find_one(
                                    {"guild_id": message.guild.id}
                                )
                                if loggingdata:
                                    loggingchannel = self.client.get_channel(
                                        loggingdata["channel_id"]
                                    )
                                    if loggingchannel:
                                        embed = discord.Embed(
                                            title="Custom Command Usage",
                                            description=f"Command **{command}** was used by {message.author.mention} in {message.channel.mention}",
                                            color=discord.Color.dark_embed(),
                                        )
                                        embed.set_author(
                                            name=message.author.display_name,
                                            icon_url=message.author.display_avatar,
                                        )
                                        try:
                                            await loggingchannel.send(embed=embed)
                                        except (
                                            discord.Forbidden,
                                            discord.HTTPException,
                                        ):
                                            print(
                                                f"[CMD] I could not find the channel to send the tag usage (guild: {message.guild.name})"
                                            )
                                    else:
                                        print(
                                            "[CMD] I could not find the channel to send the command usage"
                                        )
                            else:
                                await message.channel.send(
                                    f"{no} **{message.author.display_name},** This command does not have any content or embed.",
                                )
                                return

                        except discord.Forbidden:
                            print(
                                "[ERROR CUSTOM COMMAND AUTORESPONSE] I couldn't send a message in that channel."
                            )
                            return

                    else:
                        if content is None:
                            await message.channel.send(
                                f"{no} **{message.author.display_name},** That command does not have any content or embeds.",
                            )
                            return
                        try:
                            if content or view:
                                try:
                                    msg = await message.channel.send(content, view=view)
                                except discord.Forbidden:
                                    print(
                                        f"[CMD] I couldn't send a message in that channel."
                                    )
                                    return
                                try:
                                    await message.delete()
                                except discord.Forbidden:
                                    print(
                                        f"[CMD] I couldn't delete the message that triggered the command"
                                    )
                                loggingdata = await commandslogging.find_one(
                                    {"guild_id": message.guild.id}
                                )
                                if loggingdata:
                                    loggingchannel = self.client.get_channel(
                                        loggingdata["channel_id"]
                                    )
                                    if loggingchannel:
                                        embed = discord.Embed(
                                            title="Custom Command Usage",
                                            description=f"Command **{command}** was used by {message.author.mention} in {message.channel.mention}",
                                            color=discord.Color.dark_embed(),
                                        )
                                        embed.set_author(
                                            name=message.author.display_name,
                                            icon_url=message.author.display_avatar,
                                        )
                                        try:
                                            await loggingchannel.send(embed=embed)
                                        except (
                                            discord.Forbidden,
                                            discord.HTTPException,
                                        ):
                                            print(
                                                f"[CMD] I could not find the channel to send the tag usage (guild: {message.guild.name})"
                                            )
                                    else:
                                        print(
                                            "[CMD] I could not find the channel to send the command usage"
                                        )
                            else:
                                await message.channel.send(
                                    f"{no} **{message.author.display_name},** This command does not have any content or embed.",
                                )
                                return

                        except discord.Forbidden:
                            print(
                                "[ERROR] I do not have permission to send messages in that channel or can' delete the message."
                            )
                            return

        except:
            print("Custom Command Error")
            pass

    async def RegisterCustomCommands(self):
        customcommands = await self.client.customcommands.find({}).to_list(length=None)
        CommandGroups = {}
        Commands = []
        GuildsToSync = set()
        SyncedServers = 0

        for command in customcommands:
            ActualRaw = None
            Raw = None
            guild_id = None
            try:
                ActualRaw = command.get("name")
                Raw = command.get("name", "").strip().lower()
                guild_id = command.get("guild_id")
            except (KeyError, AttributeError):
                continue
            if not guild_id:
                continue

            Command = Raw.lstrip("/")
            Command = re.sub(r"[^a-z0-9\-_]", "", Command.replace(" ", "_"))
            if not (1 <= len(Command) <= 32):
                continue
            Commands.append({"name": Command, "guild_id": guild_id, "raw": ActualRaw})

            async def command_callback(interaction: discord.Interaction):
                await run(interaction)

            Command = app_commands.Command(
                name=Command, description="[Custom CMD]", callback=command_callback
            )

            try:
                command = self.client.tree.add_command(
                    Command, guild=discord.Object(id=guild_id)
                )

            except discord.app_commands.errors.CommandAlreadyRegistered:
                continue

            GuildsToSync.add(guild_id)

        for guild_id in GuildsToSync:
            try:
                tree = await self.client.tree.sync(guild=discord.Object(id=guild_id))
                for command in Commands:
                    for synced_command in tree:
                        if command["name"] == synced_command.name:
                            await self.client.customcommands.update_one(
                                {"name": command["raw"], "guild_id": guild_id},
                                {
                                    "$set": {
                                        "id": synced_command.id,
                                        "Command": synced_command.name,
                                    }
                                },
                            )
            except Exception as e:
                continue

            except (
                TypeError,
                discord.errors.NotFound,
                discord.errors.Forbidden,
                ValueError,
            ):
                continue
            SyncedServers += 1
            await asyncio.sleep(3)

        print(f"Synced {SyncedServers} servers with custom commands")

    @staticmethod
    async def replace_variables(message, replacements):
        for placeholder, value in replacements.items():
            if value is not None:
                message = str(message).replace(placeholder, str(value))
            else:
                message = str(message).replace(placeholder, "")
        return message


class Voting(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="0", style=discord.ButtonStyle.green, emoji=f"{tick}", custom_id="vote"
    )
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        message_id = interaction.message.id

        voting = await CustomVoting.find_one({"message_id": message_id}) or {
            "votes": 0,
            "Voters": [],
        }
        if interaction.user.id in voting["Voters"]:
            await CustomVoting.update_one(
                {"message_id": message_id},
                {
                    "$inc": {"votes": -1},
                    "$pull": {"Voters": interaction.user.id},
                },
            )
            button.label = str(voting["votes"] - 1)
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"{tick} **{interaction.user.display_name},** You have successfully unvoted.",
                ephemeral=True,
            )
        else:
            await CustomVoting.update_one(
                {"message_id": message_id},
                {
                    "$inc": {"votes": 1},
                    "$push": {"Voters": interaction.user.id},
                },
                upsert=True,
            )
            button.label = str(voting["votes"] + 1)
            await interaction.message.edit(view=self)
            await interaction.followup.send(
                f"{tick} **{interaction.user.display_name},** You have successfully voted.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Voters",
        style=discord.ButtonStyle.blurple,
        emoji=f"{folder}",
        custom_id="viewlist",
    )
    async def list(self, interaction: discord.Interaction, button: discord.ui.Button):
        voting = await CustomVoting.find_one({"message_id": interaction.message.id})
        voters = voting.get("Voters", [])
        if not voters:
            voters_str = f"**{interaction.user.display_name},** there are no voters!"
        else:
            voters_str = "\n".join([f"<@{voter}> ({voter})" for voter in voters])

        embed_description = str(voters_str)[:4096]
        embed = discord.Embed(
            title="Voters",
            description=embed_description,
            color=discord.Color.dark_embed(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def has_customcommandrole2(message: discord.Message, command):
    filter = {"guild_id": message.guild.id, "name": command}
    role_data = await custom_commands.find_one(filter)

    if role_data and "permissionroles" in role_data:
        role_ids = role_data["permissionroles"]
        if not isinstance(role_ids, list):
            role_ids = [role_ids]

        if any(role.id in role_ids for role in message.author.roles):
            return True
        else:
            await message.reply(
                f"{no} **{message.author.display_name}**, you don't have permission to use this command.\n<:Arrow:1115743130461933599>**Required:** `Custom Command Permission`"
            )
            return False
    else:
        return True


async def has_customcommandrole(ctx, command):
    if isinstance(ctx, discord.Interaction):
        author = ctx.user
        send = ctx.followup.send
    else:
        author = ctx.author
        send = ctx.send

    filter = {"guild_id": ctx.guild.id, "name": command}
    role_data = await custom_commands.find_one(filter)

    if role_data and "permissionroles" in role_data:
        role_ids = role_data["permissionroles"]
        if not isinstance(role_ids, list):
            role_ids = [role_ids]

        if any(role.id in role_ids for role in author.roles):
            return True
        else:
            await send(
                f"{no} **{author.display_name}**, you don't have permission to use this command.\n<:Arrow:1115743130461933599>**Required:** `Custom Command Permission`"
            )
            return False
    else:

        return await has_admin_role(ctx)


class URL(discord.ui.View):
    def __init__(self, url, buttonname):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label=buttonname, url=url, style=discord.ButtonStyle.blurple
            )
        )


class ButtonEmbed(discord.ui.View):
    def __init__(self, name):
        super().__init__()
        self.name = name

    @discord.ui.button()
    async def button_callback(self, interaction: discord.Interaction, button):

        command = self.name
        command_data = await custom_commands.find_one(
            {"name": command, "guild_id": interaction.guild.id}
        )
        if command_data is None:
            return await interaction.response.send(
                f"{no} **{interaction.user.display_name},** That command does not exist.",
            )

        if "buttons" in command_data and command_data["buttons"] == "Link Button":
            view = URL(command_data["url"], command_data["button_label"])
        else:
            view = None

        timestamp = datetime.utcnow().timestamp()
        timestampformat = f"<t:{int(timestamp)}:F>"
        channel = interaction.channel

        replacements = {
            "{author.mention}": interaction.user.mention,
            "{author.name}": interaction.user.display_name,
            "{author.id}": str(interaction.user.id),
            "{timestamp}": timestampformat,
            "{guild.name}": interaction.guild.name if interaction.guild else "",
            "{guild.id}": str(interaction.guild.id) if interaction.guild else "",
            "{guild.owner.mention}": (
                interaction.guild.owner.mention
                if interaction.guild and interaction.guild.owner
                else ""
            ),
            "{guild.owner.name}": (
                interaction.guild.owner.display_name
                if interaction.guild and interaction.guild.owner
                else ""
            ),
            "{guild.owner.id}": (
                str(interaction.guild.owner.id)
                if interaction.guild and interaction.guild.owner
                else ""
            ),
            "{random}": int(random.randint(1, 1000000)),
            "{guild.members}": int(interaction.guild.member_count),
            "{channel.name}": channel.name if channel else interaction.channel.name,
            "{channel.id}": str(channel.id) if channel else str(interaction.channel.id),
            "{channel.mention}": (
                channel.mention if channel else interaction.channel.mention
            ),
        }

        content = await self.replace_variables(
            command_data.get("content", ""), replacements
        )
        if content == "":
            content = ""

        if "embed" in command_data and command_data["embed"]:
            embed_title = await self.replace_variables(
                command_data["title"], replacements
            )
            embed_description = await self.replace_variables(
                command_data["description"], replacements
            )
            embed_author = await self.replace_variables(
                command_data["author"], replacements
            )

            if embed_title in ["None", None]:
                embed_title = ""
            if embed_description in ["None", None]:
                embed_description = ""
            color_value = command_data.get("color", None)
            colors = (
                discord.Colour(int(color_value, 16))
                if color_value
                else discord.Colour.dark_embed()
            )

            embed = discord.Embed(
                title=embed_title, description=embed_description, color=colors
            )

            if embed_author in ["None", None]:
                embed_author = ""
            if "image" in command_data:
                embed.set_image(url=command_data["image"])
            if "thumbnail" in command_data:
                embed.set_thumbnail(url=command_data["thumbnail"])
            if "author" in command_data and "author_icon" in command_data:
                embed.set_author(
                    name=embed_author, icon_url=command_data["author_icon"]
                )

            try:
                if content or embed or view:
                    msg = await interaction.response.send_message(
                        content, embed=embed, view=view, ephemeral=True
                    )

                else:
                    await interaction.response.send_message(
                        f"{no} **{interaction.user.display_name},** This command does not have any content or embed.",
                        ephemeral=True,
                    )
                    return
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"{no} **{interaction.user.display_name},** I do not have permission to send messages in that channel.",
                    ephemeral=True,
                )
                return

        else:
            if content is None:
                await interaction.response.send_message(
                    f"{no} **{interaction.user.display_name},** That command does not have any content or embeds.",
                    ephemeral=True,
                )
                return

            try:
                if content or view:
                    msg = await interaction.response.send_message(
                        content, view=view, ephemeral=True
                    )

                else:
                    await interaction.response.send_message(
                        f"{no} **{interaction.user.display_name},** This command does not have any content or embed.",
                        ephemeral=True,
                    )
                    return
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"{no} **{interaction.user.display_name},** I do not have permission to send messages in that channel.",
                    ephemeral=True,
                )
                return

    @staticmethod
    async def replace_variables(message, replacements):
        for placeholder, value in replacements.items():
            if value is not None:
                message = str(message).replace(placeholder, str(value))
            else:
                message = str(message).replace(placeholder, "")
        return message


async def setup(client: commands.Bot) -> None:
    await client.add_cog(CustomCommands(client))
