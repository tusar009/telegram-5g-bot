import subprocess
import shutil
import json

class WhatsAppBot:
    def __init__(self):
        self.process = None
        self.message_callback = None

    def connect(self):
        if not shutil.which("node"):
            print("❌ ERROR: Node.js is not installed or not found.")
            return

        self.process = subprocess.Popen(
            ["node", "whatsapp_web.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("✅ WhatsApp bot started successfully!")

    def send_message(self, chat_id, message):
        """Send a message to WhatsApp"""
        print(f"📤 Sending message to WhatsApp group {chat_id}: {message}")
        try:
            command = json.dumps({"chat_id": chat_id, "message": message}) + "\n"
            self.process.stdin.write(command)
            self.process.stdin.flush()
        except Exception as e:
            print(f"❌ Error sending message: {e}")