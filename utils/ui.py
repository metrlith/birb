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

class BasicPaginator(discord.ui.View):
    def __init__(self, author: discord.Member, messages: list = None, embeds: list = None):
        super().__init__()
        self.messages = messages
        self.embeds = embeds
        self.current = 0
        self.UpdateButtons()

    def UpdateButtons(self):
        self.prev.disabled = self.current == 0
        self.next.disabled = self.current == len(self.messages) - 1
        self.page.label = f"{self.current + 1}/{len(self.messages)}"

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple, disabled=True)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current > 0:
            self.current -= 1
            self.UpdateButtons()
            await interaction.response.edit_message(
                content=self.messages[self.current] if self.messages else None, 
                embed=self.embeds[self.current] if self.embeds else None, 
                view=self
            )

    @discord.ui.button(label="1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def page(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple, disabled=False)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current < len(self.messages) - 1:
            self.current += 1
            self.UpdateButtons()
            await interaction.response.edit_message(
                content=self.messages[self.current] if self.messages else None, 
                embed=self.embeds[self.current] if self.embeds else None, 
                view=self
            )
    

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
