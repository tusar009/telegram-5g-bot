import subprocess
import threading
import json

class WhatsAppBot:
    def __init__(self):
        self.process = None
        self.message_callback = None

    def connect(self):
        """Start the WhatsApp bot process"""
        self.process = subprocess.Popen(
            ["node", "whatsapp_web.js"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        threading.Thread(target=self._listen_for_messages, daemon=True).start()
        print("✅ WhatsApp bot started successfully!")

    def _listen_for_messages(self):
        """Continuously listen for messages from WhatsApp"""
        while self.process and self.process.stdout:
            message = self.process.stdout.readline().strip()
            if message and self.message_callback:
                self.message_callback(message)

    def on_message(self, callback):
        """Register a callback function to handle received messages"""
        self.message_callback = callback

    def send_message(self, chat_id, message):
        """Send a message to WhatsApp"""
        print(f"📤 Sending message to WhatsApp group {chat_id}: {message}")
        try:
            command = json.dumps({"chat_id": chat_id, "message": message}) + "\n"
            self.process.stdin.write(command)
            self.process.stdin.flush()
        except Exception as e:
            print(f"❌ Error sending message: {e}")