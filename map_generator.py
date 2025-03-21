import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from geopy.distance import geodesic
import folium
from docx import Document
from playwright.async_api import async_playwright
import nest_asyncio

nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("❌ ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343, -1002506198358}

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

def find_nearest_tower(user_lat, user_lon):
    min_distance = float('inf')
    nearest_tower = None
    for tower in tower_data:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower
    return nearest_tower, min_distance

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name  # Get user name

    if user_id not in ALLOWED_GROUP_ID:
        return
    
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        try:
            lat, lon = map(float, update.message.text.split(","))
        except (ValueError, AttributeError):
            return  # Ignore non-location text messages

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

async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"👋 Hello {user_name}, welcome to the 📡 *5G Tower Locator Bot*!\n"
        "To check feasibility, send your **live location** or type coordinates as:\n"
        "📍 `latitude,longitude` (e.g., `12.345,67.890`)."
    )

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION | filters.Regex(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$'), handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())