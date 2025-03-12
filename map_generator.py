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
from whatsapp_web import WhatsAppBot

nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WHATSAPP_GROUP_ID = "120363392877482908@g.us"

if not TELEGRAM_BOT_TOKEN:
    print("❌ ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343}

# Load WhatsApp bot
whatsapp_bot = WhatsAppBot()
whatsapp_bot.connect()

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

async def process_location(lat, lon, send_response):
    print(f"🔍 Processing location: {lat}, {lon}")
    await send_response(f"🔍 Searching for the nearest 5G Tower near 📍 {lat}, {lon}...")
    
    nearest_tower, distance = find_nearest_tower(lat, lon)
    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = " (Air-Fiber Feasible)" if distance_meters < 500 else " (Air-Fiber Not Feasible)"
    
    response_text = (
        f"📡 *5G Tower Locator Bot*\n"
        f"📍 Your Location: {lat}, {lon}\n"
        f"🏗 Tower Location: {nearest_tower['latitude']}, {nearest_tower['longitude']}\n"
        f"📏 Distance: {distance_display}{feasibility_text}"
    )
    
    print(f"📤 Sending response: {response_text}")
    await send_response(response_text)

async def handle_telegram_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    if user_id not in ALLOWED_GROUP_ID:
        return
    
    message_text = update.message.text
    await process_location(*map(float, message_text.split(",")), update.message.reply_text)

async def forward_whatsapp_message(message):
    """Handles WhatsApp messages and processes location data"""
    print(f"📩 Received WhatsApp message: {message}")
    try:
        lat, lon = map(float, message.split(","))
        await process_location(lat, lon, lambda response: send_whatsapp_message(response))
    except ValueError:
        print("❌ Invalid format, message ignored.")

def send_whatsapp_message(response):
    print(f"📤 Sending message to WhatsApp: {response}")
    whatsapp_bot.send_message(WHATSAPP_GROUP_ID, response)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "📡 *5G Tower Locator Bot*\nSend your location or type coordinates as: `latitude,longitude` (e.g., `12.345,67.890`)."
    )

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION | filters.Regex(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$'), handle_telegram_message))
    
    # Link WhatsApp message handling
    whatsapp_bot.on_message(lambda msg: asyncio.create_task(forward_whatsapp_message(msg)))
    
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())