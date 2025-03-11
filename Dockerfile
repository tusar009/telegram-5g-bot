FROM python:3.11

# Set working directory
WORKDIR /app

# Copy all project files (ensure the destination is a directory)
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install Playwright with dependencies
RUN playwright install --with-deps chromium

# Ensure script has execution permission
RUN chmod +x /app/map_generator.py

# Run the bot
CMD ["python", "/app/map_generator.py"]