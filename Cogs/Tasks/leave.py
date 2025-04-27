from discord.ext import commands, tasks
import os

import datetime
from datetime import datetime
from bson import ObjectId
from utils.emojis import *
import discord




class Leave(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client


    # TODO: Scheduled LOA handling
    # TODO: LOA Expiration Handling
    # TODO: LOA Request Expiration Handling. Whenever a request takes too long to be accepted or denied it'll automatically expire itself.

    
async def setup(client: commands.Bot) -> None:
    await client.add_cog(Leave(client))
