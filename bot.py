import os
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Читаем токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not TELEGRAM_TOKEN or not YOUTUBE_API_KEY:
    print("❌ Ошибка: не заданы переменные окружения TELEGRAM_TOKEN и YOUTUBE_API_KEY")
    exit(1)

VIDEO_URLS = [
    "https://www.youtube.com/watch?v=vhbNHMy9w_8",
    "https://www.youtube.com/watch?v=ia9xsw4mACI",
    "https://www.youtube.com/watch?v=il_quDDa3zA",
    "https://www.youtube.com/watch?v=K2cejE7BCGU",
    "https://www.youtube.com/watch?v=sjBK0FrF2Vo",
    "https://www.youtube.com/watch?v=rVWdiVE6Q5A",
    "https://www.youtube.com/watch?v=XVnN3ZBamD8",
    "https://www.youtube.com/watch?v=O_7SX7lToRc",
    "https://www.youtube.com/watch?v=SaA_cVSHEHg",
    "https://www.youtube.com/watch?v=6PEz4pt_gzE",
    "https://www.youtube.com/watch?v=38v0Tmc_Oro",
    "https://www.youtube.com/watch?v=w7sYCnbAufY",
]

def extract_video_id(url):
    patterns = [r"v=([a-zA-Z0-9_-]{11})", r"youtu\.be/([a-zA-Z0-9_-]{11})"]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

def format_number(num):
    return f"{num:,}".replace(",", " ")

async def get_video_stats(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,statistics", "id": video_id, "key": YOUTUBE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if not data.get("items"):
            return {"error": "Видео не найдено"}
        v = data["items"][0]
        s = v.get("statistics", {})
        return {
            "title": v.get("snippet", {}).get("title", "Без названия"),
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "comments": int(s.get("commentCount", 0))
        }
    except Exception as e:
        return {"error": str(e)}

async def get_all_videos_info():
    ids = [extract_video_id(u) for u in VIDEO_URLS if extract_video_id(u)]
    if not ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet", "id": ",".join(ids), "key": YOUTUBE_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return [{"id": i["id"], "title": i["snippet"]["title"]} for i in data.get("items", [])]
    except:
        return []

async def start(update, context):
    await update.message.reply_text("📊 Загружаю список видео...")
    videos = await get_all_videos_info()
    if not videos:
        await update.message.reply_text("❌ Ошибка загрузки видео")
        return
    context.bot_data["videos"] = videos
    keyboard = [[InlineKeyboardButton(v["title"][:40], callback_data=f"vid_{v['id']}")] for v in videos]
    await update.message.reply_text("🎬 Выбери видео:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    video_id = query.data.replace("vid_", "")
    await query.edit_message_text("📊 Загружаю статистику...")
    stats = await get_video_stats(video_id)
    if "error" in stats:
        await query.edit_message_text(f"❌ {stats['error']}")
        return
    message = f"🎬 {stats['title']}\n\n👁 Просмотры: {format_number(stats['views'])}\n❤️ Лайки: {format_number(stats['likes'])}\n💬 Комментарии: {format_number(stats['comments'])}"
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def back_handler(update, context):
    query = update.callback_query
    await query.answer()
    videos = context.bot_data.get("videos", [])
    if not videos:
        await query.edit_message_text("Напиши /start")
        return
    keyboard = [[InlineKeyboardButton(v["title"][:40], callback_data=f"vid_{v['id']}")] for v in videos]
    await query.edit_message_text("🎬 Выбери видео:", reply_markup=InlineKeyboardMarkup(keyboard))

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler, pattern="^vid_"))
app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))

print("🤖 Бот запущен!")
app.run_polling()
