import logging
import os
import re
from pathlib import Path
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from dotenv import load_dotenv

# --- WEB SERVER MINI (HỖ TRỢ CẢ GET VÀ HEAD ĐỂ UPTIMEROBOT KHÔNG BÁO LỖI) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running smoothly!")
        
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Chạy server mini ở luồng ngầm để Render không bị Timeout
threading.Thread(target=start_dummy_server, daemon=True).start()
# -------------------------------------------------------------------------

# Kho chứa video và album
VIDEO_DATABASE = {
    "album_03": {
        "video": "BAACAgUAAxkBAAIIAAFq5hbJ-VYwpg_u0oJYTVtgu7829AACcSMAArjGMFdgJTzquNLgMz0E",
        "caption": "Album 03",
    },
    "album_05": {
        "video": "BAACAgUAAxkBAAIMvmrnORVx_B0D08EDt_Z6BIqdB4ffAALhQgACuMY4V4F1_7d5CiSsPQQ",
        "caption": "Album 05",
    },
    "album_04": {
        "videos": [ 
            "BAACAgUAAxkBAAIIXGrmI3hFzpwZ9MvHddA-rq06PBgZAAKtIwACuMYwV7KGfsr2GjQnPQQ",
            "BAACAgUAAxkBAAIIW2rmI3hySozeLjU-ZGTdF4AVH0s0AAKsIwACuMYwV0b-FmwP6uvCPQQ",
            "BAACAgUAAxkBAAIIXWrmI3hqkmElXRFmRy5dQM6nUnwPAAKuIwACuMYwVxVYlCWeLGOdPQQ",
        ],
        "caption": "Album 04",
    },
}

PAYLOAD_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-video-bot")


def build_bot() -> telebot.TeleBot:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN.")

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def handle_start(message: telebot.types.Message) -> None:
        parts = (message.text or "").strip().split(maxsplit=1)
        if len(parts) == 1:
            bot.reply_to(message, "Xin chào! Hãy mở đúng link chứa mã video.")
            return

        code = parts[1].strip()
        if not PAYLOAD_PATTERN.fullmatch(code):
            bot.reply_to(message, "Mã video không hợp lệ.")
            return

        video = VIDEO_DATABASE.get(code)
        if video is None:
            bot.reply_to(message, "Không tìm thấy video cho mã này.")
            return
        
        logger.info("Nhận lệnh /start cho mã video %s.", code)

        # 1. Gửi album nhiều video
        video_list = video.get("videos")
        if video_list:
            bot.reply_to(message, f"Đang gửi {len(video_list)} video, quá trình có thể mất một lúc...")
            for file_id in video_list:
                bot.send_video(message.chat.id, file_id)
            return

        # 2. Gửi video đơn
        video_source = video.get("video", "").strip()
        if video_source:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_source,
                caption=video.get("caption") or None,
                supports_streaming=True,
                timeout=300,
            )

    @bot.message_handler(content_types=["video"])
    def handle_video_upload(message: telebot.types.Message) -> None:
        if message.chat.type != "private" or message.video is None:
            return
        bot.reply_to(
            message,
            "file_id của video:\n"
            f"{message.video.file_id}\n\n"
            "Sao chép mã này vào VIDEO_DATABASE trong bot.py.",
        )

    return bot


def main() -> None:
    bot = build_bot()
    logger.info("Bot đang chạy ở chế độ polling...")
    bot.infinity_polling(skip_pending=False)


if __name__ == "__main__":
    main()
