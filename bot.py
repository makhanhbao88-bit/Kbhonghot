import logging
import os
import re
import queue
import time
from pathlib import Path
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import telebot
from dotenv import load_dotenv

# --- WEB SERVER MINI (GIÚP RENDER KHÔNG BỊ NGỦ ĐÔNG) ---
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

threading.Thread(target=start_dummy_server, daemon=True).start()
# ---------------------------------------------------------

# ID NHÓM VIP
VIP_CHAT_ID = -1003910292149 

PAYLOAD_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-video-bot")

# Hàng đợi lưu trữ video chờ gửi để chống lỗi 429
video_queue = queue.Queue()
bot_instance = None

def worker():
    """Luồng ngầm tự động lấy video trong hàng đợi ra gửi từ từ"""
    while True:
        item = video_queue.get()
        if item is None:
            break
        message, file_id = item
        try:
            bot_instance.send_video(
                chat_id=VIP_CHAT_ID,
                video=file_id,
                caption=None, 
                supports_streaming=True,
                timeout=300,
            )
            bot_instance.reply_to(message, "✅ Đã đẩy video sạch lên nhóm VIP!")
        except Exception as e:
            bot_instance.reply_to(message, f"❌ Lỗi khi gửi: {e}")
        finally:
            video_queue.task_done()
            time.sleep(1.5) # Nghỉ 1.5 giây giữa các video để Telegram không phạt

# Chạy worker ngầm
threading.Thread(target=worker, daemon=True).start()


def build_bot() -> telebot.TeleBot:
    global bot_instance
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN.")

    bot = telebot.TeleBot(token)
    bot_instance = bot

    @bot.message_handler(commands=["start"])
    def handle_start(message: telebot.types.Message) -> None:
        bot.reply_to(message, "Bot tự động chuyển video sạch đang chạy ở chế độ Hàng đợi thông minh.")

    # BẮT VIDEO VÀ ĐẨY VÀO HÀNG ĐỢI
    @bot.message_handler(content_types=["video", "document", "animation"])
    def handle_video_auto_forward(message: telebot.types.Message) -> None:
        if message.chat.type != "private":
            return
            
        file_id = None
        if message.video:
            file_id = message.video.file_id
        elif message.document:
            file_id = message.document.file_id
        elif message.animation:
            file_id = message.animation.file_id

        if not file_id:
            bot.reply_to(message, "Không tìm thấy file video hợp lệ.")
            return

        # Cho video vào hàng đợi, bot sẽ tự xử lý lần lượt không lo quá tải
        video_queue.put((message, file_id))
        bot.reply_to(message, "⏳ Đã xếp vào hàng chờ gửi lên nhóm VIP...")

    return bot


def main() -> None:
    bot = build_bot()
    logger.info("Bot đang chạy ở chế độ polling với hàng đợi chống tràn...")
    bot.infinity_polling(skip_pending=False)


if __name__ == "__main__":
    main()
