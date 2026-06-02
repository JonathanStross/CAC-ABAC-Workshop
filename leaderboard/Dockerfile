FROM python:3.11-slim

WORKDIR /app
COPY leaderboard.py .
COPY level_codes.json /data/level_codes.json

RUN pip install flask

VOLUME ["/data"]
EXPOSE 9000

CMD ["python3", "leaderboard.py"]
