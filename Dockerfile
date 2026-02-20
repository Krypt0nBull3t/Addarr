# filename: Dockerfile
# author: Christian Blank (https://github.com/Cyneric)
# created date: 2024-11-08
# description: Dockerfile for Addarr Refresh Telegram Bot.

FROM python:3.11.5-alpine3.18

WORKDIR /app

# Install requirements
RUN apk add --no-cache \
    transmission-cli

# Copy files to container
COPY . /app

# Install and build Addarr Refresh requirements
RUN	pip install --no-cache-dir -r requirements.txt --upgrade

# Create non-root user and set ownership
RUN addgroup -S addarr && adduser -S addarr -G addarr \
    && chown -R addarr:addarr /app

USER addarr

# Graceful shutdown signal
STOPSIGNAL SIGTERM

# Health check - verify the process is running
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python.*run.py" || exit 1

ENTRYPOINT ["python", "/app/run.py"]
