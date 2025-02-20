from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
import os
from bson import ObjectId
import asyncio
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = ""
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]

custom_commands = db["Custom Commands"]
Customisation = db["Customisation"]

async def TransformData():
    print("Starting TransformData...")
    data = await Customisation.find({}).to_list(length=None)
    bulk_operations = []
    for entry in data:
        dat = {
            "type": entry.get("type"),
            "guild_id": entry.get("guild_id", None),
            "content": entry.get("content", None),
            "creator": entry.get("creator", None),
            "embed": {
                "title": entry.get("title"),
                "description": entry.get("description"),
                "thumbnail": entry.get("thumbnail"),
                "color": entry.get("color"),
                "author": {
                    "name": entry.get("author"),
                    "icon_url": entry.get("author_icon"),
                },
            },
        }

        if not dat:
            continue

        bulk_operations.append(
            UpdateOne({"_id": ObjectId(entry.get("_id"))}, {"$set": dat})
        )

    if bulk_operations:
        try:
            result = await Customisation.bulk_write(bulk_operations)
            print(f"Bulk update completed for {result.modified_count} documents.")
        except Exception as e:
            print(f"Error during bulk update: {e}")
    else:
        print("No operations to perform in Customisation.")

    print("Data transformation and update complete!")

async def TransformCustomCommands():
    print("Starting TransformCustomCommands...")
    data = await custom_commands.find({}).to_list(length=None)
    bulk_operations = []
    for entry in data:
        dat = {
            "guild_id": entry.get("guild_id", None),
            "content": entry.get("content", None),
            "name": entry.get('name'),
            'Command': entry.get('Command'),
            "creator": entry.get("creator", None),
            "embed": {
                "title": entry.get("title"),
                "description": entry.get("description"),
                "thumbnail": entry.get("thumbnail"),
                "color": entry.get("color"),
                "author": {
                    "name": entry.get("author"),
                    "icon_url": entry.get("author_icon"),
                },
            },
        }

        bulk_operations.append(
            UpdateOne({"_id": ObjectId(entry.get("_id"))}, {"$set": dat})
        )

    if bulk_operations:
        try:
            result = await custom_commands.bulk_write(bulk_operations)
            print(f"Bulk update completed for {result.modified_count} custom commands.")
        except Exception as e:
            print(f"Error during bulk update: {e}")
    else:
        print("No operations to perform in Custom Commands.")

    print("Custom commands transformation complete!")

async def main():
    print("Starting the transformation process...")
    try:
        await asyncio.gather(
            TransformData(),
            TransformCustomCommands(),
        )
    except Exception as e:
        print(f"Error during execution: {e}")
    print("Transformation process finished!")

if __name__ == "__main__":
    asyncio.run(main())
