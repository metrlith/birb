import discord
from discord.ext import commands
from datetime import timedelta
from discord import app_commands
from discord.ext import tasks
from utils.emojis import *
import string
import random
from utils.ui import BasicPaginator
import os


from datetime import datetime


# from utils.HelpEmbeds import (
#     BotNotConfigured,
#     NoPermissionChannel,
#     ChannelNotFound,
#     ModuleNotEnabled,
#     NoChannelSet,
#     Support,
#     ModuleNotSetup,
#     NotYourPanel,

# )
import utils.HelpEmbeds as HelpEmbeds

from utils.permissions import has_admin_role, has_staff_role
from utils.format import strtotime

environment = os.getenv("ENVIRONMENT")


async def CurrentLOA(
    ctx: commands.Context, loa: dict, user: discord.User = None
) -> discord.Embed:

    if not isinstance(ctx, commands.Context):
        author = ctx.user
    else:
        author = ctx.author
    embed = discord.Embed(color=discord.Color.dark_embed())
    embed.set_author(name="Leave Manage")
    embed.set_footer(text=f"@{author.name}", icon_url=author.display_avatar)

    if not loa:
        return "N/A"

    if not loa.get("start_time"):
        return "N/A"

    if user is None:
        user = ctx.author

    if loa.get("Accepted"):
        A = f"> **Accepted:** by <@{loa.get('Accepted').get('user')}> at <t:{int(loa.get('Accepted').get('time').timestamp())}:R>\n"
    else:
        A = ""

    embed.add_field(
        name="Current LOA",
        value=(
            f"> **Duration:** {await Duration(loa)}\n"
            f"> **Reason:** {loa.get('reason')}\n{A}"
        ),
    )
    embed.set_thumbnail(url=user.display_avatar)
    embed.set_footer(text=f"@{user.name}", icon_url=user.display_avatar)
    return embed


async def Duration(loa: dict) -> str:
    if not loa:
        return "N/A"

    Added = 0
    if loa.get("AddedTime") is not None:
        if loa["AddedTime"].get("RequestExt") is not None:
            if loa["AddedTime"]["RequestExt"].get("status", "Rejected") == "Accepted":
                Added = int(loa["AddedTime"].get("Time", 0))
        else:
            Added = int(loa["AddedTime"].get("Time", 0))

    Removed = 0
    if loa.get("RemovedTime") is not None and loa["RemovedTime"].get("Time", 0) > 0:
        Removed = int(loa["RemovedTime"].get("Time", 0))

    if not loa.get("start_time"):
        return "N/A"
    return f"<t:{int(loa.get('start_time').timestamp())}:D> - <t:{int(loa.get('end_time').timestamp()) - (Removed - Added)}:D>"


class LOAModule(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    # TODO: Rewrite LOA's for V1.46.0

    @commands.hybrid_group()
    async def loa(self, ctx: commands.Context):
        return

    @loa.command(description="View past leave of absences")
    async def history(self, ctx: commands.Context):
        if not await has_staff_role(ctx):
            return

        LOA = (
            await self.client.db["loa"]
            .find(
                {
                    "user": ctx.author.id,
                    "guild_id": ctx.guild.id,
                    "active": False,
                    "request": False,
                }
            )
            .to_list(length=1000)
        )

        if len(LOA) == 0:
            await ctx.send(embed=HelpEmbeds.CustomError("No past LOAs."))
            return

        pages = []
        for i in range(0, len(LOA), 10):
            chunk = LOA[i : i + 10]
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(name="Past LOAs")
            embed.set_footer(text=f"Page {i // 10 + 1} of {len(LOA) // 10 + 1}")
            for loa in chunk:
                if not loa.get("LoaID"):
                    continue
                embed.add_field(
                    name=f"@{loa.get('ExtendedUser').get('name')}",
                    value=(
                        f"> **ID:** `{loa.get('LoaID')}`\n"
                        f"> **Duration:** {await Duration(loa)}\n"
                        f"> **Reason:** {loa.get('reason')}\n"
                    ),
                    inline=False,
                )

            pages.append(embed)

        paginator = BasicPaginator(author=ctx.author, embeds=pages)
        await ctx.send(embed=pages[0], view=paginator)

    @loa.command(description="View active leave of absences")
    async def active(self, ctx: commands.Context):
        if not await has_staff_role(ctx):
            return

        LOA = (
            await self.client.db["loa"]
            .find(
                {
                    "guild_id": ctx.guild.id,
                    "request": False,
                    "active": True,
                }
            )
            .to_list(length=1000)
        )

        if len(LOA) == 0:
            await ctx.send(embed=HelpEmbeds.CustomError("No active LOAs."))
            return

        pages = []
        for i in range(0, len(LOA), 1):
            chunk = LOA[i : i + 1]
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(name="Active LOAs")
            embed.set_footer(text=f"Page {i // 1 + 1} of {len(LOA) // 1 + 1}")
            for loa in chunk:
                if not loa.get("LoaID"):
                    continue
                embed.add_field(
                    name=f"@{loa.get('ExtendedUser').get('name')}",
                    value=(
                        f"> **ID:** `{loa.get('LoaID')}`\n"
                        f"> **Duration:** <t:{int(loa.get('start_time').timestamp())}:D> - <t:{int(loa.get('end_time').timestamp())}:D>\n"
                        f"> **Reason:** {loa.get('reason')}\n"
                    ),
                    inline=False,
                )
                embed.set_footer(text=loa.get("LoaID"))
            pages.append(embed)

        paginator = BasicPaginator(author=ctx.author, embeds=pages)
        await ctx.send(embed=pages[0], view=paginator)

    @loa.command(description="View pending leave of absence requests")
    async def pending(self, ctx: commands.Context):

        if not await has_staff_role(ctx):
            return

        LOA = (
            await self.client.db["loa"]
            .find(
                {
                    "guild_id": ctx.guild.id,
                    "request": True,
                    "active": False,
                }
            )
            .to_list(length=1000)
        )

        if len(LOA) == 0:
            await ctx.send(embed=HelpEmbeds.CustomError("No pending LOA requests."))
            return

        pages = []
        for i in range(0, len(LOA), 1):
            chunk = LOA[i : i + 1]
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_author(name="Pending LOA Requests")
            embed.set_footer(text=f"Page {i // 1 + 1} of {len(LOA) // 1 + 1}")
            for loa in chunk:
                if not loa.get("LoaID"):
                    continue
                embed.add_field(
                    name=f"@{loa.get('ExtendedUser').get('name')}",
                    value=(
                        f"> **ID:** `{loa.get('LoaID')}`\n"
                        f"> **Duration:** <t:{int(loa.get('start_time').timestamp())}:D> - <t:{int(loa.get('end_time').timestamp())}:D>\n"
                        f"> **Reason:** {loa.get('reason')}\n"
                    ),
                    inline=False,
                )
                embed.set_footer(text=loa.get("LoaID"))
            pages.append(embed)

        Act = PendingActions(ctx.author)

        paginator = BasicPaginator(author=ctx.author, embeds=pages)
        paginator.add_item(Act.Accept)
        paginator.add_item(Act.Decline)

        await ctx.send(embed=pages[0], view=paginator)

    @loa.command(description="Request a leave of absence")
    async def request(
        self, ctx: commands.Context, duration: str, reason: str, start: str = None
    ):
        if not await has_staff_role(ctx):
            return

        Already = await self.client.db["loa"].find_one(
            {
                "user": ctx.author.id,
                "guild_id": ctx.guild.id,
                "active": True,
            }
        )
        if Already:
            await ctx.send(
                content=f"{no} **{ctx.author.display_name},** you already have an active LOA. Please end it before requesting a new one."
            )
            return

        Start = datetime.now()
        S = False
        if start:
            S = True
            Start = await strtotime(start, back=True)
        Duration = await strtotime(duration, back=False)

        if Duration < datetime.now():
            await ctx.send(
                embed=HelpEmbeds.CustomError("The duration must be in the future.")
            )
            return

        if Duration > datetime.now() + timedelta(days=1000):
            await ctx.send(embed=HelpEmbeds.CustomError("The duration is too long."))
            return
        if Duration < datetime.now() + timedelta(days=1):
            await ctx.send(
                embed=HelpEmbeds.CustomError("The duration must be at least 1 day.")
            )
            return

        MSG = await ctx.send(
            f"<a:Loading:1167074303905386587> **{ctx.author.display_name},** requesting LOA..."
        )
        R = await self.client.db["loa"].insert_one(
            {
                "LoaID": "".join(
                    random.choices(string.ascii_letters + string.digits, k=8)
                ),
                "user": ctx.author.id,
                "ExtendedUser": {
                    "id": ctx.author.id,
                    "name": ctx.author.name,
                    "thumbnail": (
                        ctx.author.display_avatar.url
                        if ctx.author.display_avatar
                        else None
                    ),
                },
                "guild_id": ctx.guild.id,
                "start_time": Start,
                "end_time": Duration,
                "reason": reason,
                "active": False,
                "request": True,
                "scheduled": S,
                "AddedTime": {
                    "Time": 0,
                    "Reason": None,
                    "RequestExt": None,
                    "Log": [],
                },
                "RemovedTime": {
                    "Duration": 0,
                    "Log": [],
                },
            }
        )
        if not R.acknowledged:
            await MSG.edit(
                embed=HelpEmbeds.CustomError("Failed to request LOA."),
                content=None,
            )
            return
        self.client.dispatch(
            "loa_request",
            R.inserted_id,
        )
        try:
            await MSG.edit(
                content=(
                    f"{tick} **{ctx.author.display_name},** loa requested. Please wait for a staff member to accept it."
                ),
                embed=None,
            )
        except (discord.HTTPException, discord.Forbidden):
            await ctx.send(
                content=(
                    f"{tick} **{ctx.author.display_name},** loa requested. Please wait for a staff member to accept it."
                ),
                embed=None,
            )

    @loa.command(description="Manage your own leave of absence")
    async def manage(self, ctx: commands.Context):
        if not await has_staff_role(ctx):
            return
        ActiveLOA = await self.client.db["loa"].find_one(
            {
                "user": ctx.author.id,
                "guild_id": ctx.guild.id,
                "active": True,
                "request": False,
                "start_time": {"$lt": datetime.now()},
            }
        )
        PastLOAs = (
            await self.client.db["loa"]
            .find(
                {
                    "user": ctx.author.id,
                    "guild_id": ctx.guild.id,
                    "active": False,
                    "request": False,
                }
            )
            .to_list(length=750)
        )

        view = LOAManage(ctx.author, ctx.author, True)
        embed = discord.Embed(color=discord.Color.dark_embed())

        view.PLOA.label = f"Past LOA's ({len(PastLOAs)})"
        if len(PastLOAs) > 0:
            view.PLOA.disabled = False

        if ActiveLOA:
            embed = await CurrentLOA(ctx, ActiveLOA)

        else:
            embed.add_field(
                name="Current LOA",
                value="> You currently have no active LOA. To request one, use `/loa request`",
            )

            view.remove_item(view.RequestExt)
            view.remove_item(view.ReduceT)
            view.remove_item(view.End)

        embed.set_thumbnail(url=ctx.author.display_avatar)
        embed.set_author(name="Leave Manage")
        embed.set_footer(text=f"@{ctx.author.name}", icon_url=ctx.author.display_avatar)
        await ctx.send(embed=embed, view=view)

    @loa.command(description="Manage a staff's leave of absence")
    @app_commands.describe(user="The user to manage")
    async def admin(self, ctx: commands.Context, user: discord.User):
        if not await has_staff_role(ctx):
            return
        ActiveLOA = await self.client.db["loa"].find_one(
            {
                "user": user.id,
                "guild_id": ctx.guild.id,
                "active": True,
                "request": False,
                "start_time": {"$lt": datetime.now()},
            }
        )
        PastLOAs = (
            await self.client.db["loa"]
            .find({"user": user.id, "guild_id": ctx.guild.id, "active": False})
            .to_list(length=750)
        )

        view = LOAManage(ctx.author, user)
        embed = discord.Embed(color=discord.Color.dark_embed())

        view.PLOA.label = f"Past LOA's ({len(PastLOAs)})"
        if len(PastLOAs) > 0:
            view.PLOA.disabled = False

        if ActiveLOA:
            embed = await CurrentLOA(ctx, ActiveLOA, user)

        else:
            embed.add_field(
                name="Current LOA",
                value="> They have no active LOA.",
            )

            view.remove_item(view.RequestExt)
            view.remove_item(view.ReduceT)
            view.remove_item(view.End)

        view.RequestExt.label = "Add Time"
        embed.set_thumbnail(url=ctx.author.display_avatar)
        embed.set_author(name="Leave Admin")
        embed.set_footer(text=f"@{ctx.author.name}", icon_url=ctx.author.display_avatar)
        await ctx.send(embed=embed, view=view)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(LOAModule(client))


class LOAManage(discord.ui.View):
    def __init__(
        self,
        author: discord.Member,
        target: discord.User = None,
        ExtRequest: bool = False,
    ):
        super().__init__(timeout=960)
        self.author = author
        self.target = target
        self.ExtRequest = ExtRequest

    @discord.ui.button(label="Request Extension", style=discord.ButtonStyle.green)
    async def RequestExt(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return
        await interaction.response.send_modal(
            AddTime(author=self.author, target=self.target, RequestExt=self.ExtRequest)
        )

    @discord.ui.button(label="Reduce Time", style=discord.ButtonStyle.red)
    async def ReduceT(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return

        await interaction.response.send_modal(
            RemoveTime(author=self.author, target=self.target)
        )

    @discord.ui.button(label="End", style=discord.ButtonStyle.blurple)
    async def End(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                ephemeral=True, embed=HelpEmbeds.NotYourPanel()
            )
            return

        await interaction.response.defer(ephemeral=True)
        Already = await interaction.client.db["loa"].find_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            }
        )
        if Already is None:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("You have no active LOA."), ephemeral=True
            )
            return

        Z = await interaction.client.db["loa"].update_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            },
            {
                "$set": {
                    "end_time": datetime.now(),
                    "active": False,
                }
            },
        )
        if Z.modified_count == 0:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("Failed to end LOA."), ephemeral=True
            )
            return
        interaction.client.dispatch(
            "loa_end",
            Already.get("_id"),
            self.target.id,
        )
        interaction.client.dispatch("loa_log", Already.get("_id"), "End")

        await interaction.edit_original_response(
            content=(
                f"{tick} **{interaction.user.display_name}**, I've ended `@{self.target.name}'s` LOA."
                if self.target == self.author
                else f"{tick} **{interaction.user.display_name}**, I've ended your LOA."
            ),
            embed=None,
            view=None,
        )

    @discord.ui.button(
        label="Past LOA's (0)", style=discord.ButtonStyle.blurple, disabled=True
    )
    async def PLOA(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                ephemeral=True, embed=HelpEmbeds.NotYourPanel()
            )
            return

        await interaction.response.defer(ephemeral=True)
        PastLOAs = (
            await interaction.client.db["loa"]
            .find(
                {
                    "user": self.target.id,
                    "guild_id": interaction.guild.id,
                    "active": False,
                    "request": False,
                }
            )
            .to_list(length=750)
        )
        if len(PastLOAs) == 0:
            await interaction.followup.send("You have no past LOA's.", ephemeral=True)
            return

        pages = []
        for i in range(0, len(PastLOAs), 10):
            chunk = PastLOAs[i : i + 10]
            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_thumbnail(url=self.target.display_avatar)
            embed.set_author(name="Leave Manage")
            embed.set_footer(
                text=f"@{self.target.name}", icon_url=self.target.display_avatar
            )
            for loa in chunk:
                A = ""
                if loa.get("Accepted"):
                    A = f"> **Accepted:** by <@{loa.get('Accepted').get('user')}> at <t:{int(loa.get('Accepted').get('time').timestamp())}:R>\n"

                embed.add_field(
                    name=await Duration(loa),
                    value=f"> **Reason:** {loa.get('reason')}\n{A}",
                    inline=False,
                )
            pages.append(embed)

        paginator = BasicPaginator(author=interaction.user, embeds=pages)
        await interaction.followup.send(embed=pages[0], view=paginator, ephemeral=True)


class RemoveTime(discord.ui.Modal):
    def __init__(self, author: discord.Member, target: discord.User = None):
        super().__init__(title="Remove Time")
        self.author = author
        self.target = target

        self.duration = discord.ui.TextInput(
            label="Duration",
            placeholder="1d 2h 30m",
            required=True,
            max_length=20,
        )
        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction):

        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return

        if self.target is None:
            self.target = interaction.user
        try:
            Duration = await strtotime(self.duration.value, Interger=True)
        except (ValueError, TypeError, AttributeError):
            await interaction.response.send_message(
                embed=HelpEmbeds.CustomError("Invalid duration format."), ephemeral=True
            )
        except OverflowError:
            await interaction.response.send_message(
                embed=HelpEmbeds.CustomError("The duration is too long."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        Already = await interaction.client.db["loa"].find_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            }
        )
        Z = await interaction.client.db["loa"].update_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            },
            {
                "$set": {
                    "RemovedTime.Time": Already.get("RemovedTime", {}).get("Time", 0)
                    + Duration,
                    "RemovedTime.Log": Already.get("RemovedTime", {}).get("Log", [])
                    + [
                        {
                            "time": datetime.now(),
                            "duration": Duration,
                            "user": interaction.user.id,
                        }
                    ],
                }
            },
        )
        if Z.modified_count == 0:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("Failed to add time."), ephemeral=True
            )
            return

        await interaction.followup.send(
            content=(
                f"{tick} **{interaction.user.display_name}**, I've removed `{self.duration.value}` from `@{self.target.name}'s` LOA."
                if self.target == self.author
                else f"{tick} **{interaction.user.display_name}**, I've added `{self.duration.value}` to your LOA."
            ),
            ephemeral=True,
        )
        interaction.client.dispatch(
            "loa_log",
            Already.get("_id"),
            "RemoveTime",
            {
                "time": datetime.now(),
                "duration": Duration,
                "user": interaction.user.id,
            },
        )
        await interaction.edit_original_response(
            embed=await CurrentLOA(ctx=interaction, loa=Already, user=self.target),
        )


class AddTime(discord.ui.Modal):
    def __init__(
        self, author: discord.Member, target: discord.User = None, RequestExt=False
    ):
        super().__init__(title="Add Time" if not RequestExt else "Request Extension")
        self.author = author
        self.target = target
        self.RequestExt = RequestExt

        self.duration = discord.ui.TextInput(
            label="Duration",
            placeholder="1d 2h 30m",
            required=True,
            max_length=20,
        )
        self.add_item(self.duration)

        if RequestExt:
            self.reason = discord.ui.TextInput(
                label="Reason",
                placeholder="Why are you requesting this extension?",
                required=True,
                max_length=200,
            )
            self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return

        if self.target is None:
            self.target = interaction.user
        try:
            Duration = await strtotime(self.duration.value, Interger=True)
        except (ValueError, TypeError, AttributeError):
            await interaction.response.send_message(
                embed=HelpEmbeds.CustomError("Invalid duration format."), ephemeral=True
            )
        except OverflowError:
            await interaction.response.send_message(
                embed=HelpEmbeds.CustomError("The duration is too long."),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        Already = await interaction.client.db["loa"].find_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            }
        )
        Z = await interaction.client.db["loa"].update_one(
            {
                "user": self.target.id,
                "guild_id": interaction.guild.id,
                "active": True,
            },
            {
                "$set": {
                    "AddedTime.Time": Already.get("AddedTime", {}).get("Time", 0)
                    + Duration,
                    "AddedTime.Reason": (
                        self.reason.value if hasattr(self, "reason") else None
                    ),
                    "AddedTime.RequestExt": (
                        {"status": "Pending", "acceptedBy": None, "AcceptedAt": None}
                        if self.RequestExt
                        else None
                    ),
                    "AddedTime.Log": Already.get("AddedTime", {}).get("Log", [])
                    + [
                        {
                            "time": datetime.now(),
                            "duration": Duration,
                            "user": interaction.user.id,
                            "ExtRequest": self.RequestExt,
                            "reason": (
                                self.reason.value if hasattr(self, "reason") else None
                            ),
                        }
                    ],
                }
            },
        )
        if Z.modified_count == 0:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("Failed to add time."), ephemeral=True
            )
            return

        if self.RequestExt:
            await interaction.client.dispatch(
                "loa_request_ext",
                Z.modified_id,
                self.target.id,
            )
            await interaction.followup.send(
                content=f"{tick} **{interaction.user.display_name}**, I've requested an extension for `{self.duration.value}` on your LOA.",
                ephemeral=True,
            )
            return
        else:
            interaction.client.dispatch(
                "loa_log",
                Already.get("_id"),
                "AddTime",
                {
                    "time": datetime.now(),
                    "duration": Duration,
                    "user": interaction.user.id,
                },
            )
            Already = await interaction.client.db["loa"].find_one(
                {
                    "user": self.target.id,
                    "guild_id": interaction.guild.id,
                    "active": True,
                }
            )
            await interaction.edit_original_response(
                embed=await CurrentLOA(ctx=interaction, loa=Already, user=self.target),
            )
            await interaction.followup.send(
                content=(
                    f"{tick} **{interaction.user.display_name}**, I've added `{self.duration.value}` to `@{self.target.name}'s` LOA."
                    if self.target == self.author
                    else f"{tick} **{interaction.user.display_name}**, I've added `{self.duration.value}` to your LOA."
                ),
                ephemeral=True,
            )


class PendingActions(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=960)
        self.author = author

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, row=0)
    async def Accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        embed = interaction.message.embeds[0]

        Already = await interaction.client.db["loa"].find_one(
            {
                "LoaID": embed.footer.text,
            }
        )
        if Already is None:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("This isn't a valid LOA Request"),
                ephemeral=True,
            )
            return

        Z = await interaction.client.db["loa"].update_one(
            {
                "LoaID": embed.footer.text,
                "guild_id": interaction.guild.id,
                "active": False,
                "request": True,
            },
            {
                "$set": {
                    "Accepted": {
                        "user": interaction.user.id,
                        "time": datetime.now(),
                    },
                    "active": True,
                    "request": False,
                }
            },
        )
        if Z.modified_count == 0:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("Failed to accept LOA."), ephemeral=True
            )
            return
        interaction.client.dispatch(
            "loa_accept",
            Already.get("_id"),
        )
        await interaction.followup.send(
            content=(
                f"{tick} **{interaction.user.display_name}**, I've accepted `@{Already.get('ExtendedUser', {}).get('name', 'N/A')}'s` LOA."
            ),
            ephemeral=True,
        )

        await interaction.edit_original_response(
            embed=discord.Embed(
                color=discord.Color.green(),
            ),
            view=self.remove_item(self.Accept)
            .remove_item(self.Decline)
            .add_item(
                discord.ui.Button(
                    label="Accepted",
                    style=discord.ButtonStyle.green,
                    disabled=True,
                )
            ),
        )

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, row=0)
    async def Decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.user.id == self.author.id:
            await interaction.response.send_message(
                embed=HelpEmbeds.NotYourPanel(), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        embed = interaction.message.embeds[0]

        Already = await interaction.client.db["loa"].find_one(
            {
                "LoaID": embed.footer.text,
                "guild_id": interaction.guild.id,
                "active": False,
                "request": True,
            }
        )
        if Already is None:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("This isn't a valid LOA Request"),
                ephemeral=True,
            )
            return

        Z = await interaction.client.db["loa"].update_one(
            {
                "LoaID": embed.footer.text,
                "guild_id": interaction.guild.id,
                "active": False,
                "request": True,
            },
            {
                "$set": {
                    "Accepted": None,
                    "active": False,
                    "request": False,
                }
            },
        )
        if Z.modified_count == 0:
            await interaction.followup.send(
                embed=HelpEmbeds.CustomError("Failed to decline LOA."), ephemeral=True
            )
            return
        await interaction.client.dispatch(
            "loa_decline",
            Already.get("_id"),
        )
        await interaction.followup.send(
            content=(
                f"{tick} **{interaction.user.display_name}**, I've declined `@{Already.get('ExtendedUser', {}).get('name', 'N/A')}'s` LOA."
            ),
            ephemeral=True,
        )

        await interaction.edit_original_response(
            embed=discord.Embed(
                color=discord.Color.red(),
            ),
            view=self.remove_item(self.Accept)
            .remove_item(self.Decline)
            .add_item(
                discord.ui.Button(
                    label="Declined",
                    style=discord.ButtonStyle.red,
                    disabled=True,
                )
            ),
        )


# class LOAContainer(discord.ui.Container):
#     def __init__(self):
#         super().__init__(id=1)
#         text = discord.ui.TextDisplay("## <:LOA:1223063170856390806> Leave Manage")
#         self.add_item(text)
#         sep = discord.ui.Separator()
#         self.add_item(sep)
#         load_description = discord.ui.TextDisplay(
#             "**Active LOA**\n> **Duration**: <t:{int(CurrentLOA.get('start_time').timestamp())}> - <t:{int(CurrentLOA.get('end_time').timestamp())}>\n> **Reason:** {CurrentLOA.get('reason')}\n"
#         )
#         self.add_item(load_description)
#         sep2 = discord.ui.Separator()
#         self.add_item(sep2)
#         action_row = discord.ui.ActionRow()

#         @action_row.button(label="Extension Request", style=discord.ButtonStyle.green)
#         async def extension_request(interaction: discord.Interaction, button):
#             await interaction.response.send_message("Extension request initiated.")

#         @action_row.button(label="Reduce Time", style=discord.ButtonStyle.red)
#         async def reduce_time(interaction: discord.Interaction, button):
#             await interaction.response.send_message("Time reduction initiated.")

#         @action_row.button(label="End", style=discord.ButtonStyle.red)
#         async def end_loa(interaction: discord.Interaction, button):
#             await interaction.response.send_message("LOA ended.")

#         @action_row.button(label="LOA History", style=discord.ButtonStyle.blurple)
#         async def loa_history(interaction: discord.Interaction, button):
#             await interaction.response.send_message("Displaying LOA history.")

#         self.add_item(action_row)


# class LOAManage(discord.ui.LayoutView):
#         def __init__(self, *, timeout = 180):
#             super().__init__(timeout=timeout)
#             self.add_item(LOAContainer())
