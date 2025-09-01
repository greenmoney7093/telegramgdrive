# Use Python 3.12 slim image
FROM python:3.12-slim




# Set working directory inside container
WORKDIR /app

# Copy all project files into container
COPY . /app

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install required Python packages
RUN pip install --no-cache-dir \
    python-telegram-bot==13.15 \
    google-api-python-client==2.89.0 \
    google-auth==2.21.0 \
    google-auth-httplib2==0.1.0 \
    google-auth-oauthlib==1.0.0 \
    Pillow \
    six \
    "urllib3<1.27"
    telethon

# Set environment variables (replace with your actual secrets in Render dashboard)
ENV TELEGRAM_TOKEN="YOUR_BOT_TOKEN"
ENV CREDENTIALS_FILE="credentials.json"
ENV FOLDER_ID="YOUR_DRIVE_FOLDER_ID"

# Expose a port (if needed, optional)
EXPOSE 8080

# Run the bot
CMD ["python", "app.py"]