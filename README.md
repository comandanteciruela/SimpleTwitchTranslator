## Welcome to STT (SimpleTwitchTranslator)

It is a simple bot that makes use of Google Translate without the need for an API key.

It is very similar to [sayonari](https://github.com/sayonari)'s [twitchTransFreeNext](https://github.com/sayonari/twitchTransFreeNext) but simpler.

Written in Python, it primarily makes use of these two libraries: [TwitchIO](https://twitchio.dev/en/stable/) and [async-google-trans-new](https://pypi.org/project/async-google-trans-new/), as well as some other libraries.

### How to use

1. Edit config.py (get your bot's info from [Twitch Token Generator](https://twitchtokengenerator.com))
2. Build the image with Podman: `$ podman build -t stt -f Containerfile`
3. Run the container: `$ podman run --rm -it stt` or `$ podman run --rm -d stt` to leave it in background

Enjoy!
