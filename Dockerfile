FROM python:3.11

# Install dependencies
RUN apt-get update && apt-get install -y wget unzip

# Install Google Chrome
RUN wget -O /usr/bin/google-chrome "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" \
    && chmod +x /usr/bin/google-chrome

# Install ChromeDriver
RUN wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Run the bot
CMD ["python", "map_generator.py"]