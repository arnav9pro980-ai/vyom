const mineflayer = require('mineflayer');

const CONFIG = {
    host: 'PectSMP.aternos.me',
    port: 62957,
    username: 'botiee',
    auth: 'offline',
    version: '1.21.11',
    hideErrors: false,
    // Add this to skip/refuse resource packs automatically
    skipValidation: true
};

const bot = mineflayer.createBot(CONFIG);

// Alternatively, handle the resource pack event to decline/ignore it explicitly
bot.on('resourcePack', (url, hash) => {
    console.log('[BOT] Server requested a resource pack, denying/ignoring.');
    // If the server requires a response, you can decline it (depending on mineflayer version support):
    // bot.denyResourcePack();
});

bot.on('spawn', () => {
    console.log('[BOT] Successfully joined the server without downloading resource packs!');
    bot.chat('Hello everyone, I have joined the server!');
});

bot.on('error', (err) => {
    console.log('[BOT] Error:', err);
});

bot.on('kicked', (reason) => {
    console.log('[BOT] Kicked from server:', reason);
});
