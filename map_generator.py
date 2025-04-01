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
    from docx import Document
    if not os.path.exists(docx_path):
        print(f"❌ ERROR: {docx_path} not found.")
        return []
    
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
    with open(txt_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.search(r'Latitude:\s*(-?\d+\.\d+),\s*Longitude:\s*(-?\d+\.\d+)', line)
            if match:
                lat, lon = float(match.group(1)), float(match.group(2))
                towers.append({'latitude': lat, 'longitude': lon})
    
    print(f"✅ Loaded {len(towers)} towers from {txt_path}")
    return towers

# Load tower data
tower_data = load_tower_data_from_docx("5G_Tower_Details.docx")
ftth_tower_data = load_tower_data_from_txt("FTTH_Tower_Details.txt")

# Find nearest tower function
def find_nearest_tower(user_lat, user_lon, tower_list):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_list:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

# Handle messages (Live Location, Coordinates, Google Maps Links)
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name

    if user_id not in ALLOWED_GROUP_ID:
        return

    lat, lon = None, None
    text = update.message.text.strip()

    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    elif re.match(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$', text):  # Latitude,Longitude format
        lat, lon = map(float, text.split(","))
    
    if lat is None or lon is None:
        return  # Ignore messages that don't contain valid coordinates

    # Find nearest towers
    nearest_5g_tower, distance_5g = find_nearest_tower(lat, lon, tower_data)
    nearest_ftth_tower, distance_ftth = find_nearest_tower(lat, lon, ftth_tower_data)

    # Convert distances to meters
    distance_5g_meters = distance_5g * 1000 if distance_5g != float('inf') else float('inf')
    distance_ftth_meters = distance_ftth * 1000 if distance_ftth != float('inf') else float('inf')

    # Feasibility determination
    af_feasibility = "✅ *Air-Fiber Feasible!*" if distance_5g_meters < 500 else "❌ *Air-Fiber Not Feasible!*"
    ftth_feasibility = "✅ *FTTH Feasible!*" if distance_ftth_meters < 150 else "❌ *FTTH Not Feasible!*"

    distance_5g_display = f"{distance_5g_meters:.0f} m" if distance_5g_meters < 1000 else f"{distance_5g:.2f} km"
    distance_ftth_display = f"{distance_ftth_meters:.0f} m" if distance_ftth_meters < 1000 else f"{distance_ftth:.2f} km"

    await update.message.reply_text(
        f"🔍 Hi {user_name}, Aatreyee received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n\n"
        f"📏 *Distance from Airtel 5G Tower*: {distance_5g_display} ({nearest_5g_tower if nearest_5g_tower else 'None'})\n"
        f"{af_feasibility}\n\n"
        f"📏 *Distance from FTTH Box*: {distance_ftth_display} ({nearest_ftth_tower if nearest_ftth_tower else 'None'})\n"
        f"{ftth_feasibility}\n\n"
        f"⚡ *Note:* Feasibility is calculated within **500 meters** for Air-Fiber and **150 meters** for FTTH."
    )

# Run bot
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
