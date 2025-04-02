import os
import asyncio
import re
import requests
import openrouteservice
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from geopy.distance import geodesic
import nest_asyncio
from docx import Document  # Import for handling .docx files

nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ORS_API_KEY = os.getenv("ORS_API_KEY")  # OpenRouteService API key

if not TELEGRAM_BOT_TOKEN:
    print("\u274c ERROR: Telegram bot token not found.")
    exit()

ors_client = openrouteservice.Client(key=ORS_API_KEY) if ORS_API_KEY else None

# Define group IDs
DETAILED_GROUP_ID = -1002341717383
SUMMARY_GROUP_ID = [-1002448933343, -1002506198358, -1002693800859]  # Use a list

# Load 5G Tower data from DOCX
def load_tower_data_from_docx(docx_path):
    if not os.path.exists(docx_path):
        print(f"❌ ERROR: {docx_path} not found.")
        return []
    
    towers = []
    doc = Document(docx_path)
    
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
    with open(txt_path, "r", encoding="utf-8") as file:
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

# Get road distance for FTTH using OpenRouteService
def get_road_distance(origin, destination):
    if not ors_client:
        print("❌ ERROR: OpenRouteService API key not found.")
        return float('inf')
    
    try:
        route = ors_client.directions(
            coordinates=[origin, destination],
            profile='foot-walking',  # FTTH follows electricity poles along roads
            format='geojson'
        )
        return route['features'][0]['properties']['segments'][0]['distance'] / 1000  # Convert meters to km
    except Exception as e:
        print(f"❌ Error getting road distance: {e}")
        return float('inf')

# Find nearest tower function
def find_nearest_tower(user_lat, user_lon, tower_list, use_road_distance=False):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_list:
        if use_road_distance:
            distance = get_road_distance((user_lon, user_lat), (tower['longitude'], tower['latitude']))
        else:
            distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

# Handle messages async
def extract_coordinates(text):
    if re.match(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$', text):  # Latitude,Longitude format
        return map(float, text.split(","))
    return None

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name
    group_id = update.message.chat.id

    lat, lon = None, None

    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        coords = extract_coordinates(update.message.text.strip())
        if coords:
            lat, lon = coords

    if lat is None or lon is None:
        return  # Ignore messages without valid coordinates

    # Air-Fiber: Geodesic distance (straight line)
    nearest_5g_tower, distance_5g = find_nearest_tower(lat, lon, tower_data)

    # FTTH: Road distance (following electricity poles)
    nearest_ftth_tower, distance_ftth = find_nearest_tower(lat, lon, ftth_tower_data, use_road_distance=True)

    distance_5g_display = f"{distance_5g * 1000:.0f} m" if distance_5g < 1 else f"{distance_5g:.2f} km"
    distance_ftth_display = f"{distance_ftth * 1000:.0f} m" if distance_ftth < 1 else f"{distance_ftth:.2f} km"

    af_feasibility = "\u2705 *Air-Fiber Feasible!*" if distance_5g * 1000 < 500 else "\u274c *Air-Fiber Not Feasible!*"
    ftth_feasibility = "\u2705 *FTTH Feasible!*" if distance_ftth * 1000 < 150 else "\u274c *FTTH Not Feasible!*"

    if group_id == DETAILED_GROUP_ID:
        message = (
            f"\U0001F50D Hi {user_name}, Aatreyee received your request.\n"
            f"\U0001F4CD Location: `{lat}, {lon}`\n\n"
            f"\U0001F4CF *Distance from Airtel 5G Tower*: {distance_5g_display}\n"
            f"{af_feasibility}\n\n"
            f"\U0001F4CF *Distance from FTTH Box (by road)*: {distance_ftth_display}\n"
            f"{ftth_feasibility}\n\n"
            f"⚡ *Note:* Feasibility is calculated within **500 meters** for Air-Fiber and **150 meters** for FTTH."
        )
    elif group_id in SUMMARY_GROUP_ID:
        message = (
            f"\U0001F50D Hi {user_name}, Aatreyee received your request.\n"
            f"\U0001F4CD Location: `{lat}, {lon}`\n\n"
            f"\U0001F4CF *Distance from Airtel 5G Tower*: {distance_5g_display}\n"
            f"{af_feasibility}\n\n"
            f"⚡ *Note:* Feasibility is calculated within **500 meters** of a tower."
        )
    else:
        return
    
    await update.message.reply_text(message)

# Run bot
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.LOCATION | filters.TEXT, handle_message))
    print("\u2705 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
