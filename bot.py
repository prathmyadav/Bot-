import os
import asyncio
import threading
import urllib.request
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

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
    
    # 🔥 ANTI-SLEEP SELF-PING LOGIC
    def start_pinging():
        while True:
            try:
                # 📌 Updated Render URL - Changed here
                bot_url = "https://bot-8x03.onrender.com" 
                urllib.request.urlopen(bot_url)
                print("[Self-Ping] Bot kept awake!")
            except Exception as e:
                print(f"[Self-Ping] Failed: {e}")
            import time
            time.sleep(300) # 5 मिनट का इंतजार

    # पिंग वाले काम को अलग बैकग्राउंड थ्रेड में चलाना
    ping_thread = threading.Thread(target=start_pinging)
    ping_thread.daemon = True
    ping_thread.start()
    httpd.serve_forever()

http_thread = threading.Thread(target=run_http_server)
http_thread.daemon = True
http_thread.start()
# -------------------------------------

# 📌 Updated Telegram API डिटेल्स और बॉट टोकन
API_ID = 33427426
API_HASH = 'a4c1eb3419e497aeb040a9be9b53a09a'
BOT_TOKEN = '8821344722:AAFbrvqZHA43Wuc2hMB0WG-t1YGE4vsPzu4'

bot_client = TelegramClient('main_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Users के लाइव सेशन्स और डेटा याद रखने के लिए मेमोरी डिक्शनरी
user_data = {}

print("🤖 Multi-User Advanced Restricted Bot is starting...")

@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    welcome_text = (
        "👋 **Welcome to Multi-User Restricted Saver Bot!**\n\n"
        "यह बॉट किसी भी रेस्ट्रिक्टेड चैनल/ग्रुप से मीडिया डाउनलोड कर सकता है। काम शुरू करने के लिए आपको एक बार लॉगिन करना होगा ताकि बॉट आपके अकाउंट के जरिए उस ग्रुप को एक्सेस कर सके।\n\n"
        "🔐 **लॉगिन करने के लिए नीचे दिए गए स्टेप्स फॉलो करें:**\n"
        "1. सबसे पहले अपना फ़ोन नंबर भेजें (जैसे: `+919876543210` या बिना प्लस के भी भेज सकते हैं)।"
    )
    user_data[user_id] = {'step': 'PHONE'}
    await event.respond(welcome_text)

@bot_client.on(events.NewMessage)
async def handle_all_messages(event):
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    if text.startswith('/start'):
        return

    # स्टेप 1: फोन नंबर कलेक्ट करना और OTP भेजना
    if user_id in user_data and user_data[user_id].get('step') == 'PHONE':
        clean_number = re.sub(r'\D', '', text) 
        if len(clean_number) == 10:
            clean_number = "91" + clean_number
        formatted_phone = "+" + clean_number
        
        if len(clean_number) < 11 or len(clean_number) > 15:
            await event.respond("❌ कृपया सही फ़ोन नंबर भेजें। देश का कोड होना ज़रूरी है (जैसे: `+919876543210`)")
            return
        
        status = await event.respond(f"⏳ **{formatted_phone} पर OTP कोड भेज रहा हूँ... कृपया प्रतीक्षा करें।**")
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            send_code_obj = await client.send_code_request(formatted_phone)
            user_data[user_id] = {
                'step': 'OTP',
                'phone': formatted_phone,
                'phone_code_hash': send_code_obj.phone_code_hash,
                'client': client
            }
            await bot_client.edit_message(status, "✅ **सफलतापूर्वक OTP भेज दिया गया है!**\n\nकोड को स्पेस देकर लिखें, जैसे: `1 2 3 4 5`")
        except Exception as e:
            await bot_client.edit_message(status, f"❌ **Error:** {str(e)}\nकृपया /start दबाकर दोबारा कोशिश करें।")
        return

    # स्टेप 2: OTP वेरीफाई करना
    if user_id in user_data and user_data[user_id].get('step') == 'OTP':
        status = await event.respond("⏳ **OTP जांचा जा रहा है...**")
        otp_code = text.replace(" ", "")
        client = user_data[user_id]['client']
        phone = user_data[user_id]['phone']
        phone_code_hash = user_data[user_id]['phone_code_hash']
        
        try:
            await client.sign_in(phone, otp_code, phone_code_hash=phone_code_hash)
            session_str = client.session.save()
            user_data[user_id] = {'step': 'COMPLETED', 'session': session_str}
            await bot_client.edit_message(status, "🎉 **लॉगिन सफल!** अब आप कोई भी रेस्ट्रिक्टेड मैसेज लिंक भेजें।")
            await client.disconnect()
        except SessionPasswordNeededError:
            user_data[user_id]['step'] = 'PASSWORD'
            await bot_client.edit_message(status, "🔐 2-Step Verification पासवर्ड भेजें।")
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # स्टेप 3: पासवर्ड हैंडलर
    if user_id in user_data and user_data[user_id].get('step') == 'PASSWORD':
        status = await event.respond("⏳ **पासवर्ड की जांच हो रही है...**")
        client = user_data[user_id]['client']
        try:
            await client.sign_in(password=text)
            session_str = client.session.save()
            user_data[user_id] = {'step': 'COMPLETED', 'session': session_str}
            await bot_client.edit_message(status, "🎉 **लॉगिन सफल!**")
            await client.disconnect()
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # स्टेप 4: लिंक डाउनलोड
    if "t.me/" in text:
        if user_id not in user_data or user_data[user_id].get('step') != 'COMPLETED':
            await event.respond("⚠️ **कृपया पहले /start करके लॉगिन करें!**")
            return

        status_msg = await event.respond("⏳ **डाउनलोड हो रहा है...**")
        try:
            parts = text.split('/')
            msg_id = int(parts[-1])
            entity = int("-100" + parts[-2]) if 'c' in parts else parts[-2]

            user_session = user_data[user_id]['session']
            user_client = TelegramClient(StringSession(user_session), API_ID, API_HASH)
            await user_client.connect()
            msg = await user_client.get_messages(entity, ids=msg_id)
            if msg and msg.media:
                file_path = await user_client.download_media(msg)
                await bot_client.send_file(event.chat_id, file_path, caption=msg.text or "Downloaded!")
                if os.path.exists(file_path): os.remove(file_path)
            await user_client.disconnect()
            await bot_client.delete_messages(event.chat_id, status_msg.id)
        except Exception as e:
            await bot_client.edit_message(status_msg, f"❌ Error: {str(e)}")

if __name__ == '__main__':
    bot_client.run_until_disconnected()
      
