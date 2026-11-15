import logging
import os
import queue
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot

# --- WEB SERVER MINI (CHỐNG NGỦ ĐÔNG TRÊN RENDER) ---
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

# MÃ TOKEN ĐÃ ĐƯỢC CẬP NHẬT TRỰC TIẾP
BOT_TOKEN = "9256145713:AAHgEal2tDARtTQZOVqw2gJuR9-d8B9nhvY"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-video-bot")

# Hàng đợi chứa file_id
video_queue = queue.Queue()
bot_instance = None


def worker():
  """Luồng ngầm xử lý hàng đợi tuần tự, né lỗi 429 tuyệt đối"""
  while True:
    file_id = video_queue.get()
    if file_id is None:
      break

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
        time.sleep(1.2)  # Khoảng nghỉ an toàn giữa các video
      except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Too Many Requests" in err_str:
          match = (
              re.search(r"retry after (\d+)", err_str, re.IGNORECASE)
              if "re" in globals()
              else None
          )
          sleep_time = int(match.group(1)) if match else 15
          logger.warning(
              f"Bị giới hạn tốc độ, bot tạm nghỉ {sleep_time} giây..."
          )
          time.sleep(sleep_time)
          retries -= 1
        else:
          logger.error(f"Lỗi gửi video: {e}")
          break
    video_queue.task_done()


threading.Thread(target=worker, daemon=True).start()


def build_bot() -> telebot.TeleBot:
  global bot_instance
  token = BOT_TOKEN.strip()
  if not token:
    raise RuntimeError("Chưa điền BOT_TOKEN vào code.")

  bot = telebot.TeleBot(token)
  bot_instance = bot

  @bot.message_handler(commands=["start"])
  def handle_start(message: telebot.types.Message) -> None:
    bot.reply_to(
        message, "Bot tự động chuyển video sạch đang chạy ngầm siêu tốc."
    )

  # BẮT VIDEO VÀ ĐẨY THẲNG VÀO HÀNG ĐỢI (HOÀN TOÀN KHÔNG SPAM CHAT)
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

    if file_id:
      video_queue.put(file_id)

  return bot


def main() -> None:
  bot = build_bot()
  logger.info("Bot đang chạy ngầm mượt mà...")
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  main()
