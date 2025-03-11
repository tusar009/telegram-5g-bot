FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y wget unzip curl xvfb libnss3 libatk1.0-0 libcups2 libxkbcommon-x11-0 && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy only necessary files
COPY map_generator.py /app/map_generator.py
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Ensure script has execution permission
RUN chmod +x /app/map_generator.py

# Run the bot
CMD ["python3", "/app/map_generator.py"]