FROM python:3.11-alpine
RUN apk add build-base python3-dev py3-pip
RUN pip install async_google_trans_new twitchio
COPY bot.py config.py ./
CMD python bot.py
