import logging
import os
import re
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

# ID NHÓM VIP ĐÃ ĐƯỢC THIẾT LẬP SẴN
VIP_CHAT_ID = -1003910292149 

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
        bot.reply_to(message, "Bot tự động chuyển video sạch lên nhóm VIP đang hoạt động.")

    # TỰ ĐỘNG BẮT VIDEO CHUYỂN TIẾP VÀ ĐẨY THẲNG LÊN NHÓM VIP
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

        try:
            # Gửi thẳng vào nhóm VIP, hoàn toàn sạch không dính chữ Forwarded
            bot.send_video(
                chat_id=VIP_CHAT_ID,
                video=file_id,
                caption=message.caption or None,
                supports_streaming=True,
                timeout=300,
            )
            bot.reply_to(message, "✅ Đã tự động đẩy video sạch lên nhóm VIP thành công!")
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi khi gửi vào nhóm VIP (Kiểm tra lại quyền admin của bot trong nhóm): {e}")

    return bot


def main() -> None:
    bot = build_bot()
    logger.info("Bot đang chạy ở chế độ polling tự động đẩy video...")
    bot.infinity_polling(skip_pending=False)


if __name__ == "__main__":
    main()
