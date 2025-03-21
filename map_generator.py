import os
import asyncio
import re
import aiohttp
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
    print("❌ ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343, -1002506198358}

def extract_lat_lon_from_url(url):
    """Extract latitude and longitude from Google Maps URLs"""
    match = re.search(r'@([-]?\d+\.\d+),([-]?\d+\.\d+)', url)  # Match @lat,lon format
    if match:
        return float(match.group(1)), float(match.group(2))

    match = re.search(r'q=([-]?\d+\.\d+),([-]?\d+\.\d+)', url)  # Match q=lat,lon format
    if match:
        return float(match.group(1)), float(match.group(2))

    return None

async def get_redirected_url(url):
    """Fetch the final redirected URL from a shortened Google Maps link"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as response:
                return str(response.url)  # Get the final redirected URL
    except Exception as e:
        print(f"Error fetching redirected URL: {e}")
        return None

async def process_location(update: Update, context: CallbackContext, lat: float, lon: float):
    """Process the location and send the nearest 5G tower details"""
    user_name = update.message.from_user.first_name

    await update.message.reply_text(
        f"🔍 Hi {user_name}, I have received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n"
        f"⏳ Please wait while we process your request..."
    )

    nearest_tower, distance = find_nearest_tower(lat, lon)
    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = "✅ *Air-Fiber Feasible!*" if distance_meters < 500 else "❌ *Air-Fiber Not Feasible!*"

    await update.message.reply_text(
        f"📡 *5G Tower Locator Bot* 🌍\n"
        f"✅ *User Location*: `{lat}, {lon}`\n"
        f"🏗 *Nearest Airtel 5G Tower*: `{nearest_tower['latitude']}, {nearest_tower['longitude']}`\n"
        f"📏 *Distance*: {distance_display}\n"
        f"{feasibility_text}\n\n"
        f"⚡ *Note:* This bot calculates feasibility within **500 meters** of a tower."
    )

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    if user_id not in ALLOWED_GROUP_ID:
        return

    message_text = update.message.text.strip()

    # 📍 Case 1: User sends a Google Maps Short Link
    if "maps.app.goo.gl" in message_text:
        final_url = await get_redirected_url(message_text)
        if final_url:
            coords = extract_lat_lon_from_url(final_url)
            if coords:
                await process_location(update, context, coords[0], coords[1])
                return

    # 📍 Case 2: User sends a Google Maps Direct Link
    elif "www.google.com/maps" in message_text:
        coords = extract_lat_lon_from_url(message_text)
        if coords:
            await process_location(update, context, coords[0], coords[1])
            return

    # 📍 Case 3: User sends Manual Lat,Long (12.345,67.890)
    try:
        lat, lon = map(float, message_text.split(","))
        await process_location(update, context, lat, lon)
        return
    except (ValueError, AttributeError):
        pass

    # Ignore other messages that do not contain valid location info

async def handle_location(update: Update, context: CallbackContext):
    """Handle live location shared via Telegram"""
    user_id = update.message.chat.id
    if user_id not in ALLOWED_GROUP_ID:
        return

    lat = update.message.location.latitude
    lon = update.message.location.longitude
    await process_location(update, context, lat, lon)

async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"👋 Hello {user_name}, welcome to the 📡 *5G Tower Locator Bot*!\n\n"
        "You can send your location in three ways:\n"
        "✅ *Live Location* (shared via Telegram)\n"
        "✅ *Manual Coordinates* (`12.345,67.890`)\n"
        "✅ *Google Maps Link* (`https://maps.app.goo.gl/...` or `https://www.google.com/maps/...`)\n\n"
        "No matter how you provide your location, I will:\n"
        "🔹 Extract the coordinates 📍\n"
        "🔹 Find the nearest 5G tower 📡\n"
        "🔹 Check feasibility within 500 meters 🏗\n"
    )

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
