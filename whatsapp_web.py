import subprocess
import shutil
import json

class WhatsAppBot:
    def __init__(self):
        self.process = None

    def connect(self):
        if not shutil.which("node"):
            print("❌ ERROR: Node.js is not installed or not found.")
            return

        self.process = subprocess.Popen(
            ["node", "whatsapp_web.js"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ WhatsApp bot started successfully!")

    def send_message(self, chat_id, message):
        """Send a message to WhatsApp"""
        print(f"📤 Sending message to WhatsApp group {chat_id}: {message}")
        command = json.dumps({"chat_id": chat_id, "message": message})

        try:
            subprocess.run(["node", "whatsapp_web.js", command], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error sending message to WhatsApp: {e}")