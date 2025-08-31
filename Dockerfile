# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy your bot code and credentials
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir \
    python-telegram-bot==13.15 \
    google-api-python-client \
    google-auth-httplib2 \
    google-auth-oauthlib \
    Pillow

# Set environment variables (you can override in Render dashboard)
ENV BOT_TOKEN=""
ENV FOLDER_ID=""

# Run the bot
CMD ["python", "app.py"]