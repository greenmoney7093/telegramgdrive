# Use Python 3.12 slim image
FROM python:3.12-slim


# Install ntp for time sync
RUN apt-get update && \
    apt-get install -y ntp && \
    apt-get clean

# Enable NTP
RUN systemctl enable ntp || true
RUN systemctl start ntp || true

# Set timezone to UTC
RUN ln -sf /usr/share/zoneinfo/UTC /etc/localtime

# Copy your bot code
WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start bot
CMD ["python", "app.py"]

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

# Set environment variables (replace with your actual secrets in Render dashboard)
ENV TELEGRAM_TOKEN="YOUR_BOT_TOKEN"
ENV CREDENTIALS_FILE="credentials.json"
ENV FOLDER_ID="YOUR_DRIVE_FOLDER_ID"

# Expose a port (if needed, optional)
EXPOSE 8080

# Run the bot
CMD ["python", "app.py"]