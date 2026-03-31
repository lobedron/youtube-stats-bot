import os
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
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
            "comments": int(s.get("commentCount", 0)),
            "url": f"https://youtu.be/{video_id}"
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

def build_menu(buttons, n_cols):
    """Вспомогательная функция для создания сетки кнопок"""
    return [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wait_msg = await update.message.reply_text("⏳ *Загружаю список видео...*", parse_mode=ParseMode.MARKDOWN)
    
    videos = await get_all_videos_info()
    if not videos:
        await wait_msg.edit_text("❌ *Ошибка загрузки данных из YouTube.*")
        return
    
    context.bot_data["videos"] = videos
    
    # Создаем кнопки (по 2 в ряд)
    buttons = []
    for i, v in enumerate(videos, 1):
        # Обрезаем название, чтобы кнопка не была слишком огромной
        short_title = f"{i}. {v['title'][:20]}..."
        buttons.append(InlineKeyboardButton(short_title, callback_data=f"vid_{v['id']}"))
    
    keyboard = build_menu(buttons, n_cols=2)
    
    await wait_msg.edit_text(
        "<b>🎬 Выберите видео для просмотра статистики:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    video_id = query.data.replace("vid_", "")
    await query.edit_message_text("📊 *Собираю аналитику...*", parse_mode=ParseMode.MARKDOWN)
    
    stats = await get_video_stats(video_id)
    if "error" in stats:
        await query.edit_message_text(f"❌ *Ошибка:* {stats['error']}", parse_mode=ParseMode.MARKDOWN)
        return

    # Красивое оформление текста статистики
    message = (
        f"<b>📌 {stats['title']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👁 <b>Просмотры:</b>  <code>{format_number(stats['views'])}</code>\n"
        f"❤️ <b>Лайки:</b>      <code>{format_number(stats['likes'])}</code>\n"
        f"💬 <b>Комменты:</b>   <code>{format_number(stats['comments'])}</code>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌐 Смотреть на YouTube", url=stats['url'])],
        [InlineKeyboardButton("◀️ Вернуться к списку", callback_data="back")]
    ]
    
    await query.edit_message_text(
        message, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode=ParseMode.HTML
    )

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    videos = context.bot_data.get("videos", [])
    if not videos:
        await query.edit_message_text("Напишите /start, чтобы обновить список.")
        return
    
    buttons = []
    for i, v in enumerate(videos, 1):
        short_title = f"{i}. {v['title'][:20]}..."
        buttons.append(InlineKeyboardButton(short_title, callback_data=f"vid_{v['id']}"))
    
    keyboard = build_menu(buttons, n_cols=2)
    
    await query.edit_message_text(
        "<b>🎬 Выберите видео:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# Настройка приложения
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler, pattern="^vid_"))
app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))

print("🤖 Бот запущен и готов к работе!")
app.run_polling()
