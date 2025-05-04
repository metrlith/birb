import discord
from discord.ext import commands
import psutil
from utils.emojis import *

class management(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command()
    @commands.is_owner()
    async def account(self, ctx: commands.Context, user: discord.User):
        await ctx.defer()
        
        premiumresult = await self.client.db['premium'].find_one({"user_id": user.id})
        blacklistsresult = await self.client.db['blacklists'].find_one({"user": user.id})

        premiums = tick if premiumresult else no
        blacklistss = tick if blacklistsresult else no
        
        view = ManageAccount(ctx.author, user)
        view.premium.style = discord.ButtonStyle.green if premiumresult else discord.ButtonStyle.red
        view.blacklisted.style = discord.ButtonStyle.green if blacklistsresult else discord.ButtonStyle.red
        
        embed = discord.Embed(
            title=f"@{user.display_name}",
            description=f"**Premium:** {premiums}\n**Blacklisted:** {blacklistss}",
            color=discord.Color.dark_embed(),
        )
        embed.set_thumbnail(url=user.avatar)
        embed.set_author(name=user.display_name, icon_url=user.avatar)
        await ctx.send(embed=embed, view=view)

    @commands.command()
    @commands.is_owner()
    async def version(self, ctx: commands.Context, v: str):
        await self.client.db['Support Variables'].update_one({"_id": 1}, {'$set': {'version': v}}, upsert=True)


    @commands.command()
    @commands.is_owner()
    async def vps(self, ctx: commands.Context):
        await ctx.defer()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        embed = discord.Embed(
            color=discord.Color.dark_embed()
        ).add_field(
            name="`🧠` Memory", 
            value=f"> `Total:` {memory.total / 1e9:.2f} GB\n> `Available:` {memory.available / 1e9:.2f} GB\n> `Usage:` {memory.percent}%", 
            inline=False
        ).add_field(
            name="` 💫 ` CPU Usage", 
            value=f"{psutil.cpu_percent()}%", 
            inline=False
        ).add_field(
            name="` 💿 ` Disk", 
            value=f"> `Total:` {disk.total / 1e9:.2f} GB\n> `Used:` {disk.used / 1e9:.2f} GB\n> `Usage:` {disk.percent}%", 
            inline=False
        )
        await ctx.author.send(embed=embed)
        

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx: commands.Context, *, message: str):
        channel = ctx.channel
        await channel.send(message)
        await ctx.message.delete()

    @commands.command()
    @commands.is_owner()
    async def analyticss(self, ctx: commands.Context):
        result = await self.client.db["analytics"].find({}).to_list(length=None)

        content = ""
        for x in result:
            for key, value in x.items():
                if key != "_id":
                    content += f"{key}: {value}\n"
            content += "\n"
            with open("analytics.txt", "w", encoding="utf-8") as file:
                file.write(content)

            await ctx.send(file=discord.File("analytics.txt"))

class ManageAccount(discord.ui.View):
    def __init__(self, author, user: discord.User):
        super().__init__()
        self.user = user
        self.author = author

    async def updateembed(self, user: discord.User, interaction: discord.Interaction = None) -> discord.Embed:
        premiumresult = await interaction.client.db['premium'].find_one({"user_id": user.id})
        blacklistsresult = await interaction.client.db['blacklists'].find_one({"user": user.id})

        premiums = tick if premiumresult else no
        blacklistss = tick if blacklistsresult else no

        embed = discord.Embed(
            title=f"@{user.display_name}",
            description=(
                f"**Premium:** {premiums}\n"
                f"**Blacklisted:** {blacklistss}\n"
            ),
            color=discord.Color.dark_embed(),
        )
        embed.set_thumbnail(url=user.avatar)
        embed.set_author(name=user.display_name, icon_url=user.avatar)
        return embed

    @discord.ui.button(label="Premium", style=discord.ButtonStyle.red)
    async def premium(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        author = self.author.id
        if interaction.user.id != author:
            embed = discord.Embed(
                description=f"**{interaction.user.display_name},** this is not your view!",
                color=discord.Colour.dark_embed(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        premiumresult = await interaction.client.db['premium'].find_one({"user_id": self.user.id})
        if premiumresult:
            await interaction.client.db['premium'].delete_one({"user_id": self.user.id})
            self.premium.style = discord.ButtonStyle.red
        else:
            await interaction.client.db['premium'].insert_one({"user_id": self.user.id})
            self.premium.style = discord.ButtonStyle.green
        embed = await self.updateembed(self.user, interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Blacklisted", style=discord.ButtonStyle.red)
    async def blacklisted(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        author = self.author.id
        if interaction.user.id != author:
            embed = discord.Embed(
                description=f"**{interaction.user.display_name},** this is not your view!",
                color=discord.Colour.dark_embed(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        blacklistsresult = await interaction.client.db['blacklists'].find_one({"user": self.user.id})
        if blacklistsresult:
            await interaction.client.db['blacklists'].delete_one({"user": self.user.id})
            self.blacklisted.style = discord.ButtonStyle.red
        else:
            await interaction.client.db['blacklists'].insert_one({"user": self.user.id})
            self.blacklisted.style = discord.ButtonStyle.green

        embed = await self.updateembed(self.user)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple)
    async def refresh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        author = self.author.id
        if interaction.user.id != author:
            embed = discord.Embed(
                description=f"**{interaction.user.display_name},** this is not your view!",
                color=discord.Colour.dark_embed(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = await self.updateembed(self.user)
        await interaction.response.edit_message(embed=embed, view=self)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(management(client))
