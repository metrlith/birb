import discord
from discord.ext import commands
from discord import app_commands
from motor.motor_asyncio import AsyncIOMotorClient
import os
from utils.emojis import *
import typing
import utils.Paginator as Paginator
from utils.Module import ModuleCheck

# MONGO_URL = os.getenv("MONGO_URL")
# mongo = AsyncIOMotorClient(MONGO_URL)
# db = mongo["astro"]
# connectionroles = db["connectionroles"]


class ConnectionRoles(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.hybrid_group()
    async def connectionrole(self, ctx: commands.Context):
        pass

    async def tag_name_autocompletion(
        ctx: commands.Context, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        try:
            filter = {"guild": interaction.guild_id}

            tag_names = await interaction.client.db['connectionroles'].distinct("name", filter)

            filtered_names = [
                name for name in tag_names if current.lower() in name.lower()
            ]
            filtered_names = filtered_names[:25]

            choices = [
                app_commands.Choice(name=name, value=name) for name in filtered_names
            ]

            return choices
        except Exception as e:
            print(e)

    @connectionrole.command(
        name="sync", description="Sync connection roles to all members"
    )
    @commands.cooldown(1, 3600, commands.BucketType.guild)
    @app_commands.checks.has_permissions(manage_roles=True)
    @commands.has_guild_permissions(manage_roles=True)
    async def sync(self, ctx: commands.Context):
        if not await ModuleCheck(ctx.guild.id, "connectionroles"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the connection roles module isn't enabled.",
            )
            return

        await ctx.defer()
        roleresult = await self.client.db['connectionroles'].find({"guild": ctx.guild.id}).to_list(
            length=100000
        )
        if len(roleresult) == 0:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, There are no connection roles.",
            )
            return
        if not ctx.guild.chunked:
            await ctx.guild.chunk()

        total_members = len(ctx.guild.members)
        updated_members = 0
        msg = await ctx.send(
            f"<a:astroloading:1245681595546079285> Syncing connection roles..."
        )

        for role in roleresult:
            child_id = role["child"]
            parent_id = role["parent"]
            child_role = ctx.guild.get_role(child_id)
            parent_role = ctx.guild.get_role(parent_id)
            if child_role and parent_role:
                for i, member in enumerate(ctx.guild.members):
                    if parent_role in member.roles:
                        if child_role not in member.roles:
                            try:
                                await member.add_roles(child_role)
                                updated_members += 1
                                print(
                                    f"[Connection Roles] Added {child_role.name} to {member.display_name}."
                                )
                            except discord.Forbidden:
                                await ctx.send(
                                    f"{no} **{ctx.author.display_name}**, I don't have permission to add the role to {member.mention}.",
                                )
                                return
                            except discord.HTTPException:
                                await ctx.send(
                                    f"{no} **{ctx.author.display_name}**, An error occurred while adding the role to {member.mention}.",
                                )
                                return

                    if i % 10 == 0:
                        await msg.edit(
                            content=f"<a:astroloading:1245681595546079285> Syncing connection roles... {i}/{total_members} members processed."
                        )
                break
        await msg.edit(
            content=f"{tick} **{ctx.author.display_name}**, Connection roles have been synced. {updated_members}/{total_members} members updated."
        )

    @connectionrole.command(
        name="add", description="Add a connection role to your server"
    )
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.describe(
        parent="Will automatically assign this role once they recieve a child role.",
        child="Automatically assigns the parent role if they are given the child role.",
    )
    async def connectionrole_add(
        self, ctx: commands.Context, parent: discord.Role, child: discord.Role
    ):
        if not await ModuleCheck(ctx.guild.id, "connectionroles"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the connection roles module isn't enabled.",
            )
            return
        if parent == child:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, The parent and child roles cannot be the same.",
            )
            return

        await self.client.db['connectionroles'].insert_one(
            {
                "guild": ctx.guild.id,
                "parent": child.id,
                "child": parent.id,
                "name": child.name,
            }
        )
        await ctx.send(
            f"{tick} **{ctx.author.display_name}**, The connection role has been added."
        )

    @connectionrole.command(
        name="remove", description="Remove a connection role from your server"
    )
    @app_commands.autocomplete(name=tag_name_autocompletion)
    @commands.has_guild_permissions(manage_roles=True)
    @app_commands.describe(name="The name of the connection role")
    async def connectionrole_remove(self, ctx: commands.Context, name):
        if not await ModuleCheck(ctx.guild.id, "connectionroles"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the connection roles module isn't enabled.",
            )
            return
        roleresult = await self.client.db['connectionroles'].find_one(
            {"guild": ctx.guild.id, "name": name}
        )
        if roleresult is None:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, The connection role does not exist.",
            )
            return

        await self.client.db['connectionroles'].delete_many({"guild": ctx.guild.id, "name": name})
        await ctx.send(
            f"{tick} **{ctx.author.display_name}**, The connection role has been removed.",
        )

    @connectionrole.command(
        name="list", description="List all connection roles in your server"
    )
    @commands.has_guild_permissions(manage_roles=True)
    async def connectionrole_list(self, ctx: commands.Context):
        if not await ModuleCheck(ctx.guild.id, "connectionroles"):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, the connection roles module isn't enabled.",
            )
            return

        roleresult = await self.client.db['connectionroles'].find({"guild": ctx.guild.id}).to_list(
            length=100000
        )
        if len(roleresult) == 0:
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, There are no connection roles.",
            )
            return

        if os.getenv('ENVIRONMENT') == "custom":
            msg = await ctx.send(
                embed=discord.Embed(description="Loading...", color=discord.Color.dark_embed())
            )

        else:
            msg = await ctx.send(
                embed=discord.Embed(
                    description="<a:astroloading:1245681595546079285>",
                    color=discord.Color.dark_embed(),
                )
            )

        grouped_roles = {}
        for role in roleresult:
            child_id = role["child"]
            parent_id = role["parent"]
            child_role = ctx.guild.get_role(child_id)
            parent_role = ctx.guild.get_role(parent_id)
            if child_role and parent_role:
                if child_id not in grouped_roles:
                    grouped_roles[child_id] = []
                grouped_roles[child_id].append(parent_id)

        MAX_FIELDS_PER_PAGE = 9
        embeds = []
        current_embed = None
        description = "<:suggestion:1207370004379607090> **What?**\n> The bot will automatically assign the parent role to a user once they get the child role.\n\n"

        for idx, (child_id, parent_ids) in enumerate(grouped_roles.items()):
            if idx % MAX_FIELDS_PER_PAGE == 0:
                if description:
                    current_embed = discord.Embed(
                        title="Connection Roles",
                        description=description,
                        color=discord.Color.dark_embed(),
                    )
                    current_embed.set_thumbnail(url=ctx.guild.icon)
                    current_embed.set_author(
                        name=ctx.guild.name, icon_url=ctx.guild.icon
                    )
                    embeds.append(current_embed)
                    description = ""

            parent_roles_str = "\n".join(
                f"* <@&{parent_id}>" for parent_id in parent_ids
            )
            description += f"**<@&{child_id}>**\n{parent_roles_str}\n\n"

        if description:
            current_embed = discord.Embed(
                title="Connection Roles",
                description=description,
                color=discord.Color.dark_embed(),
            )
            current_embed.set_thumbnail(url=ctx.guild.icon)
            current_embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon)
            embeds.append(current_embed)

        PreviousButton = discord.ui.Button(emoji="<:chevronleft:1220806425140531321>")
        NextButton = discord.ui.Button(emoji="<:chevronright:1220806430010118175>")
        FirstPageButton = discord.ui.Button(emoji="<:chevronsleft:1220806428726661130>")
        LastPageButton = discord.ui.Button(emoji="<:chevronsright:1220806426583371866>")
        InitialPage = 0
        timeout = 42069

        paginator = Paginator.Simple(
            PreviousButton=PreviousButton,
            NextButton=NextButton,
            FirstEmbedButton=FirstPageButton,
            LastEmbedButton=LastPageButton,
            InitialPage=InitialPage,
            timeout=timeout,
        )

        await paginator.start(ctx, pages=embeds, msg=msg)

    @connectionrole_add.error
    @connectionrole_remove.error
    @connectionrole_list.error
    @sync.error
    async def permissionerror(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, you can only use this command once every hour.",
            )
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"{no} **{ctx.author.display_name}**, you don't have permission to configure connection roles.\n<:Arrow:1115743130461933599>**Required:** ``Manage Roles``",
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ConnectionRoles(client))
