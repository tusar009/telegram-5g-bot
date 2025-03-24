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

# Load 5G Tower data from DOCX
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

# Find nearest tower
def find_nearest_tower(user_lat, user_lon):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_data:
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

    # Match both @lat,lon and ?q=lat,lon formats
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
        elif "google.com/maps" in text or "maps.app.goo.gl" in text:  # Google Maps link
            coords = extract_coordinates_from_google_maps(text)
            if coords:
                lat, lon = coords

    if lat is None or lon is None:
        return  # Ignore messages that don't contain valid coordinates

    await update.message.reply_text(
        f"\U0001F50D Hi {user_name}, I have received your request.\n"
        f"\U0001F4CD Location: `{lat}, {lon}`\n"
        f"⏳ Please wait while Aatreyee processes your request..."
    )
    nearest_tower, distance = find_nearest_tower(lat, lon)
    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = "✅ *Air-Fiber Feasible!*" if distance_meters < 500 else "❌ *Air-Fiber Not Feasible!*"

    await update.message.reply_text(
        f"\U0001F4E1 *Aatreyee Tower Locator Bot* \U0001F30D\n"
        f"✅ *User Location*: `{lat}, {lon}`\n"
        f"\U0001F3D7 *Nearest Airtel 5G Tower Location*: `{nearest_tower['latitude']}, {nearest_tower['longitude']}`\n"
        f"\U0001F4CF *Distance*: {distance_display}\n"
        f"{feasibility_text}\n\n"
        f"⚡ *Note:* As per policy, the bot calculates feasibility within **500 meters** of a tower."
    )

# Start command
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"\U0001F44B Hello {user_name}, welcome to the \U0001F4E1 *Aatreyee Tower Locator Bot*!\n"
        "To check feasibility, send your **live location** or type coordinates as:\n"
        "📍 `latitude,longitude` (e.g., `12.345,67.890`).\n"
    )

# Run bot
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION | filters.Regex(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$') | filters.Regex(r'https://maps\.app\.goo\.gl/.*') | filters.Regex(r'https://www\.google\.com/maps/.*'), handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
