from asyncio import run, sleep, create_task
from aiohttp import ClientSession
from twitchio.ext import commands
from async_google_trans_new import AsyncTranslator
from random import choice
from sys import exit
from os.path import join, exists, abspath
from importlib.util import spec_from_file_location, module_from_spec

ERROR_BOLD_RED = "\033[1;31mERROR!\033[0m "
OK_BOLD_GREEN = "\033[1;32mOK!\033[0m "
LIGHT_GRAY = "\033[0;37m"
RESET = "\033[0m"


def is_valid(token):
    return isinstance(token, str) and len(token) > 18 and token.isalnum()


current_dir = abspath(".")

config_path = join(current_dir, "config.py")

if not exists(config_path):
    print(f"{ERROR_BOLD_RED}config.py is not in {current_dir}.")
    exit(1)

try:
    spec = spec_from_file_location("config", config_path)
    config = module_from_spec(spec)
    spec.loader.exec_module(config)
    BOT_OAUTH_TOKEN = config.BOT_OAUTH_TOKEN
    BOT_CLIENT_ID = config.BOT_CLIENT_ID
    CHANNEL_NAME = config.CHANNEL_NAME
    CHANNEL_NATIVE_LANG = config.CHANNEL_NATIVE_LANG
    TRANSLATE_TO_LANG = config.TRANSLATE_TO_LANG


except Exception as e:
    print(f"{ERROR_BOLD_RED}Couldn't load config.py correctly: {e}")
    exit(1)

    for var, name in zip(
        [BOT_OAUTH_TOKEN, BOT_CLIENT_ID], ["BOT_OAUTH_TOKEN", "BOT_CLIENT_ID"]
    ):
        if not is_valid(var):
            print(
                f"{ERROR_BOLD_RED}{name} must be a string with more than 18 alphanumeric characters."
            )
            exit(1)

    if not (isinstance(CHANNEL_NATIVE_LANG, str) and len(CHANNEL_NATIVE_LANG) == 2):
        print(
            f"{ERROR_BOLD_RED}CHANNEL_NATIVE_LANG must be a string with exactly 2 characters. Examples: es, en, ja, ru"
        )
        exit(1)

    if not (isinstance(TRANSLATE_TO_LANG, str) and len(TRANSLATE_TO_LANG) == 2):
        print(
            f"{ERROR_BOLD_RED}TRANSLATE_TO_LANG must be a string with exactly 2 characters. Examples: es, en, ja, ru"
        )
        exit(1)

except Exception as e:
    print(f"{ERROR_BOLD_RED}Couldn't load config.py correctly: {e}")
    exit(1)

DEFAULT_RANDOM_MESSAGES_INTERVAL = 2400

try:
    BOT_INTRO_MESSAGES = config.BOT_INTRO_MESSAGES
except AttributeError:
    BOT_INTRO_MESSAGES = []

try:
    RANDOM_MESSAGES = config.RANDOM_MESSAGES
except AttributeError:
    RANDOM_MESSAGES = []

try:
    IGNORE_USERS = config.IGNORE_USERS
except AttributeError:
    IGNORE_USERS = []

try:
    RANDOM_MESSAGES_INTERVAL = config.RANDOM_MESSAGES_INTERVAL
except AttributeError:
    RANDOM_MESSAGES_INTERVAL = DEFAULT_RANDOM_MESSAGES_INTERVAL

try:
    IGNORE_TEXT = config.IGNORE_TEXT
except AttributeError:
    IGNORE_TEXT = []


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=BOT_OAUTH_TOKEN, prefix="!", initial_channels=[CHANNEL_NAME]
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
            print(f"Retrying connection...")
            await sleep(1)

        self.websocket_ready = True
        self.bot_id = bot_data["id"]
        self.bot_display_name = bot_data["display_name"]
        self.bot_connected_channel = self.get_channel(CHANNEL_NAME)
        print(f"\n<Bot name: {self.bot_display_name}>")
        print(f"{self.bot_connected_channel}")


        if isinstance(BOT_INTRO_MESSAGES, list) and BOT_INTRO_MESSAGES:
            intro_message = choice(BOT_INTRO_MESSAGES)
            await self.bot_connected_channel.send(intro_message)
            await sleep(1)

        create_task(self.send_random_messages())

    async def send_random_messages(self):
        interval = RANDOM_MESSAGES_INTERVAL

        if not (isinstance(interval, (int, float)) and interval > 0):
            print(
                f"{ERROR_BOLD_RED}Invalid RANDOM_MESSAGES_INTERVAL; defaulting to {DEFAULT_RANDOM_MESSAGES_INTERVAL} seconds."
            )
            interval = DEFAULT_RANDOM_MESSAGES_INTERVAL

        while True:
            await sleep(interval)
            if (
                self.websocket_ready
                and RANDOM_MESSAGES
                and any(isinstance(msg, str) for msg in RANDOM_MESSAGES)
            ):
                message = choice(RANDOM_MESSAGES)
                await self.bot_connected_channel.send(message)
                await sleep(1)
                print(f"\nSent random message: {message}")

    async def check_connection(self):
        print(f"Trying to connect...")
        try:
            async with ClientSession() as session:
                async with session.get(
                    "https://api.twitch.tv/helix/users",
                    headers={
                        "Authorization": f"Bearer {BOT_OAUTH_TOKEN}",
                        "Client-Id": BOT_CLIENT_ID,
                    },
                ) as response:
                    if response.status == 200:
                        print(
                            f"Successful connection. {OK_BOLD_GREEN}"
                        )
                        data = await response.json()
                        if data.get("data"):
                            return True, data["data"][0]
                        else:
                            print(
                                f"{ERROR_BOLD_RED}No user data found."
                            )
                            return False, None
                    else:
                        print(
                            f"{ERROR_BOLD_RED}Connection response: {response.status}"
                        )
                        return False, None
        except Exception as e:
            print(f"{ERROR_BOLD_RED}Connection broken. Error: {e}")
            return False, None

    async def event_message(self, message):
        if not self.websocket_ready:
            return

        if message.author is None or message.author.id == self.bot_id:
            return

        if isinstance(IGNORE_USERS, list) and any(
            isinstance(user, str) for user in IGNORE_USERS
        ):
            if message.author.display_name.lower() in [
                user.lower() for user in IGNORE_USERS
            ]:
                print(f"{LIGHT_GRAY} is ignored. Not translating.{RESET}")
                return

        if any(word.lower() in message.content.lower() for word in IGNORE_TEXT):
            return

        await self.handle_commands(message)

        if message.content.startswith("!"):
            return

        await self.handle_translation(message)

    async def handle_translation(self, message):
        try:
            await sleep(0.35)
            detected_lang = await self.translator.detect(message.content)

            if isinstance(detected_lang, list) and len(detected_lang) == 2:
                detected_lang = detected_lang[0].lower()
                is_owner = message.author.display_name.lower() == CHANNEL_NAME.lower()

                print(f"\n{message.author.display_name} ({detected_lang}): {message.content}")

                if is_owner:
                    if detected_lang == CHANNEL_NATIVE_LANG:
                        target_lang = TRANSLATE_TO_LANG
                    else:
                        target_lang = CHANNEL_NATIVE_LANG
                else:
                    if detected_lang == CHANNEL_NATIVE_LANG:
                        print(f"{LIGHT_GRAY}Not translating.{RESET}")
                        return
                    else:
                        target_lang = CHANNEL_NATIVE_LANG

                await sleep(0.35)
                translated_text = await self.translator.translate(
                    message.content, target_lang
                )

                if isinstance(translated_text, list) and translated_text:
                    translated_text = translated_text[0]

                if translated_text:
                    formatted_message = f"{translated_text} [by {message.author.display_name}] ({detected_lang} > {target_lang})"
                    print(f"✅ Message sent: {formatted_message}")
                    await self.bot_connected_channel.send(f"/me {formatted_message}")
                    await sleep(0.35)

                else:
                    print(
                        f"{ERROR_BOLD_RED}Could not translate the message."
                    )
            else:
                print(
                    f"{ERROR_BOLD_RED}Detection response is not valid."
                )
        except Exception as e:
            print(
                f"{ERROR_BOLD_RED}Could not process the message: {e}"
            )


async def main():
    bot = Bot()
    await bot.start()


if __name__ == "__main__":
    run(main())
