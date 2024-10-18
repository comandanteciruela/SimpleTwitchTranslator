from asyncio import run, sleep, create_task
from twitchio.ext import commands
from twitchio.ext.commands import Command
from async_google_trans_new import AsyncTranslator
from random import choice
from sys import exit
from os.path import join, exists, abspath
from importlib.util import spec_from_file_location, module_from_spec

import ssl
import certifi

ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

ERROR_BOLD_RED = "\033[1;31mERROR!\033[0m "
OK_BOLD_GREEN = "\033[1;32mOK!\033[0m "
LIGHT_GRAY = "\033[0;37m"
RESET = "\033[0m"


def is_valid(token):
    return isinstance(token, str) and len(token) > 18 and token.isalnum()


def contains_repetitions(msg):
    words = msg.split()
    count = {}
    unique_words = set()

    for word in words:
        if word in count:
            count[word] += 1
        else:
            count[word] = 1
            unique_words.add(word)

    has_repetition = any(c >= 2 for c in count.values())
    has_unique_word = len(unique_words) > 1

    return has_repetition, has_unique_word


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
DEFAULT_ORDERED_MESSAGES_INTERVAL = 2400

try:
    if not isinstance(config.BOT_INTRO_MESSAGES, list):
        print(f"{ERROR_BOLD_RED}BOT_INTRO_MESSAGES must be a list.")
        BOT_INTRO_MESSAGES = []
    else:
        BOT_INTRO_MESSAGES = config.BOT_INTRO_MESSAGES
except AttributeError:
    BOT_INTRO_MESSAGES = []

try:
    if not isinstance(config.RANDOM_MESSAGES, list):
        print(f"{ERROR_BOLD_RED}RANDOM_MESSAGES must be a list.")
        RANDOM_MESSAGES = []
    else:
        RANDOM_MESSAGES = config.RANDOM_MESSAGES
except AttributeError:
    RANDOM_MESSAGES = []

try:
    if not isinstance(config.ORDERED_MESSAGES, list):
        print(f"{ERROR_BOLD_RED}ORDERED_MESSAGES must be a list.")
        ORDERED_MESSAGES = []
    else:
        ORDERED_MESSAGES = config.ORDERED_MESSAGES
except AttributeError:
    ORDERED_MESSAGES = []

try:
    if not isinstance(config.IGNORE_USERS, list):
        print(f"{ERROR_BOLD_RED}IGNORE_USERS must be a list.")
        IGNORE_USERS = []
    else:
        IGNORE_USERS = config.IGNORE_USERS
except AttributeError:
    IGNORE_USERS = []

try:
    if not isinstance(config.MESSAGES, dict):
        print(f"{ERROR_BOLD_RED}MESSAGES must be a dictionary.")
        MESSAGES = []
    else:
        MESSAGES = config.MESSAGES
except AttributeError:
    MESSAGES = {}

try:
    if (
        not isinstance(config.RANDOM_MESSAGES_INTERVAL, int)
        or config.RANDOM_MESSAGES_INTERVAL <= 0
    ):
        print(
            f"{ERROR_BOLD_RED}Invalid RANDOM_MESSAGES_INTERVAL. RANDOM_MESSAGES_INTERVAL must be a positive integer. Defaulting to {DEFAULT_RANDOM_MESSAGES_INTERVAL} seconds."
        )
        RANDOM_MESSAGES_INTERVAL = DEFAULT_RANDOM_MESSAGES_INTERVAL
    else:
        RANDOM_MESSAGES_INTERVAL = config.RANDOM_MESSAGES_INTERVAL
except AttributeError:
    RANDOM_MESSAGES_INTERVAL = DEFAULT_RANDOM_MESSAGES_INTERVAL

try:
    if (
        not isinstance(config.ORDERED_MESSAGES_INTERVAL, int)
        or config.ORDERED_MESSAGES_INTERVAL <= 0
    ):
        print(
            f"{ERROR_BOLD_RED}Invalid ORDERED_MESSAGES_INTERVAL. ORDERED_MESSAGES_INTERVAL must be a positive integer. Defaulting to {DEFAULT_ORDERED_MESSAGES_INTERVAL} seconds."
        )
        ORDERED_MESSAGES_INTERVAL = DEFAULT_ORDERED_MESSAGES_INTERVAL
    else:
        ORDERED_MESSAGES_INTERVAL = config.ORDERED_MESSAGES_INTERVAL
except AttributeError:
    ORDERED_MESSAGES_INTERVAL = DEFAULT_ORDERED_MESSAGES_INTERVAL

try:
    if not isinstance(config.IGNORE_TEXT, list):
        print(f"{ERROR_BOLD_RED}IGNORE_TEXT must be a list.")
        IGNORE_TEXT = []
    IGNORE_TEXT = config.IGNORE_TEXT
except AttributeError:
    IGNORE_TEXT = []


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=BOT_OAUTH_TOKEN, prefix="!", initial_channels=[CHANNEL_NAME], ssl_context=ssl_context
        )
        self.translator = AsyncTranslator()

    def create_commands(self):

        for key, message_template in MESSAGES.items():

            async def command(ctx, message_template=message_template):
                user = ctx.author.display_name
                message = message_template.format(user=user)
                await ctx.send(message)

            command.__name__ = key
            command_instance = Command(name=key, func=command)
            self.add_command(command_instance)

        async def help_command(ctx):
            command_list = ", ".join(f"!{command}" for command in MESSAGES.keys())
            await ctx.send(f"Available commands: {command_list}")

        help_command.__name__ = "help"
        help_command_instance = Command(name="help", func=help_command)
        self.add_command(help_command_instance)

        commands_command_instance = Command(name="commands", func=help_command)
        self.add_command(commands_command_instance)

    async def event_ready(self):

        self.bot_connected_channel = self.get_channel(CHANNEL_NAME)

        print(f"Connected. {OK_BOLD_GREEN}")
        print(f"Bot name: {self.nick}")
        print(f"Channel name: {self.bot_connected_channel.name}")

        self.create_commands()

        if BOT_INTRO_MESSAGES and isinstance(BOT_INTRO_MESSAGES, list):
            intro_message = choice(BOT_INTRO_MESSAGES)
            await self.bot_connected_channel.send(intro_message)

        create_task(self.send_random_messages())
        create_task(self.send_ordered_messages())

    async def send_ordered_messages(self):
        interval = ORDERED_MESSAGES_INTERVAL
        index = 0
        while True:
            await sleep(interval)
            if ORDERED_MESSAGES and isinstance(ORDERED_MESSAGES[index], str):
                message = ORDERED_MESSAGES[index]
                await self.bot_connected_channel.send(message)
                print(f"\n⭐ Sent ordered message: {message}")

                index += 1
                if index >= len(ORDERED_MESSAGES):
                    index = 0

    async def send_random_messages(self):
        interval = RANDOM_MESSAGES_INTERVAL
        while True:
            await sleep(interval)
            if RANDOM_MESSAGES and any(isinstance(msg, str) for msg in RANDOM_MESSAGES):
                message = choice(RANDOM_MESSAGES)
                await self.bot_connected_channel.send(message)
                print(f"\n⭐ Sent random message: {message}")

    async def event_message(self, message):

        if message.author is None or message.author.id == self.nick:
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
        await self.handle_translation(message)

    async def event_command_error(self, context: commands.Context, error: Exception):
        if isinstance(error, commands.CommandNotFound):
            print(
                f"{ERROR_BOLD_RED}Command not found. Use !help to see a list of available commands."
            )
            await context.send(
                "Command not found. Use !help to see a list of available commands."
            )
        else:
            print(f"{ERROR_BOLD_RED}Something happened: {str(error)}")

    async def handle_translation(self, message):
        if message.content.startswith("!"):
            return

        print(f"\n{message.author.display_name}: {message.content}")

        has_repetition, has_unique_word = contains_repetitions(message.content)
        if has_repetition and not has_unique_word:
            print(f"{LIGHT_GRAY}Not translating.{RESET}")
            return

        try:
            detected_lang = await self.translator.detect(message.content)

            if isinstance(detected_lang, list) and len(detected_lang) == 2:
                detected_lang = detected_lang[0].lower()
                is_owner = message.author.display_name.lower() == CHANNEL_NAME.lower()

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

                translated_text = await self.translator.translate(
                    message.content, target_lang
                )

                if isinstance(translated_text, list) and translated_text:
                    translated_text = translated_text[0]

                if translated_text:
                    formatted_message = f"{translated_text} [by {message.author.display_name}] ({detected_lang} > {target_lang})"
                    print(f"✅ Message sent: {formatted_message}")
                    await self.bot_connected_channel.send(f"/me {formatted_message}")

                else:
                    print(f"{ERROR_BOLD_RED}Could not translate the message.")
            else:
                print(f"{ERROR_BOLD_RED}Detection response is not valid.")
        except Exception as e:
            print(f"{ERROR_BOLD_RED}Could not process the message: {e}")


async def main():
    bot = Bot()
    await bot.start()


if __name__ == "__main__":
    run(main())
