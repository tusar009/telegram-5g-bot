import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
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
    print("\u274c ERROR: Telegram bot token not found.")
    exit()

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247, -1002448933343}

def load_tower_data_from_docx(docx_path):
    if not os.path.exists(docx_path):
        print(f"\u274c ERROR: {docx_path} not found.")
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

    print(f"\u2705 Loaded {len(towers)} towers from {docx_path}")
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

async def generate_map_and_capture(user_lat, user_lon):
    nearest_tower, distance = find_nearest_tower(user_lat, user_lon)
    zoom_level = 18 if distance < 1 else 12

    m = folium.Map(
        location=[user_lat, user_lon],
        zoom_start=zoom_level,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri Satellite"
    )

    folium.Marker([user_lat, user_lon], tooltip=f'Your Location: {user_lat}, {user_lon}').add_to(m)

    if nearest_tower:
        folium.Marker([nearest_tower['latitude'], nearest_tower['longitude']],
                      tooltip=f"Tower Location: {nearest_tower['latitude']}, {nearest_tower['longitude']}").add_to(m)
        folium.PolyLine([(user_lat, user_lon), (nearest_tower['latitude'], nearest_tower['longitude'])],
                        color='black', weight=2).add_to(m)
        
        distance_meters = distance * 1000
        feasibility_text = "Air-Fiber Feasible" if distance_meters < 500 else "Air-Fiber Not Feasible"
        feasibility_color = "yellow" if distance_meters < 500 else "red"
        
        folium.Circle([nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=500, color=feasibility_color, fill=True, fill_opacity=0.3).add_to(m)
        
    save_path = "lat_long_details"
    os.makedirs(save_path, exist_ok=True)
    screenshot_path = os.path.join(save_path, "map_screenshot.png")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"file:///{os.path.abspath('lat_long_details/map.html')}", wait_until="networkidle")
            await asyncio.sleep(2)
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
    except Exception as e:
        print(f"\u274c Screenshot failed: {e}")
        return nearest_tower, distance, None

    return nearest_tower, distance, screenshot_path if os.path.exists(screenshot_path) else None

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name or "User"

    if user_id not in ALLOWED_GROUP_ID:
        return
    
    if update.message.text and update.message.text == "/start":
        await update.message.reply_text(
            "\ud83d\udcf1 *5G Tower Locator Bot*\n"
            "Send your location or type coordinates as: `latitude,longitude` (e.g., `12.345,67.890`)."
        )
        return
    
    try:
        lat, lon = map(float, update.message.text.split(","))
    except (ValueError, AttributeError):
        if update.message.location:
            lat, lon = update.message.location.latitude, update.message.location.longitude
        else:
            return  # Ignore any other messages
    
    await update.message.reply_text(
        f"\ud83d\udd0d Hi {user_name}, as per your shared \ud83d\udccd Lat: {lat}, Lon: {lon},\n"
        "We found a nearby Airtel 5G Tower for you. Please wait for details..."
    )
    
    nearest_tower, distance, screenshot_path = await generate_map_and_capture(lat, lon)
    distance_meters = distance * 1000
    feasibility_text = " (Air-Fiber Feasible)" if distance_meters < 500 else " (Air-Fiber Not Feasible)"
    
    message_text = (
        f"\ud83d\udcf1 *5G Tower Locator Bot* This Bot Only Feasibility Calculate 500 Meter From Tower.\n"
        f"\ud83d\udccd {user_name} Location: {lat}, {lon}\n"
        f"\ud83c\udfed Airtel 5G Tower Location: {nearest_tower['latitude']}, {nearest_tower['longitude']}\n"
        f"\ud83d\udccb Distance: {distance_meters:.0f} m{feasibility_text}"
    )
    
    if screenshot_path:
        with open(screenshot_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=message_text)
    else:
        await update.message.reply_text(message_text)

async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.LOCATION, handle_message))
    print("\u2705 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())