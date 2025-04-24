import discord
from discord.ext import commands
from datetime import timedelta
from discord import app_commands
from discord.ext import tasks
from utils.emojis import *
import os
from dotenv import load_dotenv

from datetime import datetime
from utils.Module import ModuleCheck

load_dotenv()

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



async def setup(client: commands.Bot) -> None:
    await client.add_cog(LOAModule(client))
