import os
import asyncio
import re
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from geopy.distance import geodesic
import nest_asyncio

nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("\u274c ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343, -1002506198358, -1002693800859}

# Load 5G Tower data from DOCX
def load_tower_data_from_docx(docx_path):
    if not os.path.exists(docx_path):
        print(f"❌ ERROR: {docx_path} not found.")
        return []
    
    from docx import Document
    doc = Document(docx_path)
    towers = []
    for para in doc.paragraphs:
        match = re.search(r'Latitude:\s*(-?\d+\.\d+),\s*Longitude:\s*(-?\d+\.\d+)', para.text)
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            towers.append({'latitude': lat, 'longitude': lon})
    
    print(f"✅ Loaded {len(towers)} towers from {docx_path}")
    return towers

# Load FTTH Tower data from TXT
def load_tower_data_from_txt(txt_path):
    if not os.path.exists(txt_path):
        print(f"❌ ERROR: {txt_path} not found.")
        return []
    
    towers = []
    with open(txt_path, "r") as file:
        for line in file:
            match = re.search(r'Latitude:\s*(-?\d+\.\d+),\s*Longitude:\s*(-?\d+\.\d+)', line)
            if match:
                lat, lon = float(match.group(1)), float(match.group(2))
                towers.append({'latitude': lat, 'longitude': lon})
    
    print(f"✅ Loaded {len(towers)} FTTH towers from {txt_path}")
    return towers

# Load tower data
tower_data = load_tower_data_from_docx("5G_Tower_Details.docx")
ftth_tower_data = load_tower_data_from_txt("FTTH_Tower_Details.txt")

def find_nearest_tower(user_lat, user_lon, tower_list):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_list:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

def expand_google_maps_short_link(short_url):
    try:
        response = requests.head(short_url, allow_redirects=True)
        return response.url  # Get the final expanded URL
    except requests.RequestException:
        return None

def extract_coordinates_from_google_maps(url):
    expanded_url = expand_google_maps_short_link(url) if "maps.app.goo.gl" in url else url
    if not expanded_url:
        return None
    match = re.search(r'[@](-?\d+\.\d+),(-?\d+\.\d+)|[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)', expanded_url)
    if match:
        lat, lon = match.group(1) or match.group(3), match.group(2) or match.group(4)
        return float(lat), float(lon)
    return None

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name

    if user_id not in ALLOWED_GROUP_ID:
        return

    lat, lon = None, None
    
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        print(f"Live Location Received: {lat}, {lon}")  # Debugging log
    else:
        text = update.message.text.strip()
        if re.match(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$', text):
            lat, lon = map(float, text.split(","))
        elif re.search(r'(?:google\.com/maps|maps\.app\.goo\.gl)', text):
            coords = extract_coordinates_from_google_maps(text)
            if coords:
                lat, lon = coords
    
    if lat is None or lon is None:
        return

    nearest_5g_tower, distance_5g = find_nearest_tower(lat, lon, tower_data)
    nearest_ftth_tower, distance_ftth = find_nearest_tower(lat, lon, ftth_tower_data)

    distance_5g_meters = distance_5g * 1000 if distance_5g != float('inf') else float('inf')
    distance_ftth_meters = distance_ftth * 1000 if distance_ftth != float('inf') else float('inf')

    af_feasibility = "✅ *Air-Fiber Feasible!*" if distance_5g_meters < 500 else "❌ *Air-Fiber Not Feasible!*"
    ftth_feasibility = "✅ *FTTH Feasible!*" if distance_ftth_meters < 150 else "❌ *FTTH Not Feasible!*"

    distance_5g_display = f"{distance_5g_meters:.0f} m" if distance_5g_meters < 1000 else f"{distance_5g:.2f} km"
    distance_ftth_display = f"{distance_ftth_meters:.0f} m" if distance_ftth_meters < 1000 else f"{distance_ftth:.2f} km"

    await update.message.reply_text(
        f"🔍 Hi {user_name}, Aatreyee received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n\n"
        f"📏 *Distance from Airtel 5G Tower*: {distance_5g_display} ({nearest_5g_tower})\n"
        f"{af_feasibility}\n\n"
        f"📏 *Distance from FTTH Box*: {distance_ftth_display} ({nearest_ftth_tower})\n"
        f"{ftth_feasibility}\n\n"
        f"⚡ *Note:* Feasibility is calculated within **500 meters** for Air-Fiber and **150 meters** for FTTH."
    )

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
