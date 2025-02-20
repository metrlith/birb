import discord
import discord.http
import os
import traceback

from utils.emojis import *
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from utils.permissions import premium
from typing import Literal

load_dotenv()
Mongos = AsyncIOMotorClient(os.getenv("MONGO_URL"))
DB = Mongos["astro"]
Configuration = DB["Config"]
Customisation = DB["Customisation"]
Panels = DB["Panels"]


class Tickets(discord.ui.Select):
    def __init__(self, author: discord.Member):
        super().__init__(
            options=[
                discord.SelectOption(label="Panels", emoji="<:Panel:1340741181965078642>"),
                discord.SelectOption(label="Multi Panels", emoji="<:MultiPanel:1340741183579885690>"),
            ]
        )
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        option = self.values[0]

        if option == "Panels":
            view = discord.ui.View()
            view.add_item(CreateDeletePanel(self.author, "single"))
            await interaction.response.send_message(view=view, ephemeral=True)

        elif option == "Multi Panels":
            view = discord.ui.View()
            view.add_item(CreateDeletePanel(self.author, "multi"))
            await interaction.response.send_message(view=view, ephemeral=True)


class CreateDeletePanel(discord.ui.Select):
    def __init__(self, author: discord.Member, PanelType: Literal["single", "multi"]):
        Options = [
            discord.SelectOption(label="Create", emoji="<:Add:1163095623600447558>"),
            discord.SelectOption(label="Delete", emoji="<:Subtract:1229040262161109003>"),
            discord.SelectOption(label="Modify", emoji="<:Pen:1235001839036923996>"),
        ]
        self.PanelType = PanelType
        self.author = author
        super().__init__(options=Options)

    async def callback(self, interaction: discord.Interaction):
        Action = self.values[0]

        if Action == "Create":
            await interaction.response.send_modal(PanelCreationModal(self.PanelType))

        elif Action == "Delete":
            PanelsList = await Panels.find(
                {"guild": interaction.guild.id, "type": self.PanelType}
            ).to_list(length=None)
            Options = [
                discord.SelectOption(label=Panel.get("name", "Unnamed"))
                for Panel in PanelsList
            ]

            if not Options:
                await interaction.response.send_message(
                    content="No panels found to delete.", ephemeral=True
                )
                return

            View = discord.ui.View()
            View.add_item(DeletePanelSelect(self.author, self.PanelType, Options))
            await interaction.response.edit_message(view=View)

        elif Action == "Modify":
            PanelsList = await Panels.find(
                {"guild": interaction.guild.id, "type": self.PanelType}
            ).to_list(length=None)
            Options = [
                discord.SelectOption(label=Panel.get("name", "Unnamed"))
                for Panel in PanelsList
            ]

            if not Options:
                await interaction.response.send_message(
                    content="No panels found to modify.", ephemeral=True
                )
                return

            View = discord.ui.View()
            View.add_item(ModifyPanelSelect(self.author, self.PanelType, Options))
            await interaction.response.edit_message(view=View)


class ModifyPanelSelect(discord.ui.Select):
    def __init__(self, author: discord.Member, PanelType: str, options: list):
        super().__init__(options=options)
        self.author = author
        self.PanelType = PanelType

    async def callback(self, interaction: discord.Interaction):
        SelectedPanel = self.values[0]

        if self.PanelType == "single":
            View = SingelPanelCustomisation(interaction.user, SelectedPanel)
        else:
            View = MultiPanelCustomisation(interaction.user, SelectedPanel)

        await interaction.response.edit_message(view=View)


class PanelCreationModal(discord.ui.Modal):
    def __init__(self, PanelType: Literal["single", "multi"]):
        self.PanelType = PanelType
        super().__init__(title="Create New Panel")

        self.name_input = discord.ui.TextInput(
            label="Panel Name", placeholder="Enter a name for your new panel"
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        PanelName = self.name_input.value
        await Panels.insert_one(
            {"guild": interaction.guild.id, "type": self.PanelType, "name": PanelName}
        )

        if self.PanelType == "single":
            View = SingelPanelCustomisation(interaction.user, PanelName)
        else:
            View = MultiPanelCustomisation(interaction.user, PanelName)

        await interaction.response.edit_message(view=View)


class DeletePanelSelect(discord.ui.Select):
    def __init__(self, author: discord.Member, PanelType: str, options: list):
        super().__init__(options=options)
        self.author = author
        self.PanelType = PanelType

    async def callback(self, interaction: discord.Interaction):
        SelectedPanel = self.values[0]
        await Panels.delete_one(
            {
                "guild": interaction.guild.id,
                "type": self.PanelType,
                "name": SelectedPanel,
            }
        )
        await interaction.response.edit_message(
            content=f"Panel '{SelectedPanel}' deleted successfully.",
            view=None,
            embed=None,
        )


class SingelPanelCustomisation(discord.ui.View):
    def __init__(self, author: discord.Member, name: str):
        super().__init__(timeout=3060)
        self.name = name
        self.author = author

    @discord.ui.button(label="Customise Embeds", style=discord.ButtonStyle.gray, emoji="<:Customisation:1223063306131210322>")
    async def CustomiseEmbed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        view = discord.ui.View()
        view.add_item(EmbedSelection(interaction.user, "Panel", self.name))
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(
        label="Customise Button", emoji="<:Button:1223063359184830494>"
    )
    async def CustomiseButton(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )
        await interaction.response.send_modal(
            CustomiseButton(interaction.user, self.name, custom)
        )


    @discord.ui.button(label="Category", style=discord.ButtonStyle.blurple, emoji="<:category:1248312604733210735>")
    async def Category(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )
        view = discord.ui.View()
        view.add_item(
            Category(
                interaction.user,
                self.name,
                interaction.guild.get_channel(custom.get("Category", 0)),
            )
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Transcript Channel", style=discord.ButtonStyle.blurple, emoji="<:tag:1234998802948034721>")
    async def Transcript(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )

        view = discord.ui.View()
        view.add_item(
            TranscriptChannel(
                interaction.user,
                self.name,
                interaction.guild.get_channel(custom.get("TranscriptChannel", 0)),
            )
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Permissions", style=discord.ButtonStyle.blurple, emoji="<:Permissions:1207365901956026368>")
    async def Permissions(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )

        view = discord.ui.View()
        view.add_item(
            Permissions(
                interaction.user,
                self.name,
                [
                    role
                    for role in interaction.guild.roles
                    if role.id in custom.get("permissions", [])
                ],
            )
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Mentions On Open", style=discord.ButtonStyle.blurple, emoji="<:Ping:1298301862906298378>")
    async def Mentions(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )
        view = discord.ui.View()
        view.add_item(
            MentionsOnOpen(
                interaction.user,
                self.name,
                [
                    role
                    for role in interaction.guild.roles
                    if role.id in custom.get("MentionsOnOpen", [])
                ],
            )
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Access Control", style=discord.ButtonStyle.blurple, emoji="<:AccessControl:1340741536492814458>")
    async def AccessControl(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )
        view = discord.ui.View()

        view.add_item(
            AccessControl(
                interaction.user,
                self.name,
                [
                    role
                    for role in interaction.guild.roles
                    if role.id in custom.get("AccessControl", [])
                ],
            )
        )
        await interaction.response.send_message(view=view, ephemeral=True)
    
    @discord.ui.button(label="Finish", style=discord.ButtonStyle.green, emoji="<:Save:1223293419678470245>")
    async def Finish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name}
        )
        if not custom:
            await interaction.response.send_message(
            content=f"{no} **{interaction.user.display_name},** this panel does not exist.",
            ephemeral=True,
            )
            return

        Required = ["permissions", "Category", "TranscriptChannel", "Button"]
        MissingFields = []
        for field in Required:
            if not custom.get(field):
                MissingFields.append(field)
            
        if len(MissingFields) > 0:
            return await interaction.response.send_message(
                content=f"{no} **{interaction.user.display_name},** missing required fields: {', '.join(MissingFields)}",
                ephemeral=True,
            )

        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** configuration finished.",
            view=None
        )


class MultiPanelCustomisation(discord.ui.View):
    def __init__(self, author: discord.Member, name: str):
        super().__init__(timeout=3060)
        self.name = name
        self.author = author

    @discord.ui.button(label="Customise Embeds", style=discord.ButtonStyle.gray, emoji="<:Customisation:1223063306131210322>")
    async def CustomiseEmbed(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        view = discord.ui.View()
        view.add_item(EmbedSelection(interaction.user, "Multi", self.name))
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Manage Panels", emoji="<:MultiPanel:1340741183579885690>")
    async def ManagePanels(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        panels = await Panels.find(
            {"guild": interaction.guild.id, "type": "single"}
        ).to_list(length=None)
        panel = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "multi", "name": self.name}
        )
        Default = panel.get("Panels", [])
        options = [
            discord.SelectOption(
                label=p.get("name", "Unnamed"), default=p.get("name") in Default
            )
            for p in panels
        ]
        if not options:
            await interaction.response.send_message(
                content="No panels found.", ephemeral=True
            )
            return
        view = discord.ui.View()
        view.add_item(MultiToSingle(interaction.user, self.name, options))
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.green, emoji="<:Save:1223293419678470245>")
    async def Finish(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        custom = await Panels.find_one(
            {"guild": interaction.guild.id, "type": "multi", "name": self.name}
        )
        if not custom:
            await interaction.response.send_message(
            content=f"{no} **{interaction.user.display_name},** this panel does not exist.",
            ephemeral=True,
            )
            return

        Required = ["Panels"]
        MissingFields = []
        for field in Required:
            if not custom.get(field):
                MissingFields.append(field)
            
        if len(MissingFields) > 0:
            return await interaction.response.send_message(
                content=f"{no} **{interaction.user.display_name},** missing required fields: {', '.join(MissingFields)}",
                ephemeral=True,
            )

        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** configuration finished.",
            view=None
        )


async def CustomiseEmbed(interaction: discord.Interaction, option, name):
    try:
        await interaction.response.defer()
        custom = await Panels.find_one({"guild": interaction.guild.id, "name": name})
        embed = None

        from Cogs.Configuration.Components.EmbedBuilder import (
            DisplayEmbed,
            Embed,
        )

        if not custom or custom.get(option) is None:
            view = Embed(
                interaction.user,
                FinalFunction,
                option,
                {
                    "thumb": "",
                    "author_url": "",
                    "option": option,
                    "image": "",
                    "name": name,
                },
            )
            embed = discord.Embed(
                title="Unknown",
            )

            view.remove_item(view.Buttons)
            view.remove_item(view.RemoveEmbed)
            view.remove_item(view.Content)
            view.remove_item(view.Permissions)
            view.remove_item(view.ForumsChannel)
            view.remove_item(view.Ping)
            view.remove_item(view.reset)

            return await interaction.edit_original_response(
                embed=embed, view=view, content=None
            )
        view = Embed(
            interaction.user,
            FinalFunction,
            option,
            {
                "thumb": custom.get("embed", {}).get("thumbnail", ""),
                "author_url": custom.get("embed", {})
                .get("author", {})
                .get("icon_url", ""),
                "image": custom.get("image"),
                "option": option,
                "name": name,
            },
        )
        embed = await DisplayEmbed(custom.get(option), interaction.user)
        view.remove_item(view.Buttons)
        view.remove_item(view.RemoveEmbed)
        view.remove_item(view.Content)
        view.remove_item(view.Permissions)
        view.remove_item(view.ForumsChannel)
        view.remove_item(view.Ping)
        view.remove_item(view.reset)

        return await interaction.edit_original_response(
            embed=embed, view=view, content=None
        )
    except Exception as e:
        traceback.print_exc()


async def FinalFunction(interaction: discord.Interaction, d={}):
    embed = interaction.message.embeds[0]
    if embed:

        data = {
            f"{d.get('option')}": {
                "content": interaction.message.content,
                "creator": interaction.user.id,
                "embed": {
                    "title": embed.title,
                    "description": embed.description,
                    "thumbnail": d.get("thumb"),
                    "image": d.get("image"),
                    "color": f"{embed.color.value:06x}" if embed.color else None,
                    "author": {
                        "name": embed.author.name if embed.author else None,
                        "icon_url": d.get("author_url"),
                    },
                    "fields": [
                        {
                            "name": field.name,
                            "value": field.value,
                            "inline": field.inline,
                        }
                        for field in embed.fields
                    ],
                },
            }
        }
    await Panels.update_one(
        {"guild": interaction.guild.id, "name": d.get("name")},
        {"$set": data},
        upsert=True,
    )

    await interaction.response.edit_message(
        content=f"{tick} **{interaction.user.display_name}**, succesfully updated `{d.get('option')}` embed.",
        embed=None,
        view=None,
    )


class EmbedSelection(discord.ui.Select):
    def __init__(self, author: discord.Member, type: str, name: str):
        if type == "Panel":
            options = [
                discord.SelectOption(label="Panel", value="Panel"),
                discord.SelectOption(label="Welcome Message", value="Welcome Message"),
            ]
        else:
            options = [
                discord.SelectOption(label="Panel", value="Panel"),
            ]
        super().__init__(options=options)
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        option = self.values[0]
        await CustomiseEmbed(interaction, option, self.name)


class MultiToSingle(discord.ui.Select):
    def __init__(self, author: discord.Member, name: str, options: list):
        super().__init__(options=options[:25], max_values=len(options), min_values=0)
        self.name = name
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "multi", "name": self.name},
            {"$set": {"Panels": self.values}},
        )
        return await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** I've succesfully updated the connected panels.",
            embed=None,
            view=None,
        )


async def TicketsEmbed(interaction: discord.Interaction, embed: discord.Embed):
    embed.set_author(name=f"{interaction.guild.name}", icon_url=interaction.guild.icon)
    embed.set_thumbnail(url=interaction.guild.icon)
    embed.description = (
        "> The Tickets Panel allows users to create and manage tickets for support, "
        "inquiries, or reports. You can customize ticket categories, forms, and permissions. "
        "Learn more at [the documentation](https://docs.astrobirb.dev/)."
    )
    return embed


class Permissions(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, name: str, permissions: list):
        super().__init__(
            placeholder="Select roles for permissions",
            min_values=1,
            max_values=25,
            default_values=permissions,
        )
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        selected_roles = [role.id for role in self.values]
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {"$set": {"permissions": selected_roles}},
        )
        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** permissions updated successfully.",
            view=None,
        )


class TranscriptChannel(discord.ui.ChannelSelect):
    def __init__(self, author: discord.Member, name: str, channel: discord.TextChannel):
        super().__init__(
            placeholder="Select a channel",
            min_values=1,
            max_values=1,
            default_values=[channel] if channel else [],
        )
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {"$set": {"TranscriptChannel": self.values[0].id}},
        )
        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** transcript channel updated successfully.",
            view=None,
        )


class Category(discord.ui.ChannelSelect):
    def __init__(
        self, author: discord.Member, name: str, category: discord.CategoryChannel
    ):
        super().__init__(
            placeholder="Select a category",
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.category],
            default_values=[category] if category else [],
        )
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {"$set": {"Category": self.values[0].id}},
        )
        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** category updated successfully.",
            view=None,
        )


class MentionsOnOpen(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, name: str, roles: list):
        super().__init__(
            placeholder="Select roles",
            min_values=0,
            max_values=25,
            default_values=roles,
        )
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        selected_roles = [role.id for role in self.values]
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {"$set": {"MentionsOnOpen": selected_roles}},
        )
        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** mentions on open updated successfully.",
            view=None,
        )


class AccessControl(discord.ui.RoleSelect):
    def __init__(self, author: discord.Member, name: str, roles: list):
        super().__init__(
            placeholder="Select roles",
            min_values=0,
            max_values=25,
            default_values=roles,
        )
        self.author = author
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            embed = discord.Embed(
                description=f"{redx} **{interaction.user.display_name},** this is not your panel!",
                color=discord.Colour.brand_red(),
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {"$set": {"AccessControl": [role.id for role in self.values]}},
        )
        await interaction.response.edit_message(
            content=f"{tick} **{interaction.user.display_name},** access control updated successfully.",
            view=None,
        )


class CustomiseButton(discord.ui.Modal):
    def __init__(self, author: discord.Member, name: str, data: dict):
        super().__init__(title="Customise Button")
        self.author = author
        self.name = name
        self.button = discord.ui.TextInput(
            label="Button",
            placeholder="Enter the button name",
            default=data.get("Button", {}).get("label", ""),
        )
        self.color = discord.ui.TextInput(
            label="Color",
            placeholder="Enter the button color (Blurple, Green, Red, Grey)",
            default=data.get("Button", {}).get("style", ""),
            required=False,
        )
        self.emoji = discord.ui.TextInput(
            label="Emoji",
            placeholder="Enter the button emoji",
            default=data.get("Button", {}).get("emoji", ""),
            required=False,
        )
        self.add_item(self.button)
        self.add_item(self.color)
        self.add_item(self.emoji)

    async def on_submit(self, interaction: discord.Interaction):
        button = self.button.value
        color = self.color.value
        emoji = self.emoji.value
        if not color:
            color = "Grey"
        if not color in ["Blurple", "Green", "Red", "Grey"]:
            return await interaction.response.send_message(
                content=f"{no} **{interaction.user.display_name},** invalid button color.",
                ephemeral=True,
            )
        if not emoji:
            emoji = None
        import string
        import random

        await Panels.update_one(
            {"guild": interaction.guild.id, "type": "single", "name": self.name},
            {
                "$set": {
                    "Button": {
                        "label": button,
                        "style": color,
                        "emoji": emoji,
                        "custom_id": "".join(
                            random.choices(string.ascii_letters + string.digits, k=32)
                        ),
                    }
                }
            },
        )
        await interaction.response.send_message(
            content=f"{tick} **{interaction.user.display_name},** button updated successfully.",
            ephemeral=True,
        )
