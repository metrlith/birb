import discord

class YesOrNo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=360)
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


class PMButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Premium",
                emoji="<:sparkle:1233931758089666695>",
                style=discord.ButtonStyle.link,
                url="https://patreon.com/astrobirb",
            )
        )
