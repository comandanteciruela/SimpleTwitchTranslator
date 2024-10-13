FROM python:3.11-alpine
RUN apk add py3-pip
RUN pip install -r requirements.txt
COPY bot.py config.py ./
CMD python bot.py
