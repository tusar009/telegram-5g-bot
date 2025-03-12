# Use a lightweight official Python image
FROM python:3.11-slim

# Install Node.js and npm
RUN apt update && apt install -y curl && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt install -y nodejs

# Set working directory inside the container
WORKDIR /app

# Copy project files to the container
COPY . .  

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install WhatsApp dependencies
RUN npm install whatsapp-web.js qrcode-terminal

# Ensure script has execution permission
RUN chmod +x /app/map_generator.py

# Set default command to run the bot
CMD ["python3", "/app/map_generator.py"]