import os
import requests
import re
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== ВЕБ-СЕРВЕР ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Бот работает!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ========== ТОКЕНЫ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

# Если переменные не заданы — используем значения напрямую
if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = "8719951045:AAH-Q9aUFCKqU67TjayYpSlz6WAD8sZOwRw"
if not YOUTUBE_API_KEY:
    YOUTUBE_API_KEY = "AIzaSyCJQp6Yo_tHBJOQAF5JG-lXN7wsTpVDAXk"

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
    m = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None

def format_number(num):
    return f"{num:,}".replace(",", " ")

async def get_full_data():
    ids = [extract_video_id(u) for u in VIDEO_URLS if extract_video_id(u)]
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,statistics", "id": ",".join(ids), "key": YOUTUBE_API_KEY}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "id": item["id"],
                "title": item["snippet"]["title"],
                "thumb": item["snippet"]["thumbnails"]["high"]["url"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
                "url": f"https://youtu.be/{item['id']}"
            })
        return results
    except Exception as e:
        print(f"Ошибка API: {e}")
        return []

def create_keyboard(index, total):
    prev_idx = (index - 1) % total
    next_idx = (index + 1) % total
    
    nav_buttons = [
        InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{prev_idx}"),
        InlineKeyboardButton(f"{index + 1} / {total}", callback_data="ignore"),
        InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_{next_idx}")
    ]
    
    sort_buttons = [
        InlineKeyboardButton("📊 По просмотрам (↓)", callback_data="sort_by_views"),
        InlineKeyboardButton("🔄 Исходный порядок", callback_data="reset_order")
    ]
    
    youtube_button = [InlineKeyboardButton("🌐 Смотреть на YouTube", url=VIDEO_URLS[index])]
    
    keyboard = [nav_buttons, sort_buttons, youtube_button]
    return InlineKeyboardMarkup(keyboard)

def format_message(video_data):
    return (
        f"<b>🎬 {video_data['title']}</b>\n\n"
        f"👁 <b>Просмотры:</b>  <code>{format_number(video_data['views'])}</code>\n"
        f"❤️ <b>Лайки:</b>      <code>{format_number(video_data['likes'])}</code>\n"
        f"💬 <b>Комменты:</b>   <code>{format_number(video_data['comments'])}</code>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ *Загружаю видео-галерею...*", parse_mode=ParseMode.MARKDOWN)
    
    videos = await get_full_data()
    if not videos:
        await msg.edit_text("❌ Ошибка загрузки данных.")
        return
    
    context.bot_data["original_videos"] = videos.copy()
    context.bot_data["videos"] = videos.copy()
    video = videos[0]
    
    await update.message.reply_photo(
        photo=video['thumb'],
        caption=format_message(video),
        reply_markup=create_keyboard(0, len(videos)),
        parse_mode=ParseMode.HTML
    )
    await msg.delete()

async def nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "ignore":
        await query.answer()
        return

    if query.data.startswith("nav_"):
        index = int(query.data.replace("nav_", ""))
        videos = context.bot_data.get("videos")
        if not videos:
            await query.answer("Данные устарели, введите /start", show_alert=True)
            return
        
        video = videos[index]
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=video['thumb'],
                caption=format_message(video),
                parse_mode=ParseMode.HTML
            ),
            reply_markup=create_keyboard(index, len(videos))
        )
        await query.answer()
        return

    if query.data == "sort_by_views":
        await query.answer("Сортирую по просмотрам...")
        fresh_videos = await get_full_data()
        if not fresh_videos:
            await query.answer("Ошибка загрузки данных", show_alert=True)
            return
        
        sorted_videos = sorted(fresh_videos, key=lambda x: x["views"], reverse=True)
        context.bot_data["videos"] = sorted_videos
        video = sorted_videos[0]
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=video['thumb'],
                caption=format_message(video),
                parse_mode=ParseMode.HTML
            ),
            reply_markup=create_keyboard(0, len(sorted_videos))
        )
        return

    if query.data == "reset_order":
        await query.answer("Возвращаю исходный порядок...")
        original = context.bot_data.get("original_videos")
        if not original:
            await query.answer("Нет исходного списка", show_alert=True)
            return
        context.bot_data["videos"] = original.copy()
        video = original[0]
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=video['thumb'],
                caption=format_message(video),
                parse_mode=ParseMode.HTML
            ),
            reply_markup=create_keyboard(0, len(original))
        )
        return

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    
    # Запускаем Telegram-бота
    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(nav_handler, pattern="^(nav_|ignore|sort_by_views|reset_order)"))
    
    print("🤖 Бот запущен! Веб-сервер на порту 10000")
    bot_app.run_polling()
