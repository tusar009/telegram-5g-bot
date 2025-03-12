const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

const client = new Client({
    authStrategy: new LocalAuth()
});

client.on('qr', qr => {
    console.log('Scan this QR Code with WhatsApp to connect:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Bot is ready!');
});

// Function to send messages
function sendMessage(chatId, message) {
    client.sendMessage(chatId, message);
}

// Listen for messages from WhatsApp group
client.on('message', message => {
    console.log(`📩 Received from WhatsApp: ${message.body}`);
    console.log(`📌 Message from: ${message.from}`);

    // Check if the message is from a group
    if (message.from.endsWith("@g.us")) {
        console.log(`✅ This message is from a WhatsApp group.`);
    } else {
        console.log(`❌ This message is from a private chat, not a group.`);
    }
});

client.initialize();

// Export functions for Python script
module.exports = { sendMessage };