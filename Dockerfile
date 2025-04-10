# Use Python base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    xvfb \
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directories and set permissions
RUN mkdir -p /app/.wdm /app/.cache \
    && chmod 777 /app/.wdm /app/.cache

# Create a non-root user
RUN useradd -m -d /app appuser \
    && chown -R appuser:appuser /app \
    && usermod -aG audio,video appuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
ENV WDM_LOG_LEVEL=0
ENV WDM_LOCAL=1
ENV DEPLOYED=true

# Create a startup script
USER root
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &\nsleep 1\nexec python app.py' > /app/start.sh \
    && chmod +x /app/start.sh \
    && chown appuser:appuser /app/start.sh
USER appuser

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/start.sh"] 