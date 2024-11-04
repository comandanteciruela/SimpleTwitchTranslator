from asyncio import run, sleep, create_task
from twitchio.ext import commands
from twitchio.ext.commands import Command
from async_google_trans_new import AsyncTranslator
from random import choice
from sys import exit
from os.path import join, exists, abspath
from importlib.util import spec_from_file_location, module_from_spec

ERROR_BOLD_RED = "\033[1;31mERROR!\033[0m "
OK_BOLD_GREEN = "\033[1;32mOK!\033[0m "
LIGHT_GRAY = "\033[0;37m"
RESET = "\033[0m"

def is_valid_token(token):
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

def load_config():
    current_dir = abspath(".")
    config_path = join(current_dir, "config.py")

    if not exists(config_path):
        print(f"{ERROR_BOLD_RED}config.py is not in {current_dir}.")
        exit(1)

    try:
        spec = spec_from_file_location("config", config_path)
        config = module_from_spec(spec)
        spec.loader.exec_module(config)

        required_vars = {
            "BOT_OAUTH_TOKEN": config.BOT_OAUTH_TOKEN,
            "BOT_CLIENT_ID": config.BOT_CLIENT_ID,
            "CHANNEL_NAME": config.CHANNEL_NAME,
            "CHANNEL_NATIVE_LANG": config.CHANNEL_NATIVE_LANG,
            "TRANSLATE_TO_LANG": config.TRANSLATE_TO_LANG
        }

        for var_name, var_value in required_vars.items():
            if not isinstance(var_value, str) or not var_value:
                print(f"{ERROR_BOLD_RED}{var_name} must be a valid non-empty string.")
                exit(1)

        if not is_valid_token(config.BOT_OAUTH_TOKEN):
            print(f"{ERROR_BOLD_RED}BOT_OAUTH_TOKEN must be a valid token.")
            exit(1)

        if not (len(config.CHANNEL_NATIVE_LANG) == 2):
            print(f"{ERROR_BOLD_RED}CHANNEL_NATIVE_LANG must be a 2-character string.")
            exit(1)

        if not (len(config.TRANSLATE_TO_LANG) == 2):
            print(f"{ERROR_BOLD_RED}TRANSLATE_TO_LANG must be a 2-character string.")
            exit(1)

        return {
            "BOT_OAUTH_TOKEN": config.BOT_OAUTH_TOKEN,
            "BOT_CLIENT_ID": config.BOT_CLIENT_ID,
            "CHANNEL_NAME": config.CHANNEL_NAME,
            "CHANNEL_NATIVE_LANG": config.CHANNEL_NATIVE_LANG,
            "TRANSLATE_TO_LANG": config.TRANSLATE_TO_LANG,
            "BOT_INTRO_MESSAGES": getattr(config, "BOT_INTRO_MESSAGES", []),
            "RANDOM_MESSAGES": getattr(config, "RANDOM_MESSAGES", []),
            "ORDERED_MESSAGES": getattr(config, "ORDERED_MESSAGES", []),
            "IGNORE_USERS": getattr(config, "IGNORE_USERS", []),
            "CUSTOM_COMMANDS": getattr(config, "CUSTOM_COMMANDS", {}),
            "RANDOM_MESSAGES_INTERVAL": getattr(config, "RANDOM_MESSAGES_INTERVAL", 2400),
            "ORDERED_MESSAGES_INTERVAL": getattr(config, "ORDERED_MESSAGES_INTERVAL", 2400),
            "IGNORE_TEXT": getattr(config, "IGNORE_TEXT", [])
        }

    except Exception as e:
        print(f"{ERROR_BOLD_RED}Couldn't load config.py correctly: {e}")
        exit(1)

config = load_config()

BOT_OAUTH_TOKEN = config["BOT_OAUTH_TOKEN"]
BOT_CLIENT_ID = config["BOT_CLIENT_ID"]
CHANNEL_NAME = config["CHANNEL_NAME"]
CHANNEL_NATIVE_LANG = config["CHANNEL_NATIVE_LANG"]
TRANSLATE_TO_LANG = config["TRANSLATE_TO_LANG"]
BOT_INTRO_MESSAGES = config["BOT_INTRO_MESSAGES"]
RANDOM_MESSAGES = config["RANDOM_MESSAGES"]
ORDERED_MESSAGES = config["ORDERED_MESSAGES"]
IGNORE_USERS = config["IGNORE_USERS"]
CUSTOM_COMMANDS = config["CUSTOM_COMMANDS"]
RANDOM_MESSAGES_INTERVAL = config["RANDOM_MESSAGES_INTERVAL"]
ORDERED_MESSAGES_INTERVAL = config["ORDERED_MESSAGES_INTERVAL"]
IGNORE_TEXT = config["IGNORE_TEXT"]

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=BOT_OAUTH_TOKEN, prefix="!", initial_channels=[CHANNEL_NAME]
        )
        self.translator = AsyncTranslator()
        self.current_raffle_name = None
        self.roulette_command_name = None
        self.RAFFLE_USERS = []
        self.raffle_reminder_task = None

    async def send_raffle_reminder(self):
        while self.current_raffle_name is not None:
            await sleep(30)
            reminder_message = f"Please join the raffle 🎲 !{self.roulette_command_name} 🎲"
            await self.bot_connected_channel.send(reminder_message)
            print(reminder_message)

    def add_roulette_command(self):
        if self.roulette_command_name:
            if self.roulette_command_name in self.commands:
                print(f"{ERROR_BOLD_RED}Command <{self.roulette_command_name}> already exists. Removing it.")
                self.remove_command(self.roulette_command_name)

        async def raffle_command(ctx):
            user = ctx.author.display_name
            if user in self.RAFFLE_USERS:
                message = f"❌ {user}, you are already registered for the raffle."
                await ctx.send(message)
                print(message)
            else:
                self.RAFFLE_USERS.append(user)
                participant_count = len(self.RAFFLE_USERS)
                message = f"✅ {user} has registered for the {self.roulette_command_name} raffle. Total participants: {participant_count}."
                await ctx.send(message)
                print(message)

        raffle_command.__name__ = self.roulette_command_name
        raffle_command_instance = Command(name=self.roulette_command_name, func=raffle_command)
        self.add_command(raffle_command_instance)

    def remove_roulette_command(self):
        if self.current_raffle_name:
            self.remove_command(self.current_raffle_name)
            self.current_raffle_name = None

    def create_commands(self):
        async def roulette_command(ctx, raffle_name: str = None):
            if ctx.author.display_name.lower() != CHANNEL_NAME.lower():
                message = "🤬 Only the channel owner can use this command."
                await ctx.send(message)
                print(message)
                return

            if raffle_name is None:
                if self.current_raffle_name is not None:
                    message = f"There is already an active raffle 🎲 !{self.current_raffle_name} 🎲 Use !roulette end or !roulette off to end it and pick a winner."
                    await ctx.send(message)
                    print(message)
                else:
                    message = "❌ Please provide a name for the raffle. Example: !roulette <rafflename>"
                    await ctx.send(message)
                    print(message)
                return

            if self.current_raffle_name is None:
                self.current_raffle_name = raffle_name
                self.roulette_command_name = raffle_name
                self.RAFFLE_USERS.clear()
                message = f"\nRaffle started 🎲 !{self.current_raffle_name} 🎲"
                await ctx.send(message)
                print(message)
                self.add_roulette_command()
                if self.raffle_reminder_task is None:
                    self.raffle_reminder_task = create_task(self.send_raffle_reminder())
            else:
                if raffle_name.lower() in ["off", "end"]:
                    if not self.RAFFLE_USERS:
                        message = "😭 There are no users registered for the raffle. No winners. Raffle ended."
                        await ctx.send(message)
                        print(message)
                    else:
                        winner = choice(self.RAFFLE_USERS)
                        participant_count = len(self.RAFFLE_USERS)
                        message = f"🏆🎉✨ The winner of 🎲 !{self.roulette_command_name} 🎲 is {winner}! 🎊🎈🎆 Total participants: {participant_count}"
                        await ctx.send(message)
                        print(message)

                    self.RAFFLE_USERS.clear()
                    self.remove_roulette_command()
                    self.current_raffle_name = None
                    self.roulette_command_name = None
                    self.raffle_reminder_task.cancel()
                    self.raffle_reminder_task = None
                else:
                    message = f"There is already an active raffle 🎲 !{self.current_raffle_name} 🎲 Use !roulette end or !roulette off to end it and pick a winner."
                    await ctx.send(message)
                    print(message)

        roulette_command.__name__ = "roulette"
        roulette_command_instance = Command(name="roulette", func=roulette_command)
        self.add_command(roulette_command_instance)

        async def roulette_users_command(ctx):
            if ctx.author.display_name.lower() != CHANNEL_NAME.lower():
                message = "🤬 Only the channel owner can use this command."
                await ctx.send(message)
                print(message)
                return

            if self.roulette_command_name is None:
                message = "🫥 There is no active raffle."
                await ctx.send(message)
                print(message)
            elif not self.RAFFLE_USERS:
                message = f"😭 There are no users registered for the raffle 🎲 !{self.current_raffle_name} 🎲."
                await ctx.send(message)
                print(message)
            else:
                users_list = ", ".join(self.RAFFLE_USERS)
                message = f"Registered users for the raffle 🎲 !{self.roulette_command_name} 🎲: {users_list}"
                await ctx.send(message)
                print(message)

        roulette_users_command.__name__ = "rouletteusers"
        roulette_users_command_instance = Command(name="rouletteusers", func=roulette_users_command)
        self.add_command(roulette_users_command_instance)

        for key, message_template in CUSTOM_COMMANDS.items():
            async def command(ctx, message_template=message_template):
                user = ctx.author.display_name
                message = message_template.format(user=user)
                await ctx.send(message)
                print(message)

            command.__name__ = key
            command_instance = Command(name=key, func=command)
            self.add_command(command_instance)

        async def help_command(ctx):
            command_list = [f"!{command}" for command in CUSTOM_COMMANDS.keys()]
            command_list.append("!roulette")

            if command_list:
                message = f"Available commands: {', '.join(command_list)}"
                await ctx.send(message)
                print(message)
            else:
                message = f"Available commands: {command_list}"
                await ctx.send(message)
                print(message)

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

        if BOT_INTRO_MESSAGES:
            intro_message = choice(BOT_INTRO_MESSAGES)
            await self.bot_connected_channel.send(intro_message)
            print(intro_message)

        create_task(self.send_random_messages())
        create_task(self.send_ordered_messages())

    async def send_ordered_messages(self):
        index = 0
        while True:
            await sleep(ORDERED_MESSAGES_INTERVAL)
            if ORDERED_MESSAGES and isinstance(ORDERED_MESSAGES[index], str):
                message = ORDERED_MESSAGES[index]
                await self.bot_connected_channel.send(message)
                print(f"\n⭐ Sent ordered message: {message}")

                index += 1
                if index >= len(ORDERED_MESSAGES):
                    index = 0

    async def send_random_messages(self):
        while True:
            await sleep(RANDOM_MESSAGES_INTERVAL)
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
            message = "Command not found. Use !help to see a list of available commands."
            await context.send(message)
            print(message)
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
