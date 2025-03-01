from datetime import timedelta, datetime
import discord
from utils import Paginator
import os

def DefaultTypes():
    return [
        "Activity Notice",
        "Verbal Warning",
        "Warning",
        "Strike",
        "Demotion",
        "Termination",
    ]


async def IsSeperateBot():
    return any([os.getenv("CUSTOM_GUILD"), os.getenv("DEFAULT_ALLOWED_SERVERS"), os.getenv("REMOVE_EMOJIS")])

async def PaginatorButtons(extra: list = None):
    Sep = await IsSeperateBot()
    emojis = {
        "first": "<:chevronsleft:1220806428726661130>",
        "previous": "<:chevronleft:1220806425140531321>",
        "next": "<:chevronright:1220806430010118175>",
        "last": "<:chevronsright:1220806426583371866>",
    }
    paginator = Paginator.Simple(
        PreviousButton=discord.ui.Button(
            emoji=emojis["previous"] if not Sep else None,
            label="<<" if Sep else None,
        ),
        NextButton=discord.ui.Button(
            emoji=emojis["next"] if not Sep else None,
            label=">>" if Sep else None,
        ),
        FirstEmbedButton=discord.ui.Button(
            emoji=emojis["first"] if not Sep else None,
            label="<<" if Sep else None,
        ),
        LastEmbedButton=discord.ui.Button(
            emoji=emojis["last"] if not Sep else None,
            label=">>" if Sep else None,
        ),
        InitialPage=0,
        timeout=360,
        extra=extra or [],
    )
    return paginator

async def strtotime(duration: int, back: bool = False):
    now = datetime.now()
    DurationValue = int(duration[:-1])
    DurationUnit = duration[-1]
    DurationSeconds = DurationValue
    if DurationUnit == "s":
        DurationSeconds *= 1
    elif DurationUnit == "m":
        DurationSeconds *= 60
    elif DurationUnit == "h":
        DurationSeconds *= 3600
    elif DurationUnit == "d":
        DurationSeconds *= 86400
    elif DurationUnit == "w":
        DurationSeconds *= 604800

    if back:
        return now - timedelta(seconds=DurationSeconds)
    else:
     return now + timedelta(seconds=DurationSeconds)


def ordinal(n):
    if 10 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def Replace(text, replacements):
    if text is None:
        return text
    for placeholder, replacement in replacements.items():
        if isinstance(replacement, (str, int, float)): 
            text = text.replace(placeholder, str(replacement))
        elif isinstance(replacement, tuple) and len(replacement) > 0:  
            text = text.replace(placeholder, str(replacement[0]))  
        else:
            text = text.replace(placeholder, '')  
    return text
