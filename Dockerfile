FROM python:3.11

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip curl && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright with dependencies
RUN playwright install --with-deps

# Run the bot
CMD ["python", "map_generator.py"]