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

# Load FTTH Tower data from TXT file (latitude, longitude only)
def load_tower_data_from_txt(txt_path):
    if not os.path.exists(txt_path):
        print(f"❌ ERROR: {txt_path} not found.")
        return []

    towers = []
    with open(txt_path, 'r') as file:
        for line in file:
            match = re.search(r'Latitude:\s*(-?\d+\.\d+),\s*Longitude:\s*(-?\d+\.\d+)', line)
            if match:
                lat, lon = float(match.group(1)), float(match.group(2))
                towers.append({'latitude': lat, 'longitude': lon})
                print(f"Loaded Tower: Latitude={lat}, Longitude={lon}")  # Debugging output
            else:
                print(f"Skipped line (no match): {line.strip()}")  # Debugging output for non-matching lines

    print(f"✅ Loaded {len(towers)} FTTH towers from {txt_path}")
    return towers

# Load FTTH tower data from file
ftth_tower_data = load_tower_data_from_txt("FTTH_Tower_Details.txt")

# Find nearest tower function with debug logs
def find_nearest_tower(user_lat, user_lon, tower_list):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_list:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
        print(f"Comparing with Tower: Latitude={tower['latitude']}, Longitude={tower['longitude']}, Distance={distance} km")  # Debugging output
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

    # Find nearest FTTH tower
    nearest_ftth_tower, distance_ftth = find_nearest_tower(lat, lon, ftth_tower_data)

    # Debugging logs
    print(f"User Location: {lat}, {lon}")
    print(f"Nearest FTTH Tower: {nearest_ftth_tower}")

    # Convert distances to meters
    distance_ftth_meters = distance_ftth * 1000 if distance_ftth != float('inf') else float('inf')

    # Debugging logs for distance
    if distance_ftth_meters == float('inf'):
        print("🚨 Error: Distance calculation returned infinity! Check FTTH tower coordinates.")

    # Feasibility determination for FTTH
    ftth_feasibility = "✅ *FTTH Feasible!*" if distance_ftth_meters < 150 else "❌ *FTTH Not Feasible!*"
    distance_ftth_display = f"{distance_ftth_meters:.0f} m" if distance_ftth_meters < 1000 else f"{distance_ftth:.2f} km"

    await update.message.reply_text(
        f"🔍 Hi {user_name}, Aatreyee received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n\n"
        f"📏 *Distance from FTTH Box*: {distance_ftth_display}\n"
        f"{ftth_feasibility}\n\n"
        f"⚡ *Note:* Feasibility is calculated within **150 meters** for FTTH."
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
    app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
