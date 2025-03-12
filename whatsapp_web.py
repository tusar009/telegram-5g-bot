import subprocess
import json
import threading

class WhatsAppBot:
    def __init__(self):
        self.process = None

    def connect(self):
        self.process = subprocess.Popen(["node", "whatsapp_web.js"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send_message(self, chat_id, message):
        command = json.dumps({"chat_id": chat_id, "message": message})
        subprocess.run(["node", "whatsapp_web.js", command])

    def on_message(self, callback):
        def listen():
            while True:
                output = self.process.stdout.readline()
                if output:
                    try:
                        message = json.loads(output.decode("utf-8"))
                        callback(message)
                    except json.JSONDecodeError:
                        pass
        
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()