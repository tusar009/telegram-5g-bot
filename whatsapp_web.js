const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', qr => {
    console.log('Scan this QR Code with WhatsApp to connect:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Bot is ready!');
});

client.on('message', async message => {
    console.log(`📩 Received from WhatsApp: ${message.body}`);
    console.log(`📌 Message from: ${message.from}`);

    if (message.from.endsWith('@g.us')) {  // Ensure group messages are handled
        console.log("✅ Message is from a WhatsApp group, processing...");
        process.stdout.write(message.body + "\n"); // Send message to Python script
    }
});

// Function to send messages from Python
process.stdin.on('data', async (data) => {
    try {
        const { chat_id, message } = JSON.parse(data.toString().trim());
        console.log(`📤 Sending message to WhatsApp group: ${chat_id}`);
        await client.sendMessage(chat_id, message);
        console.log("✅ Message sent successfully!");
    } catch (error) {
        console.error("❌ Error sending message:", error);
    }
});

client.initialize();