FROM python:3.11-alpine
RUN apk add py3-pip
COPY requirements.txt bot.py config.py ./
RUN pip install -r requirements.txt
CMD python bot.py
