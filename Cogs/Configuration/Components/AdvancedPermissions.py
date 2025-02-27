import discord
from utils.emojis import *
class PermissionsDropdown(discord.ui.Select):
    def __init__(self, author: discord.Member):
        super().__init__(
            placeholder="Advanced Permissions",
            options=[
                discord.SelectOption(
                    label="Manage Permissions",
                    value="Manage Permissions",
                    emoji="<:Permissions:1207365901956026368>",
                )
            ],
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.response.send_message(view=ManagePermissions(interaction.user), ephemeral=True)

class ManagePermissions(discord.ui.View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=360)
        self.author = author

    @discord.ui.button(label="+", style=discord.ButtonStyle.gray)
    async def Add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.defer()


        InvalidCommands = ['botinfo', 'server', 'sync', 'config', 'help', 'invite', 'mass', 'command', 'command run', 'infraction','modmail', 'support', 'docs', 'consent', 'ping', 'uptime', 'stats', 'github', 'vote', 'suggest', 'loa', 'staff', 'feedback', 'premium', 'donate', 'avatar', 'user', 'birb', 'suspension', 'connectionrole', 'feedback give', 'feedback ratings']
        commands = []
        Unused = []
        for command in interaction.client.cached_commands:
            if command in InvalidCommands:
                continue
            commands.append(discord.SelectOption(label=command, value=command, emoji="<:command1:1223062616872583289>"))
            if len(commands) >= 24:
                Unused = [command for command in interaction.client.cached_commands if command not in InvalidCommands and command not in [opt.value for opt in commands]]
                commands.append(discord.SelectOption(label="More Commands", value="More Commands", emoji="<:Add:1163095623600447558>"))
                break
          
        view = discord.ui.View()
        view.add_item(Commands(self.author, commands, Unused))
        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_author(name="Select the commands you want to add permissions to.", icon_url=interaction.guild.icon)
        await interaction.edit_original_response(view=view, embed=embed)

    @discord.ui.button(label="-", style=discord.ButtonStyle.gray)
    async def Remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.defer()

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if config is None or "Advanced Permissions" not in config:
            return await interaction.followup.send(
                content=f"{redx} There are no advanced permissions set.", ephemeral=True
            )
        commands = list(config["Advanced Permissions"].keys())
        if not commands:
            return await interaction.followup.send(
                content=f"{redx} There are no advanced permissions set.", ephemeral=True
            )

        view = discord.ui.View()
        view.add_item(RemoveCommands(self.author, commands))
        await interaction.followup.send(view=view, ephemeral=True)

class RemoveCommands(discord.ui.Select):
    def __init__(self, author: discord.Member, commands: list):
        super().__init__(
            placeholder="Select Permissions To Reset",
            min_values=0,
            max_values=len(commands),
            options=[discord.SelectOption(label=command, value=command, emoji="<:command1:1223062616872583289>") for command in commands][:25],
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.response.defer()

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})

        if config is None or "Advanced Permissions" not in config:
            return await interaction.followup.send(
                content=f"{redx} There are no advanced permissions set.", ephemeral=True
            )
        for command in self.values:
            if command in config["Advanced Permissions"]:
                del config["Advanced Permissions"][command]
        await interaction.client.config.update_one({"_id": interaction.guild.id}, {"$set": config})
        await interaction.edit_original_response(
            content=f"{tick} Successfully reset advanced permissions.",
            view=None,
            embed=None,
        )

class Commands(discord.ui.Select):
    def __init__(self, author: discord.Member, commands: list[discord.SelectOption], Unused: list):
        super().__init__(
            placeholder="Select Commands",
            min_values=0,
            max_values=len(commands),
            options=commands,
        )
        self.author = author
        self.Unused = Unused

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        await interaction.response.defer()

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})

        if self.values[0] == "More Commands":
            if len(self.Unused) > 0:
                commands = self.Unused[:24]
                Unused = self.Unused[24:]
                options = [discord.SelectOption(label=command, value=command, emoji="<:command1:1223062616872583289>") for command in commands]
                view = discord.ui.View()
                view.add_item(Commands(self.author, options, Unused))
                embed = discord.Embed(color=discord.Color.dark_embed())
                embed.set_author(name="Select the commands you want to add permissions to.", icon_url=interaction.guild.icon)
                return await interaction.followup.send(view=view, embed=embed, ephemeral=True)
            else:
                return await interaction.followup.send(content=f"{tick} No more commands to add.", ephemeral=True)
            
        if config is None:
            config = {"_id": interaction.guild.id, "Advanced Permissions": {}}
        elif "Advanced Permissions" not in config:
            config["Advanced Permissions"] = {}

        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_author(
            name="Which ranks do you want to be able to access these commands?",
            icon_url=interaction.guild.icon,
        )
        view = Roles(self.author, interaction, self.values)
        await interaction.edit_original_response(embed=embed, view=view)

class Roles(discord.ui.View):
    def __init__(self, author: discord.Member, interaction: discord.Interaction, commands: list):
        super().__init__()
        self.author = author
        self.interaction = interaction
        self.commands = commands
        self.add_item(RoleSelect(self.author, self.interaction, self.commands))

class RoleSelect(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, interaction: discord.Interaction, commands: list):
        super().__init__(placeholder="Select Roles", min_values=0, max_values=25)
        self.author = author
        self.interaction = interaction
        self.commands = commands

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        config = await interaction.client.config.find_one({"_id": interaction.guild.id})

        if config is None:
            config = {"_id": interaction.guild.id, "Advanced Permissions": {}}
        elif "Advanced Permissions" not in config:
            config["Advanced Permissions"] = {}

        for command in self.commands:
            if command not in config["Advanced Permissions"]:
                config["Advanced Permissions"][command] = []
            config["Advanced Permissions"][command].extend([role.id for role in self.values])

        await interaction.client.config.update_one({"_id": interaction.guild.id}, {"$set": config})
        await interaction.response.edit_message(
            content=f"{tick} Successfully updated advanced permissions.",
            view=None,
            embed=None,
        )
