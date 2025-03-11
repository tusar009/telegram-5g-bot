FROM python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget unzip curl xvfb \
    libnss3 libatk1.0-0 libcups2 libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .  # ✅ This ensures all files are copied properly

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright with dependencies
RUN playwright install --with-deps chromium

# Ensure script has execution permission
RUN chmod +x map_generator.py  # ✅ No need for `/app/`

# Run the bot
CMD ["python", "map_generator.py"]  # ✅ Fixed path