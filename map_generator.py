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

ALLOWED_GROUP_ID = {-1002341717383, -4767087972, -4667699247}

# Load Tower Data from DOCX
def load_tower_data_from_docx(docx_path):
    if not os.path.exists(docx_path):
        print(f"❌ ERROR: {docx_path} not found.")
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

    print(f"✅ Loaded {len(towers)} towers from {docx_path}")
    return towers

tower_data = load_tower_data_from_docx("5G_Tower_Details.docx")

# Find Nearest Tower
def find_nearest_tower(user_lat, user_lon):
    min_distance = float('inf')
    nearest_tower = None
    
    for tower in tower_data:
        distance = geodesic((user_lat, user_lon), (tower['latitude'], tower['longitude'])).kilometers
        if distance < min_distance:
            min_distance = distance
            nearest_tower = tower

    return nearest_tower, min_distance

# Generate Map & Capture Screenshot
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
        feasibility_text = "Air-Fiber Feasible" if distance_meters < 500 else "Not Feasible"
        feasibility_color = "yellow" if distance_meters < 500 else "red"
        
        folium.Circle([nearest_tower['latitude'], nearest_tower['longitude']],
                      radius=500, color=feasibility_color, fill=True, fill_opacity=0.3).add_to(m)
        
        mid_lat = (user_lat + nearest_tower['latitude']) / 2
        mid_lon = (user_lon + nearest_tower['longitude']) / 2

        folium.Marker([mid_lat, mid_lon - 0.0008],
                      icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: {feasibility_color};">{feasibility_text}</div>')).add_to(m)
        
        distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
        
        folium.Marker([mid_lat, mid_lon + 0.0008],
                      icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: cyan;">📏 {distance_display}</div>')).add_to(m)
    
    save_path = "lat_long_details"
    os.makedirs(save_path, exist_ok=True)
    map_file = os.path.join(save_path, "map.html")
    screenshot_path = os.path.join(save_path, "map_screenshot.png")

    m.save(map_file)
    print(f"✅ Map saved successfully at {os.path.abspath(map_file)}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"file:///{os.path.abspath(map_file)}", wait_until="networkidle")
            await asyncio.sleep(2)  # Shorter wait time
            print(f"📸 Capturing screenshot at {screenshot_path}")
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()
            print(f"✅ Screenshot saved at {screenshot_path}")
    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return nearest_tower, distance, None

    return nearest_tower, distance, screenshot_path if os.path.exists(screenshot_path) else None

# Telegram Bot Message Handler
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.chat.id

    if user_id not in ALLOWED_GROUP_ID:
        await update.message.reply_text("🚫 You are not authorized to use this bot.")
        return
    
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        try:
            lat, lon = map(float, update.message.text.split(","))
        except (ValueError, AttributeError):
            await update.message.reply_text(
                "📡 *5G Tower Locator Bot*\n"
                "Send your location or type coordinates as: `latitude,longitude` (e.g., `12.345,67.890`)."
            )
            return
    
    await update.message.reply_text(f"🔍 Processing request... 📍 Lat: {lat}, Lon: {lon}. Please wait...")

    nearest_tower, distance, screenshot_path = await generate_map_and_capture(lat, lon)

    distance_meters = distance * 1000
    distance_display = f"{distance_meters:.0f} m" if distance_meters < 1000 else f"{distance:.2f} km"
    feasibility_text = " (Air-Fiber Feasible)" if distance_meters < 500 else ""

    if screenshot_path:
        with open(screenshot_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=f"📏 Distance: {distance_display}{feasibility_text}")
    else:
        await update.message.reply_text(
            f"📍 Your Location: {lat}, {lon}\n"
            f"🏗 Tower Location: {nearest_tower['latitude']}, {nearest_tower['longitude']}\n"
            f"📏 Distance: {distance_display}{feasibility_text}"
        )

# Bot Main Function
async def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.LOCATION, handle_message))
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())