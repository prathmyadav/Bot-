
import os
import asyncio
import threading
import urllib.request
import re
import time
import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError

# --- Render के लिए Dummy HTTP Server ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Multi-User Restricted Saver Bot is Awake!\n")

def run_http_server():
    port = int(os.environ.get("PORT", 3000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, DummyServer)
    print(f"Web server listening on port {port}")
    
    def start_pinging():
        while True:
            try:
                bot_url = "https://bot-8x03.onrender.com" 
                urllib.request.urlopen(bot_url)
                print("[Self-Ping] Bot kept awake!")
            except Exception as e:
                print(f"[Self-Ping] Failed: {e}")
            time.sleep(300) 

    ping_thread = threading.Thread(target=start_pinging)
    ping_thread.daemon = True
    ping_thread.start()
    httpd.serve_forever()

http_thread = threading.Thread(target=run_http_server)
http_thread.daemon = True
http_thread.start()
# -------------------------------------

# 📌 Telegram API डिटेल्स
API_ID = 33427426
API_HASH = 'a4c1eb3419e497aeb040a9be9b53a09a'
BOT_TOKEN = '8821344722:AAFbrvqZHA43Wuc2hMB0WG-t1YGE4vsPzu4'

bot_client = TelegramClient('main_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_data = {}

print("🤖 Multi-User Advanced Restricted Bot is starting...")

# --- Helper Functions ---
def parse_link(url):
    clean_url = url.split('?')[0]
    parts = clean_url.split('/')
    if 't.me' in parts:
        tme_idx = parts.index('t.me')
    elif 'telegram.me' in parts:
        tme_idx = parts.index('telegram.me')
    else:
        return None, None
        
    if parts[tme_idx + 1] == 'c':
        entity = int("-100" + parts[tme_idx + 2])
    else:
        entity = parts[tme_idx + 1]
    msg_id = int(parts[-1])
    return entity, msg_id

async def progress_callback(current, total, status_msg, action_text, last_update):
    now = time.time()
    # 2 सेकंड में एक बार प्रोग्रेस बार अपडेट होगा ताकि Telegram ब्लॉक न करे
    if now - last_update[0] > 2:
        last_update[0] = now
        percent = (current / total) * 100
        filled = int(percent / 5)
        bar = '█' * filled + '░' * (20 - filled)
        txt = f"⏳ **{action_text}...**\n\n[{bar}] {percent:.1f}%\n"
        txt += f"📥 {current/(1024*1024):.2f} MB / {total/(1024*1024):.2f} MB"
        try:
            await bot_client.edit_message(status_msg, txt)
        except:
            pass

# --- Command Handlers ---
@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    if user_id not in user_data or user_data[user_id].get('step') not in ['COMPLETED', 'BATCH_START', 'BATCH_END']:
        user_data[user_id] = {'step': 'PHONE'}
        welcome_text = (
            "👋 **Welcome to Multi-User Restricted Saver Bot!**\n\n"
            "🔐 **लॉगिन करने के लिए नीचे दिए गए स्टेप्स फॉलो करें:**\n"
            "1. सबसे पहले अपना फ़ोन नंबर भेजें (जैसे: `+919876543210`)।"
        )
        await event.respond(welcome_text)
    else:
        await event.respond("✅ **आप पहले से लॉगिन हैं!** आप लिंक भेज सकते हैं या /help दबाएं।")

@bot_client.on(events.NewMessage(pattern='/help'))
async def help_cmd(event):
    help_text = (
        "🛠 **MAIN MENU**\n\n"
        "👋 /start - Start the Bot\n"
        "❓ /help - Show Help Menu\n"
        "❌ /cancel - Cancel Current Action\n"
        "📦 /batch - Batch Download (Step-by-Step)"
    )
    await event.respond(help_text)

@bot_client.on(events.NewMessage(pattern='/cancel'))
async def cancel_cmd(event):
    user_id = event.sender_id
    if user_id in user_data and user_data[user_id].get('step') in ['BATCH_START', 'BATCH_END']:
        user_data[user_id]['step'] = 'COMPLETED'
        await event.respond("❌ **करंट एक्शन कैंसिल कर दिया गया है।**")
    else:
        await event.respond("कोई भी पेंडिंग एक्शन नहीं मिला।")

@bot_client.on(events.NewMessage(pattern='/batch'))
async def batch_cmd(event):
    user_id = event.sender_id
    if user_id not in user_data or user_data[user_id].get('step') not in ['COMPLETED', 'BATCH_START', 'BATCH_END']:
        await event.respond("⚠️ **कृपया पहले /start करके लॉगिन करें!**")
        return
    
    user_data[user_id]['step'] = 'BATCH_START'
    batch_text = (
        "📦 **sᴛᴇᴘ-ʙʏ-sᴛᴇᴘ ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n"
        "sᴛᴇᴘ 1/2: sᴇɴᴅ ᴛʜᴇ ғɪʀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ:\n\n"
        "ᴇxᴀᴍᴘʟᴇ:\n"
        "`https://t.me/channelname/100`\n"
        "`https://t.me/c/1234567890/100`"
    )
    await event.respond(batch_text)

# --- Message Handler ---
@bot_client.on(events.NewMessage)
async def handle_all_messages(event):
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    if text.startswith('/'):
        return # Commands are handled above

    # स्टेप 1: फोन नंबर
    if user_id in user_data and user_data[user_id].get('step') == 'PHONE':
        clean_number = re.sub(r'\D', '', text) 
        if len(clean_number) == 10: clean_number = "91" + clean_number
        formatted_phone = "+" + clean_number
        
        status = await event.respond(f"⏳ **{formatted_phone} पर OTP भेज रहा हूँ...**")
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            send_code_obj = await client.send_code_request(formatted_phone)
            user_data[user_id].update({'step': 'OTP', 'phone': formatted_phone, 'phone_code_hash': send_code_obj.phone_code_hash, 'client': client})
            await bot_client.edit_message(status, "✅ **OTP भेज दिया गया है!**\nकोड को स्पेस देकर लिखें: `1 2 3 4 5`")
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # स्टेप 2: OTP
    if user_id in user_data and user_data[user_id].get('step') == 'OTP':
        status = await event.respond("⏳ **OTP जांचा जा रहा है...**")
        otp_code = text.replace(" ", "")
        client = user_data[user_id]['client']
        
        try:
            await client.sign_in(user_data[user_id]['phone'], otp_code, phone_code_hash=user_data[user_id]['phone_code_hash'])
            user_data[user_id] = {'step': 'COMPLETED', 'session': client.session.save()}
            await bot_client.edit_message(status, "🎉 **लॉगिन सफल!** अब लिंक भेजें।")
            await client.disconnect()
        except SessionPasswordNeededError:
            user_data[user_id]['step'] = 'PASSWORD'
            await bot_client.edit_message(status, "🔐 2-Step Verification पासवर्ड भेजें।")
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # स्टेप 3: 2FA Password
    if user_id in user_data and user_data[user_id].get('step') == 'PASSWORD':
        status = await event.respond("⏳ **पासवर्ड की जांच हो रही है...**")
        client = user_data[user_id]['client']
        try:
            await client.sign_in(password=text)
            user_data[user_id] = {'step': 'COMPLETED', 'session': client.session.save()}
            await bot_client.edit_message(status, "🎉 **लॉगिन सफल!** अब लिंक भेजें।")
            await client.disconnect()
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # --- BATCH LOGIC ---
    if user_id in user_data and user_data[user_id].get('step') == 'BATCH_START' and "t.me/" in text:
        entity, msg_id = parse_link(text)
        if not entity: return await event.respond("❌ अवैध लिंक।")
        user_data[user_id]['batch_entity'] = entity
        user_data[user_id]['batch_start_id'] = msg_id
        user_data[user_id]['step'] = 'BATCH_END'
        
        await event.respond(
            "📦 **sᴛᴇᴘ-ʙʏ-sᴛᴇᴘ ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n"
            "sᴛᴇᴘ 2/2: sᴇɴᴅ ᴛʜᴇ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ:\n\n"
            "(कृपया ध्यान दें: एक बार में मैक्सिमम 100 फाइलें ही डाउनलोड की जा सकती हैं।)"
        )
        return

    if user_id in user_data and user_data[user_id].get('step') == 'BATCH_END' and "t.me/" in text:
        entity, end_msg_id = parse_link(text)
        start_msg_id = user_data[user_id]['batch_start_id']
        saved_entity = user_data[user_id]['batch_entity']
        
        if str(entity) != str(saved_entity):
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond("❌ एरर: पहला और दूसरा लिंक एक ही चैनल/ग्रुप का होना चाहिए! प्रक्रिया रद्द कर दी गई।")
            
        if end_msg_id < start_msg_id:
            start_msg_id, end_msg_id = end_msg_id, start_msg_id # Swap if user sent backwards
            
        total_msgs = (end_msg_id - start_msg_id) + 1
        if total_msgs > 100:
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond(f"❌ **लिमिट 100 मैसेजेस की है!** आपने {total_msgs} मैसेजेस सेलेक्ट किये हैं। कृपया /batch फिर से शुरू करें।")

        user_data[user_id]['step'] = 'COMPLETED'
        await event.respond(f"🚀 **Batch Download शुरू हो रहा है... ({total_msgs} फाइल्स)**")
        
        user_session = user_data[user_id]['session']
        user_client = TelegramClient(StringSession(user_session), API_ID, API_HASH)
        await user_client.connect()

        for current_id in range(start_msg_id, end_msg_id + 1):
            try:
                status_msg = await event.respond(f"⏳ **मैसेज ID {current_id} प्रोसेस हो रहा है...**")
                msg = await user_client.get_messages(entity, ids=current_id)
                if msg and msg.media:
                    last_update = [time.time()]
                    # Download Progress
                    file_path = await user_client.download_media(
                        msg, 
                        progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Downloading", last_update)
                    )
                    
                    last_update = [time.time()]
                    # Upload Progress
                    await bot_client.send_file(
                        event.chat_id, 
                        file_path, 
                        caption=msg.text or f"Batch ID: {current_id}",
                        progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Uploading", last_update)
                    )
                    if os.path.exists(file_path): os.remove(file_path)
                    await bot_client.delete_messages(event.chat_id, status_msg.id)
                else:
                    await bot_client.edit_message(status_msg, f"⚠️ मैसेज ID {current_id} खाली है या टेक्स्ट है।")
                
                await asyncio.sleep(2) # Flood error से बचने के लिए
            except FloodWaitError as e:
                await event.respond(f"⚠️ Telegram ने ब्लॉक किया है, {e.seconds} सेकंड इंतज़ार कर रहा हूँ...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                pass # Ignore error for single file to continue loop
        
        await user_client.disconnect()
        await event.respond("✅ **Batch Download पूरी तरह से कम्पलीट हो गया है!**")
        return

    # --- SINGLE LINK LOGIC ---
    if "t.me/" in text:
        if user_id not in user_data or user_data[user_id].get('step') != 'COMPLETED':
            return await event.respond("⚠️ **कृपया पहले /start करके लॉगिन करें!**")

        entity, msg_id = parse_link(text)
        if not entity: return await event.respond("❌ अवैध लिंक।")

        status_msg = await event.respond("⏳ **डाउनलोड शुरू हो रहा है...**")
        try:
            user_session = user_data[user_id]['session']
            user_client = TelegramClient(StringSession(user_session), API_ID, API_HASH)
            await user_client.connect()
            
            msg = await user_client.get_messages(entity, ids=msg_id)
            if msg and msg.media:
                last_update = [time.time()]
                file_path = await user_client.download_media(
                    msg, 
                    progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Downloading", last_update)
                )
                
                last_update = [time.time()]
                await bot_client.send_file(
                    event.chat_id, 
                    file_path, 
                    caption=msg.text or "Downloaded!",
                    progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Uploading", last_update)
                )
                if os.path.exists(file_path): os.remove(file_path)
            else:
                await bot_client.edit_message(status_msg, "❌ यह मैसेज खाली है या इसमें कोई मीडिया नहीं है।")
                
            await user_client.disconnect()
            await bot_client.delete_messages(event.chat_id, status_msg.id)
        except Exception as e:
            await bot_client.edit_message(status_msg, f"❌ Error: {str(e)}")

if __name__ == '__main__':
    bot_client.run_until_disconnected()
      
