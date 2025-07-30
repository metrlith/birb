import discord
from discord.ext import commands
import os
from bson import ObjectId
import aiohttp
import logging
from utils.erm import voidShift
import asyncio
import datetime
from utils.permissions import premium
import random
import string
from Cogs.Configuration.Components.EmbedBuilder import DisplayEmbed
import traceback

logger = logging.getLogger(__name__)
MONGO_URL = os.getenv("MONGO_URL")


def Replacements(staff: discord.Member, Infraction: dict, manager: discord.Member):
    def get_attr_or_key(obj, key):
        return getattr(obj, key, None) if hasattr(obj, key) else obj.get(key, "N/A")

    replacements = {
        "{staff.mention}": staff.mention,
        "{staff.name}": staff.display_name,
        "{staff.avatar}": staff.display_avatar.url if staff.display_avatar else None,
        "{author.mention}": manager.mention,
        "{author.name}": manager.display_name,
        "{action}": get_attr_or_key(Infraction, "action"),
        "{reason}": get_attr_or_key(Infraction, "reason"),
        "{notes}": get_attr_or_key(Infraction, "notes"),
        "{author.avatar}": (
            manager.display_avatar.url if manager.display_avatar else None
        ),
        "{expiration}": (
            f"<t:{int(get_attr_or_key(Infraction, 'expiration').timestamp())}:R>"
            if get_attr_or_key(Infraction, "expiration")
            else "N/A"
        ),
    }
    return replacements


def DefaultEmbed(data, staff, manager):
    embed = discord.Embed(
        title="Staff Consequences & Discipline",
        description=f"- **Staff Member:** {staff.mention}\n- **Action:** {data.get('action')}\n- **Reason:** {data.get('reason')}",
        color=discord.Color.dark_embed(),
    )
    if data.get("notes"):
        embed.description += f"\n- **Notes:** {data.get('notes')}"
    if not data.get("annonymous"):
        embed.set_author(
            name=f"Signed, {manager.display_name}", icon_url=manager.display_avatar
        )
    embed.set_thumbnail(url=staff.display_avatar)
    embed.set_footer(text=f"Infraction ID | {data.get('random_string')}")
    return embed


def InfractItem(data):
    return InfractionItem(
        staff=data.get("staff"),
        management=data.get("management"),
        action=data.get("action"),
        reason=data.get("reason"),
        notes=data.get("notes"),
        expiration=data.get("expiration"),
        voided=data.get("voided"),
        expired=data.get("expired"),
        random_string=data.get("random_string"),
        guild_id=data.get("guild_id"),
        annonymous=data.get("annonymous"),
        msg_id=data.get("msg_id"),
    )


def CustomItem(data):
    return Embed(
        author=data.get("author"),
        author_icon=data.get("author_icon"),
        color=data.get("color"),
        description=data.get("description"),
        image=data.get("image"),
        thumbnail=data.get("thumbnail"),
        title=data.get("title"),
    )


class InfractionItem:
    def __init__(
        self,
        staff,
        management,
        action,
        reason,
        notes,
        expiration,
        voided,
        expired,
        random_string,
        guild_id,
        annonymous,
        msg_id,
    ):
        self.staff = staff
        self.management = management
        self.action = action
        self.reason = reason
        self.notes = notes
        self.expiration = expiration
        self.voided = voided
        self.expired = expired
        self.random_string = random_string
        self.guild_id = guild_id
        self.annonymous = annonymous
        self.msg_id = msg_id


class Embed:
    def __init__(
        self, author, author_icon, color, description, image, thumbnail, title
    ):
        self.author = author
        self.author_icon = author_icon
        self.color = color
        self.description = description
        self.image = image
        self.thumbnail = thumbnail
        self.title = title


class on_infractions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_infraction(
        self, objectid: ObjectId, Settings: dict, Actions: dict, Type: str = None
    ):
        if Type is None:
            InfractionData = await self.client.db["infractions"].find_one(
                {"_id": objectid}
            )
        else:
            InfractionData = await self.client.db["Suspensions"].find_one(
                {"_id": objectid}
            )
        Infraction = InfractItem(InfractionData)
        guild = await self.client.fetch_guild(Infraction.guild_id)
        if guild is None:
            logging.warning(
                f"[🏠 on_infraction] {Infraction.guild_id} is None and can't be found..?"
            )
            return

        try:
            staff = await guild.fetch_member(int(Infraction.staff))
        except:
            staff = None
        if staff is None:
            logging.warning(
                f"[🏠 on_infraction] @{guild.name} staff member {Infraction.staff} can't be found."
            )
            return

        try:
            manager = await guild.fetch_member(int(Infraction.management))
        except:
            manager = None
        if manager is None:
            logging.warning(
                f"[🏠 on_infraction] @{guild.name} manager {Infraction.management} can't be found."
            )
            return

        ChannelID = Settings.get(
            "Infraction" if Type is None else "Suspension", {}
        ).get("channel")
        if not ChannelID:
            logging.warning(
                f"[🏠 on_infraction] @{guild.name} no channel ID found in settings."
            )
            return
        try:
            channel = await guild.fetch_channel(int(ChannelID))
        except Exception as e:
            return print(
                f"[🏠 on_infraction] @{guild.name} the infraction channel can't be found. [1]"
            )
        if channel is None:
            logging.warning(
                f"[🏠 on_infraction] @{guild.name} the infraction channel can't be found. [2]"
            )
            return

        custom = await self.client.db["Customisation"].find_one(
            {
                "guild_id": Infraction.guild_id,
                "type": "Infractions" if Type is None else "Suspension",
            }
        )
        embed = discord.Embed()
        view = None
        if Settings.get("Module Options", {}).get("infractedbybutton"):
            view = InfractionIssuer()
            view.issuer.label = f"Issued By {manager.display_name}"

        if custom:
            replacements = Replacements(
                staff=staff, Infraction=Infraction, manager=manager
            )
            if Type == "Suspension":
                replacements.update(
                    {
                        "{start_time}": f"<t:{int(InfractionData.get('start_time').timestamp())}:f>",
                        "{end_time}": f"<t:{int(InfractionData.get('end_time').timestamp())}:f>",
                    }
                )
            embed = await DisplayEmbed(
                data=custom, user=staff, replacements=replacements
            )
        else:

            embed = DefaultEmbed(InfractionData, staff, manager)
        if not Type:
            embed.set_footer(text=f"Infraction ID | {Infraction.random_string}")

        ch = await self.InfractionTypes(Actions, staff, manager, config=Settings)
        if ch and ch.get("Channel"):
            try:
                N = await self.client.fetch_channel(int(ch.get("Channel")))
            except (discord.Forbidden, discord.NotFound):
                N = None
            if N:
                channel = N
        msg = None
        hook = None
        Status = await premium(guild.id)

        if (
            Settings.get("Infraction", {}).get("Webhook", None)
            and Status
            and Settings.get("Infraction", {}).get("Webhook", {}).get("Enabled") is True
        ):
            Webhook = await self.client.db["Webhooks"].find_one(
                {"Type": "IF", "Channel": channel.id, "Guild": guild.id}
            )

            async def CreateHook(channel: discord.TextChannel):
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.client.user.display_avatar.url) as resp:
                        if resp.status != 200:
                            return None
                        Btyes = await resp.read()
                try:
                    hook = await channel.create_webhook(name="Birb", avatar=Btyes)

                    await self.client.db["Webhooks"].update_one(
                        {"Type": "IF", "Channel": channel.id, "Guild": guild.id},
                        {"$set": {"Id": hook.id}},
                        upsert=True,
                    )
                    return hook
                except discord.Forbidden:
                    return

            if not Webhook or Webhook.get("Id"):
                hook = await CreateHook(channel)

            hook = (
                hook
                or await self.client.fetch_webhook(webhook_id=Webhook.get("Id"))
                or await CreateHook(channel)
            )

            if not hook:
                return

            hook: discord.Webhook

            WS = Settings.get("Infraction").get("Webhook", {})
            if view is not None:
                msg = await hook.send(
                    staff.mention,
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions(users=True),
                    avatar_url=WS.get("Avatar") or None,
                    username=WS.get("Username") or "Birb",
                    wait=True,
                )
            else:
                msg: discord.WebhookMessage = await hook.send(
                    staff.mention,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(users=True),
                    avatar_url=WS.get("Avatar") or None,
                    username=WS.get("Username") or "Birb",
                    wait=True,
                )

        else:
            try:
                msg: discord.Message = await channel.send(
                    staff.mention,
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )

            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                return None

        if Type is None:
            await self.client.db["infractions"].update_one(
                {"_id": objectid},
                {"$set": {"jump_url": msg.jump_url, "msg_id": msg.id, "Updated": ch}},
            )
        else:
            await self.client.db["Suspensions"].update_one(
                {"_id": objectid},
                {"$set": {"jump_url": msg.jump_url, "msg_id": msg.id}},
            )
        self.client.dispatch("infraction_log", objectid, "create", manager)

        consreult = await self.client.db["consent"].find_one({"user_id": staff.id})
        if Settings.get("Module Options", {}).get("Direct Message", True):
            if not consreult or consreult.get("infractionalert") is not False:
                try:
                    await staff.send(
                        content=f"<:SmallArrow:1140288951861649418>From  **{guild.name}**",
                        embed=embed,
                    )
                except:
                    pass
        if Actions and Actions.get("Escalation"):
            Escalation = Actions["Escalation"]
            try:
                Tresh = int(Escalation.get("Threshold", 0))
            except (TypeError, ValueError):
                Tresh = 0

            NextType = Escalation.get("Next Type")
            Reason = Escalation.get("Reason")

            if Tresh > 0 and NextType:
                if Infraction.action == NextType:
                    return

                InfractionsWithType = await self.client.db[
                    "infractions"
                ].count_documents(
                    {
                        "guild_id": guild.id,
                        "staff": staff.id,
                        "action": Infraction.action,
                        "Upscaled": {"$exists": False},
                    }
                )

                if InfractionsWithType >= Tresh:
                    await asyncio.sleep(2)

                    async for previous in self.client.db["infractions"].find(
                        {
                            "guild_id": guild.id,
                            "staff": staff.id,
                            "action": Infraction.action,
                            "Upscaled": {"$exists": False},
                        }
                    ):
                        await self.client.db["infractions"].update_one(
                            {"_id": previous["_id"]}, {"$set": {"Upscaled": True}}
                        )

                    FormedData = {
                        "guild_id": guild.id,
                        "staff": staff.id,
                        "reason": Reason,
                        "action": NextType,
                        "management": manager.id,
                        "notes": "`N/A`",
                        "expiration": None,
                        "random_string": "".join(
                            random.choices(string.ascii_uppercase + string.digits, k=10)
                        ),
                        "annonymous": Infraction.annonymous,
                        "timestamp": datetime.datetime.now(),
                        "auto_escalated": True,
                    }
                    if ch:
                        FormedData["Updated"] = ch

                    EscResult = await self.client.db["infractions"].insert_one(
                        FormedData
                    )

                    TypeActions = await self.client.db[
                        "infractiontypeactions"
                    ].find_one({"guild_id": guild.id, "name": Infraction.action})

                    self.client.dispatch(
                        "infraction", EscResult.inserted_id, Settings, TypeActions
                    )

    async def InfractionTypes(
        self, data, staff: discord.Member, manager: discord.Member, config: dict
    ):
        if not data:
            return

        Actions = {}

        try:
            channel = False
            if data.get("givenroles"):
                roles = data.get("givenroles")
                if not staff.guild.chunked:
                    await staff.guild.chunk()

                roles = [
                    discord.utils.get(staff.guild.roles, id=role)
                    for role in roles
                    if role is not None
                ]
                try:
                    await staff.add_roles(*roles)
                except (discord.Forbidden, discord.HTTPException):
                    pass
                Actions["AddedRoles"] = [role.id for role in roles]
            if data.get("changegrouprole") and data.get("grouprole"):
                from utils.roblox import UpdateMembership

                try:
                    await UpdateMembership(
                        user=staff,
                        role=data.get("grouprole"),
                        author=manager,
                        config=config,
                    )
                except Exception as e:
                    traceback.format_exc(e)
                Actions["ChangedGroupRole"] = True

            if data.get("removedroles"):
                roles = data.get("removedroles")
                if not staff.guild.chunked:
                    await staff.guild.chunk()

                roles = [
                    discord.utils.get(staff.guild.roles, id=role)
                    for role in roles
                    if role is not None
                ]
                try:
                    await staff.remove_roles(*roles)
                except (discord.Forbidden, discord.HTTPException):
                    pass
                Actions["RemovedRoles"] = [role.id for role in roles]
            if data.get("voidshift"):
                result = await self.client.db["integrations"].find_one(
                    {"server": staff.guild.id, "erm": {"$exists": True}}
                )
                if result:
                    result = await voidShift(
                        result.get("erm", None), staff.guild.id, staff.id
                    )
                    if not result:
                        pass
                Actions["VoidedShift"] = True

            if data.get("dbremoval", False) is True:
                OriginalData = await self.client.db["staff database"].find_one(
                    {"staff_id": staff.id}
                )
                await self.client.db["staff database"].delete_one(
                    {"staff_id": staff.id}
                )
                Actions["DbRemoval"] = OriginalData
            if data.get("channel"):
                channel = await staff.guild.fetch_channel(data.get("channel"))
                if not channel:
                    pass
                Actions["Channel"] = data.get("channel")
            if channel:
                client = await staff.guild.fetch_member(self.client.user.id)
                if channel.permissions_for(client).send_messages is False:
                    return

            return Actions
        except:
            pass


class InfractionIssuer(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(
        label=f"",
        style=discord.ButtonStyle.grey,
        disabled=True,
        emoji="<:flag:1223062579346145402>",
    )
    async def issuer(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass


async def setup(client: commands.Bot) -> None:
    await client.add_cog(on_infractions(client))
