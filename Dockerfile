FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    vlc \
    dbus \
    git \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash dooh_user

WORKDIR /app

COPY . /app

RUN chown -R dooh_user:dooh_user /app

USER dooh_user

CMD ["python3", "src/main.py"]
