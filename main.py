import discord
import platform
import sys
import gc

sys.dont_write_bytecode = True
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from Cogs.Modules.promotions import SyncCommands
import time
from Cogs.Events.on_suggestion import Voting as Voti
from Cogs.Modules.loa import Confirm
from Cogs.Modules.customcommands import Voting
from Cogs.Tasks.activityauto import ResetLeaderboard
from Cogs.Modules.staff import Staffview
from Cogs.Events.on_ban import AcceptOrDeny, AppealButton
from motor.motor_asyncio import AsyncIOMotorClient
from Cogs.Events.on_infraction_approval import CaseApproval
from Cogs.Events.on_ticket import PTicketControl
from discord import app_commands
from Cogs.Tasks.qotd import *
import logging

from Cogs.Events.modmail import ModmailClosure, Links
from Cogs.Events.Dev.on_ticket import TicketControl
from Cogs.Modules.tickets import ButtonHandler, Panels
from Cogs.Modules.Developer.tickets import Buttons

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

gc.enable()

if environment == "custom":
    from branding import ClearEmojis

    ClearEmojis(True, "/app")

PREFIX = os.getenv("PREFIX")
TOKEN = os.getenv("TOKEN")
STATUS = os.getenv("STATUS")
MONGO_URL = os.getenv("MONGO_URL")
SHARDS = os.getenv("SHARDS")

load_dotenv()
guildid = os.getenv("CUSTOM_GUILD")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
prefixdb = db["prefixes"]
qotdd = db["qotd"]
Config = db["Config"]
Views = db["Views"]
SupportVariables = db["Support Variables"]
staffdb = db["staff database"]


class client(commands.AutoShardedBot):
    def __init__(self):
        # Databases -----------------------
        self.db = db
        self.infractions = db["infractions"]
        self.premium = db["premium"]
        self.badges = db["badges"]
        self.promotions = db["promotions"]
        self.modmail = db["modmail"]
        self.suggestions = db["suggestions"]
        self.prefix = db["prefixes"]

        self.suspension = db["Suspensions"]
        self.feedback = db["feedback"]
        self.customcommands = db["Custom Commands"]
        self.loa = db["loa"]
        self.consent = db["consent"]
        self.analytics = db["analytics"]
        self.staffdb = db["staff database"]
        self.qotd = db["qotd"]
        self.customisation = db["Customisation"]
        self.config = db["Config"]
        self.infractiontypeactions = db["infractiontypeactions"]
        
        # Set Values -----------------------
        self.infractions_maintenance = False
        self.promotions_maintenance = False
        self.feedback_maintenance = False
        self.loa_maintenance = False
        self.suggestions_maintenance = False
        self.customcommands_maintenance = False
        self.cached_commands = {}
        # --------------------------------

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        print(environment)
        if environment == "custom":
            print("Custom Branding Loaded")
            super().__init__(
                command_prefix=commands.when_entioned_or(self.get_prefix),
                intents=intents,
                shard_count=None,
                chunk_guilds_at_startup=False,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=False, everyone=False, roles=False
                ),
            )
        elif environment == "development":
            print("Development Loaded")
            super().__init__(
                command_prefix=commands.when_mentioned_or(PREFIX),
                intents=intents,
                shard_count=None,
                chunk_guilds_at_startup=True,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=False, everyone=False, roles=False
                ),
            )

        else:
            print("Production Loaded")
            super().__init__(
                command_prefix=commands.when_mentioned_or(PREFIX),
                intents=intents,
                chunk_guilds_at_startup=False,
                allowed_mentions=discord.AllowedMentions(
                    replied_user=False, everyone=False, roles=False
                ),
            )

        self.client = client
        self.cogslist = [
            "Cogs.Modules.Developer.astro",
            "Cogs.Modules.suggestions",
            "Cogs.Modules.loa",
            "Cogs.Modules.utility",
            "Cogs.Modules.botinfo",
            "Cogs.Modules.suspension",
            "Cogs.Modules.stafffeedback",
            "Cogs.Modules.connectionroles",
            "Cogs.Modules.staff",
            "Cogs.Modules.promotions",
            "Cogs.Modules.infractions",
            "Cogs.Modules.modmail",
            "Cogs.Modules.consent",
            "Cogs.Modules.customcommands",
            "Cogs.Configuration.Configuration",
            "Cogs.Events.Dev.guilds",
            "Cogs.Events.Dev.welcome",
            "Cogs.Events.quota",
            "Cogs.Events.modmail",
            "Cogs.Events.on_thread_create",
            "Cogs.Events.Dev.topgg",
            "Cogs.Events.Dev.analytics",
            "Cogs.Events.on_error",
            "Cogs.Events.autoresponse",
            "Cogs.Events.on_ban",
            "Cogs.Events.on_infraction",
            "Cogs.Events.ConnectionRoles",
            "Cogs.Modules.data",
            "Cogs.Modules.Developer.tickets",
            "Cogs.Events.Dev.on_ticket",
            "Cogs.Tasks.expiration",
            "Cogs.Events.on_promotion",
            "Cogs.Events.on_infraction_edit",
            "Cogs.Tasks.loa",
            "Cogs.Tasks.stafflist",
            "Cogs.Tasks.suspension",
            "Cogs.Tasks.activityauto",
            "Cogs.Tasks.qotd",
            "Cogs.Events.on_feedback",
            "Cogs.Events.on_suggestion",
            "Cogs.Events.on_suggest_update",
            "Cogs.Modules.integrations",
            "Cogs.Tasks.loa_scheulded",
            "Cogs.Events.on_infraction_approval",
            "Cogs.Modules.tickets",
            "Cogs.Events.on_ticket",
        ]
        if not environment == "custom":
            self.cogslist.append("utils.api")
            self.cogslist.append("utils.dokploy")

    async def load_jishaku(self):
        await self.wait_until_ready()
        await self.load_extension("jishaku")
        print("[🔄] Jishaku Loaded")

    async def get_prefix(self, message: discord.Message) -> tasks.List[str] | str:
        if message.guild is None:
            return "!!"
        if message.author.bot:
            return None
        prefixdb = db["prefixes"]
        prefixresult = await prefixdb.find_one({"guild_id": message.guild.id})
        if prefixresult:
            prefix = prefixresult.get("prefix", "!!")
        else:
            prefix = PREFIX
        return commands.when_mentioned_or(prefix)(self, message)

    async def setup_hook(self):

        if update_channel_name.is_running():
            update_channel_name.restart()
        else:
            update_channel_name.start()

        TicketViews = await Panels.find({}).to_list(length=None)
        V = await Views.find({}).to_list(length=None)
        print('[Views] Loading Any Views')
        for view in V:

            if not view:
                continue
            if view.get("type") == "staff":
                DbResults = await staffdb.find({"guild_id": view.get("guild")}).to_list(
                    length=None
                )
                if not DbResults:
                    continue
                options = []
                guild = self.get_guild(int(view.get("guild")))
                if not guild:
                    continue
                if not guild.chunked:
                    try:
                        await guild.chunk()
                    except (discord.HTTPException, discord.Forbidden):
                        continue
                for staff in DbResults:
                    member = guild.get_member(staff.get("staff_id"))
                    if not member:
                        continue
                    options.append(
                        discord.SelectOption(
                            label=member.display_name,
                            value=str(member.id),
                            description=member.get("rolename"),
                            emoji="<:staff:1206248655359840326>"
                        )
                    )
                    if len (options) >= 24:
                        options.append(
                                discord.SelectOption(
                                    label="View More",
                                    value="more",
                                    description="View more staff members",
                                    emoji="<:List:1223063187063308328>"

                                )
                            )                        
                        break
    

                view = Staffview(options=options[:25])
                try:
                    self.add_view(view, msg_id=int(view.get("MsgID")))
                except:
                    continue
        print('[Views] Loading Ticket Views')
        for view in TicketViews:
            view_handler = ButtonHandler()
            if view.get("type") == "multi":
                buttons = []
                if not view.get("Panels"):
                    continue
                for panel_name in view.get("Panels"):
                    sub = await Panels.find_one(
                        {
                            "guild": view.get("guild"),
                            "name": panel_name,
                            "type": "single",
                        }
                    )
                    if not sub:
                        continue
                    sub_button = sub.get("Button")
                    if not sub_button:
                        continue
                    buttons.append(
                        {
                            "label": sub_button.get("label"),
                            "style": sub_button.get("style"),
                            "emoji": sub_button.get("emoji"),
                            "custom_id": sub_button.get("custom_id"),
                        }
                    )

                if buttons:
                    view_handler.add_buttons(buttons)
            else:
                single_button = view.get("Button")
              
                if not single_button:
                    continue

                view_handler.add_buttons(
                    [
                        {
                            "label": single_button.get("label"),
                            "style": single_button.get("style"),
                            "emoji": single_button.get("emoji"),
                            "custom_id": single_button.get("custom_id"),
                        }
                    ]
                )

            msg_id = view.get("MsgID")
            self.add_view(view_handler, message_id=int(msg_id) if msg_id else 0)

        self.add_view(Voting())
        self.add_view(Confirm())
        self.add_view(Voti())
        self.add_view(Staffview())
        self.add_view(ResetLeaderboard())
        self.add_view(AcceptOrDeny(client))
        self.add_view(AppealButton(client))
        self.add_view(ModmailClosure())
        self.add_view(Links())
        self.add_view(TicketControl())
        self.add_view(Buttons())
        self.add_view(CaseApproval())
        self.add_view(PTicketControl())

        self.loop.create_task(self.load_jishaku())
        for ext in self.cogslist:
            await self.load_extension(ext)
            print(f"[✅] {ext} loaded")
        await self.CacheCommands()

    async def GetVersion(self):
        V = await SupportVariables.find_one({"_id": 1})
        if not V:
            return "N/A"
        return V.get("version")

    async def CacheCommands(self):
        self.cached_commands = []

        def recursive_cache(command, parent=""):
            full_name = f"{parent} {command.name}".strip()
            self.cached_commands.append(full_name)
            if isinstance(command, discord.app_commands.Group):
                for subcommand in command.commands:
                    recursive_cache(subcommand, full_name)

        for command in self.tree.get_commands():
            recursive_cache(command)

    async def on_ready(self):
        if environment == "custom":
            guild = await self.fetch_guild(guildid)
            if guild:
                try:
                    await guild.chunk(cache=True)
                except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                    print(f"[❌] Failed to chunk guild {guild.name} ({guild.id})")
                print(f"[✅] Connected to guild {guild.name} ({guild.id})")
                try:
                    await self.tree.sync()
                except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                    print(f"[❌] Failed to sync commands")
        await SyncCommands(self)
        prfx = time.strftime("%H:%M:%S GMT", time.gmtime())
        prfx = f"[📖] {prfx}"
        print(prfx + " Logged in as " + self.user.name)
        print(prfx + " Bot ID " + str(self.user.id))
        print(prfx + " Discord Version " + discord.__version__)
        print(prfx + " Python Version " + str(platform.python_version()))
        print(prfx + " Bot is in " + str(len(self.guilds)) + " servers")
        try:
            await db.command("ping")
            print("[✅] successfully connected to MongoDB")
        except Exception as e:
            print(f"[❌] Failed to connect to MongoDB: {e}")

        activity2 = discord.CustomActivity(name=f"{STATUS}")
        if STATUS:
            await self.change_presence(activity=activity2)

        else:
            print("[⚠️] STATUS not defined in .env, bot will not set a custom status.")
        if not environment == "custom":
            Modmail = await self.config.find({"Modules.Modmail": True}).to_list(length=None)
            Guilds = 0
            DevServers = [1092976553752789054]
            for server in DevServers:
                try:
                    guild = self.get_guild(server)
                    if guild:
                        await guild.chunk()
                except:
                    continue
            for Servers in Modmail:
                try:
                    try:
                        Guild = self.get_guild(int(Servers.get("_id")))
                    except (discord.NotFound, discord.HTTPException):
                        continue
                    if not Guild:
                        continue

                    await Guild.chunk()
                    Guilds += 1
                except:
                    continue

            print(prfx + f" Succesfully cached {Guilds} modmail enabled servers.")
            del Modmail

    async def on_disconnect(self):
        print("[⚠️] Disconnected from Discord Gateway!")

    async def on_resumed(self):
        print("[✅] Resumed connection to Discord Gateway!")

    async def is_owner(self, user: discord.User):
        if user.id in [795743076520820776]:
            return True

        return await super().is_owner(user)

    async def on_shard_ready(self, shard_id):
        print(f"[✅] Shard {shard_id} is ready.")

    async def on_shard_connect(self, shard_id):
        print(f"[✅] Shard {shard_id} connected.")

    async def on_shard_disconnect(self, shard_id):
        print(f"[⚠️] Shard {shard_id} disconnected.")


client = client()


@tasks.loop(minutes=10, reconnect=True)
async def update_channel_name():
    if environment == "development":
        return
    if environment == "custom":
        return
    channel = client.get_channel(1131245978704420964)
    if not channel:
        return
    users = await GetUsers()
    try:
        await channel.edit(name=f"{len(client.guilds)} Guilds | {users} Users")
    except (discord.HTTPException, discord.Forbidden):
        return print("[⚠️] Failed to update channel name.")


async def GetUsers():
    total_members = sum(guild.member_count or 0 for guild in client.guilds)
    return total_members


if __name__ == "__main__":
    client.run(TOKEN)
