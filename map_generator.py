import os
import folium
import time
from geopy.distance import geodesic
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from docx import Document

# Setup Chromium WebDriver
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1200x800")

# Use Chromium path in Railway
CHROMIUM_PATH = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/chromium-browser")
options.binary_location = CHROMIUM_PATH

# Setup WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Allowed Telegram Group ID
ALLOWED_GROUP_ID = -4767087972  # Replace with actual group ID

# Function to Load Tower Data from Word Document
def load_tower_data_from_docx(docx_path):
    doc = Document(docx_path)
    towers = []
    for para in doc.paragraphs:
        if para.text.startswith("Name:"):
            parts = para.text.split(", ")
            try:
                name = parts[0].split(": ")[1]
                lat = float(parts[1].split(": ")[1])
                lon = float(parts[2].split(": ")[1])
                towers.append({'name': name, 'latitude': lat, 'longitude': lon})
            except (IndexError, ValueError):
                continue  # Skip invalid entries
    return towers

# Load Tower Data
tower_data = load_tower_data_from_docx("5G_Tower_Details.docx")

# Find Nearest Tower
def find_nearest_tower(user_lat, user_lon):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_data:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

# Generate Map & Capture Screenshot
def generate_map_and_capture(user_lat, user_lon):
    nearest_tower, distance = find_nearest_tower(user_lat, user_lon)
    zoom_level = 18 if distance < 1 else 12

    m = folium.Map(location=[user_lat, user_lon], zoom_start=zoom_level,
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                   attr="Esri Satellite")
    
    # Add User Location Marker
    folium.Marker([user_lat, user_lon], tooltip=f'User: {user_lat}, {user_lon}', icon=folium.Icon(color="blue")).add_to(m)
    
    if nearest_tower:
        folium.Marker([nearest_tower['latitude'], nearest_tower['longitude']],
                      tooltip=f"Nearest Tower: {nearest_tower['name']}", 
                      icon=folium.Icon(color="red")).add_to(m)
        folium.PolyLine([(user_lat, user_lon), (nearest_tower['latitude'], nearest_tower['longitude'])],
                        color='black', weight=2).add_to(m)
        folium.Circle([nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=500, color='green', fill=True, fill_opacity=0.3).add_to(m)
        folium.Circle([nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=1000, color='yellow', fill=True, fill_opacity=0.3).add_to(m)
    
    save_path = "lat_long_details/"
    os.makedirs(save_path, exist_ok=True)
    map_file = os.path.join(save_path, "map.html")
    screenshot_path = os.path.join(save_path, "map_screenshot.png")
    
    m.save(map_file)
    driver.get(f"file:///{os.path.abspath(map_file)}")
    time.sleep(5)
    driver.save_screenshot(screenshot_path)
    
    return nearest_tower, distance, screenshot_path if os.path.exists(screenshot_path) else None

# Telegram Bot Message Handler
async def handle_message(update: Update, context: CallbackContext):
    if update.message.chat.id != ALLOWED_GROUP_ID:
        await update.message.reply_text("You can't access this bot. Contact the owner.")
        return
    
    try:
        lat, lon = map(float, update.message.text.split(","))
    except ValueError:
        await update.message.reply_text("Send your location or enter lat,long to find nearby towers.")
        return
    
    await update.message.reply_text(f"Processing... Lat: {lat}, Lon: {lon}.")
    nearest_tower, distance, screenshot_path = generate_map_and_capture(lat, lon)
    
    response = f"Nearest Tower: {nearest_tower['name']}\nDistance: {distance:.2f} km" if nearest_tower else "No nearby towers found."
    await update.message.reply_text(response)
    
    if screenshot_path:
        with open(screenshot_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="Green = 5G, Yellow = 4G")

# Bot Main Function
def main():
    TOKEN = os.getenv("8198412536:AAF_48dVWZWAi58O7NEBC9GX_n8M52TzhwE", "your-telegram-bot-token")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.LOCATION, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
