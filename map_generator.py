import os
import asyncio
import re
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from geopy.distance import geodesic
from docx import Document
import nest_asyncio

nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("\u274c ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343, -1002506198358, -1002693800859}

# Load tower data from DOCX
def load_tower_data_from_docx(docx_path):
    if not os.path.exists(docx_path):
        return []
    doc = Document(docx_path)
    towers = []
    for para in doc.paragraphs:
        if para.text.startswith("Name:"):
            parts = para.text.split(", ")
            try:
                lat = float(parts[1].split(": ")[1])
                lon = float(parts[2].split(": ")[1])
                towers.append({'latitude': lat, 'longitude': lon})
            except (IndexError, ValueError):
                continue
    return towers

tower_data = load_tower_data_from_docx("5G_Tower_Details.docx")
ftth_data = load_tower_data_from_docx("FTTH_Tower_Details.docx")

# Find nearest tower
def find_nearest_tower(user_lat, user_lon, towers):
    min_distance = float('inf')
    nearest_tower = None
    for tower in towers:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

# Expand Google Maps short links
def expand_google_maps_short_link(short_url):
    try:
        response = requests.head(short_url, allow_redirects=True)
        return response.url  # Get the final expanded URL
    except requests.RequestException:
        return None

# Extract coordinates from a Google Maps URL
def extract_coordinates_from_google_maps(url):
    expanded_url = expand_google_maps_short_link(url) if "maps.app.goo.gl" in url else url
    if not expanded_url:
        return None

    match = re.search(r'[@](-?\d+\.\d+),(-?\d+\.\d+)|[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)', expanded_url)
    if match:
        lat, lon = match.group(1) or match.group(3), match.group(2) or match.group(4)
        return float(lat), float(lon)
    
    return None

# Handle messages (Live Location, Coordinates, Google Maps Links)
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name

    if user_id not in ALLOWED_GROUP_ID:
        return

    lat, lon = None, None

    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        text = update.message.text.strip()
        if re.match(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$', text):  # Latitude,Longitude format
            lat, lon = map(float, text.split(","))
        elif re.search(r'(?:google\.com/maps|maps\.app\.goo\.gl)', text):  # Google Maps link
            coords = extract_coordinates_from_google_maps(text)
            if coords:
                lat, lon = coords

    if lat is None or lon is None:
        return  # Ignore messages that don't contain valid coordinates

    nearest_5g, distance_5g = find_nearest_tower(lat, lon, tower_data)
    distance_5g_meters = distance_5g * 1000
    feasibility_5g = "✅ *Air-Fiber Feasible!*" if distance_5g_meters < 500 else "❌ *Air-Fiber Not Feasible!*"

    nearest_ftth, distance_ftth = find_nearest_tower(lat, lon, ftth_data)
    distance_ftth_meters = distance_ftth * 1000
    feasibility_ftth = "✅ *FTTH Feasible!*" if distance_ftth_meters < 150 else "❌ *FTTH Not Feasible!*"

    await update.message.reply_text(
        f"🔍 Hi {user_name}, Aatreyee received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n\n"
        f"📏 *Distance from Airtel 5G Tower*: {distance_5g_meters:.0f} m ({distance_5g:.2f} km)\n"
        f"{feasibility_5g}\n\n"
        f"📏 *Distance from FTTH Box*: {distance_ftth_meters:.0f} m ({distance_ftth:.2f} km)\n"
        f"{feasibility_ftth}\n\n"
        f"⚡ *Note:*\n- Air-Fiber feasibility is within **500 meters**.\n- FTTH feasibility is within **150 meters**."
    )

# Start command
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"\U0001F44B Hello {user_name}, welcome to the \U0001F4E1 *Aatreyee Tower Locator Bot*!\n"
        "To check feasibility, send your **live location** or type coordinates as:\n"
        "📍 latitude,longitude (e.g., 12.345,67.890).\n"
    )

# Run bot
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION | filters.Regex(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$') | filters.Regex(r'(?:google\.com/maps|maps\.app\.goo\.gl)'), handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
