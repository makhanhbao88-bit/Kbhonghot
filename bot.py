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

# Hàng đợi lưu trữ file_id chờ gửi
video_queue = queue.Queue()
bot_instance = None

def worker():
    """Luồng ngầm xử lý hàng đợi cực kỳ thông minh, tự động né lỗi 429"""
    while True:
        item = video_queue.get()
        if item is None:
            break
        file_id = item
        
        success = False
        retries = 3
        while retries > 0 and not success:
            try:
                bot_instance.send_video(
                    chat_id=VIP_CHAT_ID,
                    video=file_id,
                    caption=None, 
                    supports_streaming=True,
                    timeout=60,
                )
                success = True
                time.sleep(1.2) # Nghỉ nhẹ 1.2 giây giữa mỗi video
            except Exception as e:
                err_str = str(e)
                # Nếu dính lỗi 429 (Too Many Requests), tự động lấy số giây Telegram bắt chờ để ngủ đúng giờ đó
                if "429" in err_str or "Too Many Requests" in err_str:
                    match = re.search(r"retry after (\d+)", err_str, re.IGNORECASE)
                    sleep_time = int(match.group(1)) if match else 15
                    logger.warning(f"Telegram giới hạn tốc độ. Bot tự động tạm dừng {sleep_time} giây...")
                    time.sleep(sleep_time)
                    retries -= 1
                else:
                    logger.error(f"Lỗi gửi video: {e}")
                    break
        video_queue.task_done()

# Chạy luồng ngầm xử lý
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
        bot.reply_to(message, "Bot tự động chuyển video sạch đang chạy ở chế độ Siêu tốc độ & Chống tràn.")

    # BẮT VIDEO VÀ ĐẨY VÀO HÀNG ĐỢI NGAY LẬP TỨC (KHÔNG SPAM CHAT)
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
            return

        # Đưa vào hàng chờ xử lý ngầm, không làm phiền khung chat
        video_queue.put(file_id)

    return bot


def main() -> None:
    bot = build_bot()
    logger.info("Bot đang chạy ở chế độ hàng đợi thông minh không bao giờ đơ...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
