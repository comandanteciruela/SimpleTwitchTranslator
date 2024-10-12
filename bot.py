from asyncio import run, sleep
from twitchio.ext import commands
from async_google_trans_new import AsyncTranslator
from config import (
    OAUTH_TOKEN,
    BOT_CLIENT_ID,
    CHANNEL_NAME,
    IGNORE_LANG,
    OWNER_TO_PEOPLE,
    BOT_NAME,
    IGNORE_USERS,
)
from aiohttp import ClientSession

DEBUG_PREFIX = "\033[1;33mDEBUG:\033[0m "


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=OAUTH_TOKEN, prefix="!", initial_channels=[CHANNEL_NAME])
        self.translator = AsyncTranslator()
        self.websocket_ready = False
        self.bot_id = None
        self.bot_display_name = None

    async def event_ready(self):
        print(
            f'{DEBUG_PREFIX}Trying to connect to channel "{CHANNEL_NAME}" with bot "{BOT_NAME}"!'
        )

        while not await self.check_connection():
            print(f"{DEBUG_PREFIX}Retrying connection...")
            await sleep(1)
        self.websocket_ready = True
        user_data = await self.get_bot_info()
        self.bot_id = user_data["id"]
        self.bot_display_name = user_data["display_name"]
        print(f"{DEBUG_PREFIX}User Data: {user_data}")
        print(f'{DEBUG_PREFIX}Connected channel: {user_data["login"]}')
        print(f"{DEBUG_PREFIX}Account name: {self.bot_display_name}")
        print(f"{DEBUG_PREFIX}Bot ID: {self.bot_id}")

    async def check_connection(self):
        print(f"{DEBUG_PREFIX}Performing connection check...")
        try:
            async with ClientSession() as session:
                async with session.get(
                    "https://api.twitch.tv/helix/users",
                    headers={
                        "Authorization": f"Bearer {OAUTH_TOKEN}",
                        "Client-Id": BOT_CLIENT_ID,
                    },
                ) as response:
                    if response.status == 200:
                        print(f"{DEBUG_PREFIX}Ping to server successful.")
                        return True
                    else:
                        print(f"{DEBUG_PREFIX}Ping error: {response.status}")
                        return False
        except Exception as e:
            print(f"{DEBUG_PREFIX}Error sending ping: {e}")
            return False

    async def get_bot_info(self):
        async with ClientSession() as session:
            async with session.get(
                "https://api.twitch.tv/helix/users",
                headers={
                    "Authorization": f"Bearer {OAUTH_TOKEN}",
                    "Client-Id": BOT_CLIENT_ID,
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data"):
                        return data["data"][0]
        return None

    async def event_message(self, message):

        if not self.websocket_ready:
            return

        if message.author is None or (self.bot_id and message.author.id == self.bot_id):
            return

        print("\n")
        print(
            f"{DEBUG_PREFIX}Message received: {message.content} from {message.author.display_name}"
        )

        await self.handle_commands(message)

        if message.content.startswith("!"):
            return

        await self.handle_translation(message)

    async def handle_translation(self, message):
        try:
            print(f"{DEBUG_PREFIX}Checking if the language should be ignored...")
            detected_lang = await self.translator.detect(message.content)

            if isinstance(detected_lang, list) and len(detected_lang) >= 2:
                lang_code = detected_lang[0].lower()
                print(f"{DEBUG_PREFIX}Detected language: {lang_code}")

                if (
                    lang_code == IGNORE_LANG
                    and message.author.display_name.lower() != CHANNEL_NAME.lower()
                ):
                    print(f"{DEBUG_PREFIX}The message was ignored due to language.")
                    return

                target_lang = "es" if lang_code == "en" else OWNER_TO_PEOPLE

                translated_text = await self.translator.translate(
                    message.content, target_lang
                )

                if isinstance(translated_text, list) and translated_text:
                    translated_text = translated_text[0]

                if translated_text:
                    print(
                        f"{DEBUG_PREFIX}Translating message: {translated_text} (from {lang_code})"
                    )
                    channel = self.get_channel(CHANNEL_NAME)
                    if channel:
                        await sleep(1)
                        formatted_message = f"/me {translated_text} [by {message.author.display_name}] ({lang_code} > {target_lang})"
                        await channel.send(formatted_message)
                        print(f"{DEBUG_PREFIX}Message sent: {formatted_message}")
                    else:
                        print(f"{DEBUG_PREFIX}Error: Channel {CHANNEL_NAME} not found.")
                else:
                    print(f"{DEBUG_PREFIX}Could not translate the message.")
            else:
                print(f"{DEBUG_PREFIX}Error: Detection response is not valid.")
        except Exception as e:
            print(f"{DEBUG_PREFIX}Error processing the message: {e}")


async def main():
    bot = Bot()
    await bot.start()


if __name__ == "__main__":
    run(main())
