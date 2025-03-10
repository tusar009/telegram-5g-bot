import os
import folium
import math
import time
from geopy.distance import geodesic
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from docx import Document

# Group ID restriction
ALLOWED_GROUP_ID = -4767087972  # Replace with your actual group ID

# Function to load tower data from Word document
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

# Load tower data
tower_data = load_tower_data_from_docx("/app/5G_Tower_Details.docx")

def find_nearest_tower(user_lat, user_lon):
    min_distance = float('inf')
    nearest_tower = None
    
    for tower in tower_data:
        tower_location = (tower['latitude'], tower['longitude'])
        user_location = (user_lat, user_lon)
        distance = geodesic(user_location, tower_location).kilometers
        
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    
    return nearest_tower, min_distance

def generate_map_and_capture(user_lat, user_lon):
    nearest_tower, distance = find_nearest_tower(user_lat, user_lon)
    zoom_level = 18 if distance < 1 else 12
    
    m = folium.Map(location=[user_lat, user_lon], zoom_start=zoom_level, 
                   tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 
                   attr="Esri Satellite")
    
    folium.Marker([user_lat, user_lon], tooltip=f'{user_lat}, {user_lon}', icon=folium.DivIcon(html=f'<div style="font-size:12px; color:blue;">{user_lat}, {user_lon}</div>')).add_to(m)
    
    if nearest_tower:
        folium.Marker([nearest_tower['latitude'], nearest_tower['longitude']],
                      tooltip=f"Nearest Tower: {nearest_tower['name']}",
                      icon=folium.DivIcon(html=f'<div style="font-size:12px; color:red;">{nearest_tower["name"]}</div>')).add_to(m)
        folium.PolyLine([(user_lat, user_lon), (nearest_tower['latitude'], nearest_tower['longitude'])],
                        color='black', weight=2, tooltip=f"Distance: {distance:.2f} km").add_to(m)
        folium.Circle(location=[nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=500,
                      color='green',
                      fill=True,
                      fill_color='green',
                      fill_opacity=0.3,
                      tooltip="500m Coverage (5G)").add_to(m)
        folium.Circle(location=[nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=1000,
                      color='yellow',
                      fill=True,
                      fill_color='yellow',
                      fill_opacity=0.3,
                      tooltip="1km Coverage (4G)").add_to(m)
    
    save_path = "C:/Users/hp/Desktop/lat long details/"
    os.makedirs(save_path, exist_ok=True)
    
    map_file = os.path.join(save_path, "map.html")
    screenshot_path = os.path.join(save_path, "map_screenshot.png")
    
    m.save(map_file)
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200x800")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(f"file:///{os.path.abspath(map_file)}")
    
    time.sleep(5)
    driver.save_screenshot(screenshot_path)
    driver.quit()
    
    if not os.path.exists(screenshot_path) or os.path.getsize(screenshot_path) == 0:
        print("Error: Screenshot was not created or is empty.")
        return nearest_tower, distance, None
    
    return nearest_tower, distance, screenshot_path

async def handle_message(update: Update, context: CallbackContext):
    if update.message.chat.id != ALLOWED_GROUP_ID:
        await update.message.reply_text("You Can't Access this Bot. Kindly Contact the Owner.")
        return
    
    if update.message.text:
        try:
            lat, lon = map(float, update.message.text.split(","))
        except ValueError:
            await update.message.reply_text("Welcome to the 5G Tower Locator Bot! Send your location or enter lat,long to find nearby towers.")
            return
    elif update.message.location:
        lat, lon = update.message.location.latitude, update.message.location.longitude
    else:
        await update.message.reply_text("Please send your location or enter latitude,longitude.")
        return
    
    await update.message.reply_text(f"Your request has been received. Lat: {lat}, Lon: {lon}. Please wait for your screenshot.")
    
    nearest_tower, distance, screenshot_path = generate_map_and_capture(lat, lon)
    if nearest_tower:
        response = f"Nearest Tower: {nearest_tower['name']}\nDistance: {distance:.2f} km"
    else:
        response = "No nearby towers found."
    
    await update.message.reply_text(response)
    
    if screenshot_path:
        try:
            with open(screenshot_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption="Screenshot taken for User. Green = 5G, Yellow = 4G")
        except Exception as e:
            print(f"Error sending image: {e}")
            await update.message.reply_text("Failed to send map image.")

def main():
    TOKEN = "8198412536:AAF_48dVWZWAi58O7NEBC9GX_n8M52TzhwE"  # Replace with your actual bot token
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.LOCATION, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
