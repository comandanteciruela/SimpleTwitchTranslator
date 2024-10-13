from asyncio import run, sleep, create_task
from twitchio.ext import commands
from async_google_trans_new import AsyncTranslator
from random import choice
from config import (
    OAUTH_TOKEN,
    BOT_CLIENT_ID,
    CHANNEL,
    IGNORE_LANG,
    OWNER_TO_PEOPLE,
    IGNORE_USERS,
    MESSAGES,
    MESSAGE_INTERVAL,
    WELCOME_MESSAGE,
)
from aiohttp import ClientSession

DEBUG_PREFIX = "\033[1;33mDEBUG:\033[0m "


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=OAUTH_TOKEN, prefix="!", initial_channels=[CHANNEL]
        )
        self.translator = AsyncTranslator()
        self.websocket_ready = False
        self.bot_id = None
        self.bot_login = None

    async def event_ready(self):

        while True:
            is_connected, bot_data = await self.check_connection()
            if is_connected:
                break
            print(f"{DEBUG_PREFIX}Retrying connection...")
            await sleep(1)

        self.websocket_ready = True
        self.bot_id = bot_data["id"]
        self.bot_display_name = bot_data["display_name"]
        self.bot_connected_channel = self.get_channel(CHANNEL)
        print(f"{DEBUG_PREFIX}Bot data connection info: {bot_data}")
        print(f"{DEBUG_PREFIX}{self.bot_connected_channel}")
        print(f"{DEBUG_PREFIX}Account name: {self.bot_display_name}")
        print(f"{DEBUG_PREFIX}Bot ID: {self.bot_id}")

        if WELCOME_MESSAGE:
            await self.bot_connected_channel.send(WELCOME_MESSAGE)

        create_task(self.send_random_messages())


    async def send_random_messages(self):
        while True:
            await sleep(MESSAGE_INTERVAL)
            if self.websocket_ready and MESSAGES:
                message = choice(MESSAGES)
                await self.bot_connected_channel.send(message)
                print(f"\n{DEBUG_PREFIX}Sent random message: {message}")

    async def check_connection(self):
        print(f"{DEBUG_PREFIX}Trying to connect...")
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
                        print(f"{DEBUG_PREFIX}Successful connection.")
                        data = await response.json()
                        if data.get("data"):
                            return True, data["data"][0]
                        else:
                            print(f"{DEBUG_PREFIX}No user data found.")
                            return False, None
                    else:
                        print(f"{DEBUG_PREFIX}Connection error: {response.status}")
                        return False, None
        except Exception as e:
            print(f"{DEBUG_PREFIX}Connection error: {e}")
            return False, None

    async def event_message(self, message):

        if not self.websocket_ready:
            return

        if message.author is None or message.author.id == self.bot_id:
            return

        if message.author.display_name.lower() in [
            user.lower() for user in IGNORE_USERS
        ]:
            print(f"{DEBUG_PREFIX}User is ignored, won't translate.")
            return

        print(
            f"\n{DEBUG_PREFIX}Message received: {message.content} from {message.author.display_name}"
        )

        await self.handle_commands(message)

        if message.content.startswith("!"):
            return

        await self.handle_translation(message)

    async def handle_translation(self, message):

        try:
            detected_lang = await self.translator.detect(message.content)

            if isinstance(detected_lang, list) and len(detected_lang) == 2:
                lang_code = detected_lang[0].lower()
                is_owner = message.author.display_name.lower() == CHANNEL.lower()

                if lang_code.lower() == IGNORE_LANG.lower() and not is_owner:
                    print(f"{DEBUG_PREFIX}The message was ignored due to language.")
                    return

                target_lang = "es" if lang_code == "en" else OWNER_TO_PEOPLE

                translated_text = await self.translator.translate(
                    message.content, target_lang
                )

                if isinstance(translated_text, list) and translated_text:
                    translated_text = translated_text[0]

                if translated_text:
                    formatted_message = f"{translated_text} [by {message.author.display_name}] ({lang_code} > {target_lang})"
                    await self.bot_connected_channel.send(f"/me {formatted_message}")
                    print(f"{DEBUG_PREFIX}Message sent: {formatted_message}")
                    await sleep(1)

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
