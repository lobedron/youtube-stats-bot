import os
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Токены
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

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
    """Загружаем данные всех видео сразу, чтобы листание было мгновенным"""
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
    """Создает кнопки навигации"""
    # Определяем индексы для кнопок "Назад" и "Вперед" (с закольцовыванием)
    prev_idx = (index - 1) % total
    next_idx = (index + 1) % total
    
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"show_{prev_idx}"),
            InlineKeyboardButton(f"{index + 1} / {total}", callback_data="ignore"),
            InlineKeyboardButton("Вперед ➡️", callback_data=f"show_{next_idx}")
        ],
        [InlineKeyboardButton("🌐 Смотреть на YouTube", url=VIDEO_URLS[index])]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_message(video_data):
    """Красиво оформляет текст под фото"""
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
    
    context.bot_data["videos"] = videos
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

    index = int(query.data.replace("show_", ""))
    videos = context.bot_data.get("videos")
    
    if not videos:
        await query.answer("Данные устарели, введите /start", show_alert=True)
        return

    video = videos[index]
    
    # Обновляем фото и подпись в существующем сообщении
    await query.edit_message_media(
        media=InputMediaPhoto(
            media=video['thumb'],
            caption=format_message(video),
            parse_mode=ParseMode.HTML
        ),
        reply_markup=create_keyboard(index, len(videos))
    )
    await query.answer()

# Запуск
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(nav_handler, pattern="^show_|^ignore"))

print("🤖 Галерея запущена!")
app.run_polling()
