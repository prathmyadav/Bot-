import os
import asyncio
import threading
import urllib.request
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault

# --- Custom Exception Cancel Karne Ke Liye ---
class CancelProcess(Exception):
    pass

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
    
    def start_pinging():
        while True:
            try:
                bot_url = "https://bot-1-kslk.onrender.com" 
                urllib.request.urlopen(bot_url)
            except Exception:
                pass
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

bot_client = TelegramClient('main_bot_session', API_ID, API_HASH)
bot_client.start(bot_token=BOT_TOKEN)

# 📌 Side Menu Bar Setup
async def set_bot_commands():
    try:
        commands = [
            BotCommand(command="start", description="Start the bot & Login"),
            BotCommand(command="help", description="Show Help Menu"),
            BotCommand(command="batch", description="Batch Download (Step-by-step)"),
            BotCommand(command="cancel", description="Stop & Cancel Current Action")
        ]
        await bot_client(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=commands
        ))
    except Exception as e:
        print(f"⚠️ Failed to set commands: {e}")

bot_client.loop.run_until_complete(set_bot_commands())

user_data = {}

print("🤖 Multi-User Advanced Restricted Bot is fully running...")

# 📌 Link Parser (Topics और Private Channels के लिए 100% Accurate)
def parse_link(url):
    try:
        clean_url = url.split('?')[0].strip()
        if clean_url.endswith('/'):
            clean_url = clean_url[:-1]
        parts = clean_url.split('/')
        
        if 't.me' in parts:
            tme_idx = parts.index('t.me')
        elif 'telegram.me' in parts:
            tme_idx = parts.index('telegram.me')
        else:
            return None, None
            
        # Private Channel & Topics (e.g., t.me/c/123456789/100 or t.me/c/123456789/5/100)
        if parts[tme_idx + 1] == 'c':
            entity = int("-100" + parts[tme_idx + 2])
            msg_id = int(parts[-1])
        # Web Link with /s/
        elif parts[tme_idx + 1] == 's':
            entity = parts[tme_idx + 2]
            msg_id = int(parts[-1])
        # Public Channel
        else:
            entity = parts[tme_idx + 1]
            msg_id = int(parts[-1])
            
        return entity, msg_id
    except Exception:
        return None, None

# 📌 Entity Cache Resolver: "PeerChannel Error" को हमेशा के लिए फिक्स करता है
async def get_message_with_cache(client, entity_id, msg_id):
    try:
        # पहले सीधे कोशिश करें
        return await client.get_messages(entity_id, ids=msg_id)
    except Exception as e:
        error_str = str(e).lower()
        if "find the input entity" in error_str or "private" in error_str or "channel" in error_str:
            print(f"[Cache Miss] Fetching dialogs for entity: {entity_id}")
            # अगर एरर आये, तो डायलॉग्स (चैट लिस्ट) में ग्रुप को ढूंढें
            target_entity = None
            async for dialog in client.iter_dialogs():
                if dialog.id == entity_id:
                    target_entity = dialog.entity
                    break
            
            if target_entity:
                # सटीक Entity Object का उपयोग करके मैसेज लाएं
                return await client.get_messages(target_entity, ids=msg_id)
            else:
                # आखिरी कोशिश: Get Entity
                target_entity = await client.get_entity(entity_id)
                return await client.get_messages(target_entity, ids=msg_id)
        else:
            raise e

# 📌 Progress Bar with Instant Cancel Support
async def progress_callback(current, total, status_msg, action_text, last_update, user_id):
    # अगर यूजर ने कैंसिल कर दिया है, तो तुरन्त एरर रेज करके प्रोसेस रोक दें
    if user_data.get(user_id, {}).get('step') == 'CANCELLED':
        raise CancelProcess("User stopped the process")

    now = time.time()
    if now - last_update[0] > 3: 
        last_update[0] = now
        percent = (current / total) * 100
        filled = int(percent / 5)
        bar = '█' * filled + '░' * (20 - filled)
        txt = f"⚡ **{action_text}...**\n\n[{bar}] {percent:.1f}%\n"
        txt += f"📥 {current/(1024*1024):.2f} MB / {total/(1024*1024):.2f} MB"
        try:
            await bot_client.edit_message(status_msg, txt)
        except:
            pass

@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    if user_id not in user_data or user_data[user_id].get('step') not in ['COMPLETED', 'BATCH_START', 'BATCH_END', 'PROCESSING']:
        user_data[user_id] = {'step': 'PHONE'}
        await event.respond("👋 **Welcome to Multi-User Restricted Saver Bot!**\n\nयह बॉट Topics और Restricted ग्रुप्स से भी मीडिया डाउनलोड कर सकता है।\n\n1. सबसे पहले अपना फ़ोन नंबर भेजें (जैसे: `+919876543210`)।")
    else:
        user_data[user_id]['step'] = 'COMPLETED'
        await event.respond("✅ **आप पहले से लॉगिन हैं!** आप लिंक भेज सकते हैं या /help दबाएं।")

@bot_client.on(events.NewMessage(pattern='/help'))
async def help_cmd(event):
    help_text = (
        "🛠 **MAIN MENU**\n\n"
        "👋 /start - Start & Login\n"
        "❓ /help - Show Help Menu\n"
        "❌ /cancel - Cancel Action (Turant rokne ke liye)\n"
        "📦 /batch - Batch Download"
    )
    await event.respond(help_text)

@bot_client.on(events.NewMessage(pattern='/cancel'))
async def cancel_cmd(event):
    user_id = event.sender_id
    if user_id in user_data:
        user_data[user_id]['step'] = 'CANCELLED'
        await event.respond("🛑 **Cancel Command Received!**\nचल रहे सभी डाउनलोड/अपलोड तुरंत रोके जा रहे हैं...")
    else:
        await event.respond("कोई भी पेंडिंग एक्शन नहीं मिला।")

@bot_client.on(events.NewMessage(pattern='/batch'))
async def batch_cmd(event):
    user_id = event.sender_id
    if user_id not in user_data or user_data[user_id].get('step') not in ['COMPLETED', 'CANCELLED']:
        return await event.respond("⚠️ **कृपया पहले /start करके लॉगिन करें!** या चल रहे प्रोसेस को पूरा होने दें।")
    
    user_data[user_id]['step'] = 'BATCH_START'
    await event.respond(
        "📦 **sᴛᴇᴘ-ʙʏ-sᴛᴇᴘ ʙᴀᴛᴄʜ ᴅᴏᴡɴʟᴏᴀᴅ**\n\n"
        "sᴛᴇᴘ 1/2: sᴇɴᴅ ᴛʜᴇ ғɪʀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ:\n\n"
        "`https://t.me/c/1234567890/100`"
    )

@bot_client.on(events.NewMessage)
async def handle_all_messages(event):
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    if text.startswith('/'):
        return

    # Login Logic: Phone
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

    # Login Logic: OTP
    if user_id in user_data and user_data[user_id].get('step') == 'OTP':
        status = await event.respond("⏳ **OTP जांचा जा रहा है...**")
        otp_code = text.replace(" ", "")
        client = user_data[user_id]['client']
        try:
            await client.sign_in(user_data[user_id]['phone'], otp_code, phone_code_hash=user_data[user_id]['phone_code_hash'])
            user_data[user_id] = {'step': 'COMPLETED', 'session': client.session.save()}
            await bot_client.edit_message(status, "🎉 **लॉगिन सफल!** अब कोई भी लिंक भेजें।")
            await client.disconnect()
        except SessionPasswordNeededError:
            user_data[user_id]['step'] = 'PASSWORD'
            await bot_client.edit_message(status, "🔐 2-Step Verification पासवर्ड भेजें।")
        except Exception as e:
            await bot_client.edit_message(status, f"❌ एरर: {str(e)}")
        return

    # Login Logic: Password
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

    # Batch Process Logic (Step 1)
    if user_id in user_data and user_data[user_id].get('step') == 'BATCH_START' and "t.me/" in text:
        entity, msg_id = parse_link(text)
        if not entity: return await event.respond("❌ अवैध लिंक या फॉर्मेट।")
        user_data[user_id]['batch_entity'] = entity
        user_data[user_id]['batch_start_id'] = msg_id
        user_data[user_id]['step'] = 'BATCH_END'
        return await event.respond("📦 **sᴛᴇᴘ 2/2: sᴇɴᴅ ᴛʜᴇ ʟᴀsᴛ ᴍᴇssᴀɢᴇ ʟɪɴᴋ:**")

    # Batch Process Logic (Step 2)
    if user_id in user_data and user_data[user_id].get('step') == 'BATCH_END' and "t.me/" in text:
        entity, end_msg_id = parse_link(text)
        start_msg_id = user_data[user_id]['batch_start_id']
        saved_entity = user_data[user_id]['batch_entity']
        
        if str(entity) != str(saved_entity):
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond("❌ एरर: पहला और दूसरा लिंक एक ही चैनल/ग्रुप का होना चाहिए! प्रक्रिया रद्द कर दी गई।")
            
        if end_msg_id < start_msg_id:
            start_msg_id, end_msg_id = end_msg_id, start_msg_id
            
        total_msgs = (end_msg_id - start_msg_id) + 1
        if total_msgs > 100:
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond(f"❌ लिमिट 100 मैसेजेस की है! आपने {total_msgs} सेलेक्ट किये हैं।")

        user_data[user_id]['step'] = 'PROCESSING'
        await event.respond(f"🚀 **Batch Download शुरू... ({total_msgs} फाइल्स)**\n(रद्द करने के लिए /cancel दबाएं)")
        
        user_session = user_data[user_id]['session']
        user_client = TelegramClient(StringSession(user_session), API_ID, API_HASH)
        await user_client.connect()

        for current_id in range(start_msg_id, end_msg_id + 1):
            if user_data[user_id].get('step') == 'CANCELLED':
                break

            status_msg = await event.respond(f"⏳ **मैसेज ID {current_id} प्रोसेस हो रहा है...**")
            file_path = None
            try:
                msg = await get_message_with_cache(user_client, entity, current_id)
                if msg and msg.media:
                    last_update = [time.time()]
                    file_path = await user_client.download_media(
                        msg, 
                        progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Fast Downloading", last_update, user_id)
                    )
                    
                    last_update = [time.time()]
                    caption_text = msg.text[:950] if msg.text else f"Batch ID: {current_id}"
                    await bot_client.send_file(
                        event.chat_id, 
                        file_path, 
                        caption=caption_text,
                        progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Fast Uploading", last_update, user_id)
                    )
                    if file_path and os.path.exists(file_path): os.remove(file_path)
                    await bot_client.delete_messages(event.chat_id, status_msg.id)
                else:
                    await bot_client.delete_messages(event.chat_id, status_msg.id)
                
                await asyncio.sleep(1.5)

            except CancelProcess:
                if file_path and os.path.exists(file_path): os.remove(file_path)
                await bot_client.edit_message(status_msg, "🛑 **प्रोसेस यूजर द्वारा रद्द कर दिया गया!**")
                break
            except FloodWaitError as e:
                await event.respond(f"⚠️ Telegram ने ब्लॉक किया है, {e.seconds} सेकंड इंतज़ार कर रहा हूँ...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                pass
        
        await user_client.disconnect()
        if user_data[user_id].get('step') == 'CANCELLED':
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond("🛑 **Batch Download सफलतापूर्वक रोक दिया गया है।**")
        else:
            user_data[user_id]['step'] = 'COMPLETED'
            return await event.respond("✅ **Batch Download पूरी तरह कम्पलीट हो गया है!**")

    # Single Link Logic
    if "t.me/" in text:
        if user_id not in user_data or user_data[user_id].get('step') not in ['COMPLETED', 'CANCELLED']:
            return await event.respond("⚠️ **कृपया पहले /start करके लॉगिन करें!** या कोई चल रहा प्रोसेस पूरा होने दें।")

        entity, msg_id = parse_link(text)
        if not entity: return await event.respond("❌ अवैध लिंक। कृपया सही फॉर्मेट में लिंक भेजें।")

        user_data[user_id]['step'] = 'PROCESSING'
        status_msg = await event.respond("⚡ **फास्ट डाउनलोड शुरू हो रहा है...**\n(रद्द करने के लिए /cancel दबाएं)")
        
        user_session = user_data[user_id]['session']
        user_client = TelegramClient(StringSession(user_session), API_ID, API_HASH)
        await user_client.connect()
        file_path = None
        
        try:
            msg = await get_message_with_cache(user_client, entity, msg_id)
            if msg and msg.media:
                last_update = [time.time()]
                file_path = await user_client.download_media(
                    msg, 
                    progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Fast Downloading", last_update, user_id)
                )
                
                last_update = [time.time()]
                caption_text = msg.text[:950] if msg.text else "Downloaded Successfully!"
                await bot_client.send_file(
                    event.chat_id, 
                    file_path, 
                    caption=caption_text,
                    progress_callback=lambda c, t: progress_callback(c, t, status_msg, "Fast Uploading", last_update, user_id)
                )
                if file_path and os.path.exists(file_path): os.remove(file_path)
                await bot_client.delete_messages(event.chat_id, status_msg.id)
            else:
                await bot_client.edit_message(status_msg, "❌ यह मैसेज खाली है या इसमें कोई फाइल/वीडियो नहीं है।")
                
        except CancelProcess:
            if file_path and os.path.exists(file_path): os.remove(file_path)
            await bot_client.edit_message(status_msg, "🛑 **डाउनलोड यूजर द्वारा रद्द कर दिया गया!**")
        except Exception as e:
            await bot_client.edit_message(status_msg, f"❌ Error: {str(e)}\n\n(Note: सुनिश्चित करें कि आप उस रेस्ट्रिक्टेड चैनल में जॉइन हैं)")
        finally:
            await user_client.disconnect()
            user_data[user_id]['step'] = 'COMPLETED'

if __name__ == '__main__':
    bot_client.run_until_disconnected()
    
