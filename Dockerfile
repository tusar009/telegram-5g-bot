FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl xvfb \
    libnss3 libatk1.0-0 libcups2 libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright with dependencies
RUN playwright install --with-deps chromium

# Ensure script has execution permission
RUN chmod +x /app/map_generator.py

# Run the bot
CMD ["python", "/app/map_generator.py"]