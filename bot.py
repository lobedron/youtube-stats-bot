import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "8719951045:AAH-Q9aUFCKqU67TjayYpSlz6WAD8sZOwRw"
YOUTUBE_API_KEY = "AIzaSyCJQp6Yo_tHBJOQAF5JG-lXN7wsTpVDAXk"

# ========== НАСТРОЙКИ ПРОКСИ (ВЫБЕРИ ОДИН ВАРИАНТ) ==========
# Вариант 1: Если используешь VPN на компьютере (VPN уже запущен) - раскомментируй строку ниже
PROXY_URL = "socks5://127.0.0.1:1080"  # Для VPN через SOCKS5 (чаще всего порт 1080)

# Вариант 2: Если используешь HTTP прокси
# PROXY_URL = "http://127.0.0.1:8080"  # Для HTTP прокси

# Вариант 3: Если VPN не используешь, оставь PROXY_URL = None
PROXY_URL = None  # Если не используешь прокси

# Список ссылок на видео
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
# =================================

def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def format_number(num: int) -> str:
    return f"{num:,}".replace(",", " ")

async def get_video_stats(video_id: str) -> dict:
    api_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": YOUTUBE_API_KEY,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=15)
        data = response.json()
        
        if not data.get("items"):
            return {"error": "❌ Видео не найдено или приватное"}
        
        video = data["items"][0]
        stats = video.get("statistics", {})
        snippet = video.get("snippet", {})
        
        return {
            "title": snippet.get("title", "Без названия"),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        }
    except Exception as e:
        return {"error": f"⚠ Ошибка API: {str(e)}"}

async def get_all_videos_info() -> list:
    video_ids = [extract_video_id(url) for url in VIDEO_URLS if extract_video_id(url)]
    if not video_ids:
        return []
    
    api_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=15)
        data = response.json()
        
        videos_info = []
        for item in data.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            
            videos_info.append({
                "id": video_id,
                "title": snippet.get("title", "Без названия"),
                "url": f"https://youtu.be/{video_id}"
            })
        return videos_info
    except Exception as e:
        print(f"Ошибка получения списка видео: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Загружаю список видео...")
    
    videos_info = await get_all_videos_info()
    
    if not videos_info:
        await update.message.reply_text("❌ Не удалось загрузить список видео. Проверь API ключ и ссылки.")
        return
    
    context.bot_data["videos_info"] = videos_info
    
    keyboard = []
    for video in videos_info:
        title = video["title"][:40] + "..." if len(video["title"]) > 40 else video["title"]
        keyboard.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"video_{video['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎬 **Выбери видео**\n\n"
        "Нажми на кнопку — бот покажет актуальные просмотры, лайки и комментарии.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    video_id = query.data.replace("video_", "")
    
    await query.edit_message_text("📊 Загружаю статистику...")
    
    stats = await get_video_stats(video_id)
    
    if "error" in stats:
        await query.edit_message_text(stats["error"])
        return
    
    message = (
        f"🎬 **{stats['title']}**\n\n"
        f"👁 **Просмотры:** {format_number(stats['views'])}\n"
        f"❤️ **Лайки:** {format_number(stats['likes'])}\n"
        f"💬 **Комментарии:** {format_number(stats['comments'])}\n\n"
        f"🔄 *Обновлено сейчас*"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад к списку", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    videos_info = context.bot_data.get("videos_info", [])
    
    if not videos_info:
        await query.edit_message_text("❌ Ошибка: список видео не найден. Напиши /start заново.")
        return
    
    keyboard = []
    for video in videos_info:
        title = video["title"][:40] + "..." if len(video["title"]) > 40 else video["title"]
        keyboard.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"video_{video['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "🎬 **Выбери видео**\n\n"
        "Нажми на кнопку — бот покажет актуальные просмотры, лайки и комментарии.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def main():
    # Настройка прокси для Telegram бота
    if PROXY_URL:
        # Создаём request с прокси
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(proxy_url=PROXY_URL)
        app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
    else:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^video_"))
    app.add_handler(CallbackQueryHandler(back_handler, pattern="^back$"))
    
    print("🤖 Бот запущен! Напиши /start в Telegram")
    app.run_polling()

if __name__ == "__main__":
    main()
