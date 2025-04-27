import discord
from discord.ext import commands
from datetime import timedelta
from discord import app_commands
from discord.ext import tasks
from utils.emojis import *
from utils.ui import BasicPaginator
import os


from datetime import datetime



from utils.HelpEmbeds import (
    BotNotConfigured,
    NoPermissionChannel,
    ChannelNotFound,
    ModuleNotEnabled,
    NoChannelSet,
    Support,
    ModuleNotSetup,
)

from utils.permissions import has_admin_role, has_staff_role

environment = os.getenv("ENVIRONMENT")


class LOAModule(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    # TODO: Rewrite LOA's for V1.46.0

    @commands.hybrid_group()
    async def loa(self, ctx: commands.Context):
        return

    @loa.command(description="Request a leave of absence")
    async def request(
        self, ctx: commands.Context, duration: str, reason: str, start: str = None
    ):
        return

    @loa.command(description="Manage a staff's leave of absence")
    async def admin(self, ctx: commands.Context, user: discord.User):
        return

    @loa.command(description="Manage your own leave of absence")
    async def manage(self, ctx: commands.Context):
        if not await has_staff_role(ctx):
            return
        ActiveLOA = await self.client.db["loa"].find_one(
            {"user": ctx.author.id, "guild_id": ctx.guild.id, "active": True}
        )
        PastLOAs = (
            await self.client.db["loa"]
            .find({"user": ctx.author.id, "guild_id": ctx.guild.id, "active": False})
            .to_list(length=750)
        )

        view = LOAManage(ctx.author, ctx.author)
        embed = discord.Embed(color=discord.Color.dark_embed())

        view.PLOA.label = f"Past LOA's ({len(PastLOAs)})"
        if len(PastLOAs) > 0:
            view.PLOA.disabled = False

        if ActiveLOA:
            embed.add_field(
                name="Current LOA",
                value=f"> **Duration:** <t:{int(ActiveLOA.get('start_time').timestamp())}:D> - <t:{int(ActiveLOA.get('end_time').timestamp())}:D>\n> **Reason:** {ActiveLOA.get('reason')}",
            )

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


async def setup(client: commands.Bot) -> None:
    await client.add_cog(LOAModule(client))


class LOAManage(discord.ui.View):
    def __init__(self, author: discord.Member, target: discord.User = None):
        super().__init__(timeout=960)
        self.author = author
        self.target = target

    @discord.ui.button(label="Request Extension", style=discord.ButtonStyle.green)
    async def RequestExt(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        return

    @discord.ui.button(label="Reduce Time", style=discord.ButtonStyle.red)
    async def ReduceT(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        return

    @discord.ui.button(label="End", style=discord.ButtonStyle.blurple)
    async def End(self, interaction: discord.Interaction, button: discord.ui.Button):
        return

    @discord.ui.button(
        label="Past LOA's (0)", style=discord.ButtonStyle.blurple, disabled=True
    )
    async def PLOA(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        PastLOAs = (
            await interaction.client.db["loa"]
            .find(
                {
                    "user": self.target.id,
                    "guild_id": interaction.guild.id,
                    "active": False,
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
                    name=f"<t:{int(loa.get('start_time').timestamp())}:D> - <t:{int(loa.get('end_time').timestamp())}:D>",
                    value=f"> **Reason:** {loa.get('reason')}\n{A}",
                    inline=False,
                )
            pages.append(embed)

        paginator = BasicPaginator(author=interaction.user, embeds=pages)
        await interaction.followup.send(embed=pages[0], view=paginator, ephemeral=True)


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
