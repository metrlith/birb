import aiohttp


async def GetIdentifier():
    url = "https://api.ermbot.xyz/api/Auth/GetIdentifier"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            print(f"An error occurred: {e}")
            return None


async def voidShift(api_key=None, guild=None, user=None):
    try:
        if not api_key or not guild or not user:
            return 1
        headers = {"Authorization": api_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=f"https://api.ermbot.xyz/api/Shift/ForceVoidShift/{guild}/{user}",
                headers=headers,
            ) as response:
                response.raise_for_status()
                result = await response.text()
                print("[ERM] Succesfully voided a shift.")
                return result
    except Exception as e:
        print(e)
