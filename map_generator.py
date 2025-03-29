import os
import asyncio
import re
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, CallbackContext
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

    if lat is None or lon is None:
        return  # Ignore messages that don't contain valid coordinates

    # Store user location for later use
    context.user_data["user_location"] = (lat, lon)

    # Buttons for user selection
    keyboard = [
        [InlineKeyboardButton("🆕 New Booking Feasibility", callback_data="new_booking")],
        [InlineKeyboardButton("📋 Old Booking Status", callback_data="old_booking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"\U0001F50D Hi {user_name}, I have received your request.\n"
        f"\U0001F4CD Location: `{lat}, {lon}`\n"
        f"⏳ Please select an option below:", reply_markup=reply_markup
    )

# Handle button clicks
async def handle_button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.message.chat.id
    user_name = query.from_user.first_name
    await query.answer()

    if user_id not in ALLOWED_GROUP_ID:
        return

    if "user_location" not in context.user_data:
        await query.message.reply_text("⚠️ Location data missing. Please resend your location.")
        return

    lat, lon = context.user_data["user_location"]
    nearest_tower, distance = find_nearest_tower(lat, lon)
    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = "✅ *Air-Fiber Feasible!*" if distance_meters < 500 else "❌ *Air-Fiber Not Feasible!*"

    response_text = (
        f"🔍 Hi {user_name}, I have received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n"
        f"⏳ Please wait while Aatreyee processes your request...\n\n"
        f"📡 *Aatreyee Tower Locator Bot* 🌍\n"
        f"✅ *User Location*: `{lat}, {lon}`\n"
        f"📏 *Distance*: {distance_display}\n"
        f"{feasibility_text}\n\n"
        f"⚡ *Note:* As per policy, the bot calculates feasibility within **500 meters** of a tower."
    )

    if query.data == "new_booking":
        await query.message.reply_text(response_text)

    elif query.data == "old_booking":
        await query.message.reply_text("📋 *Please enter the last 5 digits of your Order ID:*")
        context.user_data["waiting_for_order_id"] = True  # Flag for next input

# Handle order ID input
async def process_order_id(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name
    order_id = update.message.text.strip()

    if user_id not in ALLOWED_GROUP_ID:
        return

    if "waiting_for_order_id" not in context.user_data or not context.user_data["waiting_for_order_id"]:
        return

    if not re.match(r'^\d{5}$', order_id):  # Validate order ID format (must be 5 digits)
        await update.message.reply_text("⚠️ Invalid Order ID. Please enter the last *5 digits* of your Order ID.")
        return

    context.user_data["waiting_for_order_id"] = False  # Reset flag

    if "user_location" not in context.user_data:
        await update.message.reply_text("⚠️ Location data missing. Please resend your location.")
        return

    lat, lon = context.user_data["user_location"]
    nearest_tower, distance = find_nearest_tower(lat, lon)
    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = "✅ *Air-Fiber Feasible!*" if distance_meters < 500 else "❌ *Air-Fiber Not Feasible!*"

    response_text = (
        f"🔍 Hi {user_name}, I have received your request.\n"
        f"📍 Location: `{lat}, {lon}`\n"
        f"⏳ Please wait while Aatreyee processes your request...\n\n"
        f"📡 *Aatreyee Tower Locator Bot* 🌍\n"
        f"✅ *User Location*: `{lat}, {lon}`\n"
        f"📏 *Distance*: {distance_display}\n"
        f"{feasibility_text}\n\n"
        f"⚡ *Note:* As per policy, the bot calculates feasibility within **500 meters** of a tower."
    )

    await update.message.reply_text(response_text)

# Start command
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"\U0001F44B Hello {user_name}, welcome to the \U0001F4E1 *Aatreyee Tower Locator Bot*!\n"
        "To check feasibility, send your **live location** or type coordinates as:\n"
        "📍 `latitude,longitude` (e.g., `26.7592595,88.3074051`).\n"
    )

# Run bot
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Command("start"), start))
    app.add_handler(MessageHandler(filters.LOCATION | filters.Regex(r'^-?\d{1,3}\.\d+,-?\d{1,3}\.\d+$'), handle_message))
    app.add_handler(CallbackQueryHandler(handle_button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_order_id))
    
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
