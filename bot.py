import os
import re
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8851691695:AAGI1ZXR2QklcrfIIJ2sggMn5XmfFNfWghY"
REDGIFS_API = "https://api.redgifs.com/v2"

def get_token():
    try:
        r = requests.get(f"{REDGIFS_API}/auth/temporary", timeout=10)
        return r.json().get("token")
    except:
        return None

def extract_id(url):
    m = re.search(r'redgifs\.com/(?:watch/|ifr/)?([a-zA-Z0-9]+)', url)
    return m.group(1) if m else None

def get_video(gif_id, token):
    try:
        r = requests.get(f"{REDGIFS_API}/gifs/{gif_id.lower()}", 
                        headers={'Authorization': f'Bearer {token}'}, timeout=15)
        return r.json()
    except:
        return None

def get_best_url(data):
    try:
        urls = data.get("gif", {}).get("urls", {})
        for q in ["hd", "sd", "gif"]:
            if q in urls:
                return urls[q]
    except:
        pass
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *RedGifs Downloader Bot*\n\n"
        "Send me any RedGifs link!\n\n"
        "Example: `https://www.redgifs.com/watch/xxxxx`",
        parse_mode='Markdown'
    )

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    gif_id = extract_id(url)
    
    if not gif_id:
        await update.message.reply_text("❌ Invalid link!")
        return
    
    msg = await update.message.reply_text("⏳ Processing...")
    
    token = get_token()
    if not token:
        await msg.edit_text("❌ Auth failed!")
        return
    
    data = get_video(gif_id, token)
    if not data:
        await msg.edit_text("❌ Video not found!")
        return
    
    video_url = get_best_url(data)
    if not video_url:
        await msg.edit_text("❌ No video URL!")
        return
    
    gif = data.get("gif", {})
    title = gif.get("title", "Video")[:50]
    
    await msg.edit_text(f"⬇️ Downloading: {title}...")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.redgifs.com/'}
        r = requests.get(video_url, headers=headers, stream=True, timeout=60)
        
        size = int(r.headers.get('content-length', 0))
        if size > 50 * 1024 * 1024:
            await msg.edit_text(f"⚠️ Too large! Direct link:\n`{video_url}`", parse_mode='Markdown')
            return
        
        path = f"/tmp/{gif_id}.mp4"
        with open(path, 'wb') as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        await msg.edit_text("📤 Uploading...")
        
        with open(path, 'rb') as f:
            await update.message.reply_video(
                video=f,
                caption=f"🎬 *{title}*\n🔗 [Source]({url})",
                parse_mode='Markdown'
            )
        
        os.remove(path)
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:100]}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
