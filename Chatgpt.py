import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import telebot
import yt_dlp

# --- WEB SERVER MINI (CHỐNG NGỦ ĐÔNG TRÊN RENDER) ---
class HealthCheckHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Utility Downloader Bot is running smoothly!")

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

# CẤU HÌNH TOKEN TELEGRAM BOT CỦA EM
TELEGRAM_BOT_TOKEN = "9015116230:AAFdK09k3vOv9tuccDRBXaANCb4czFozZx8"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("utility-bot")


def build_bot() -> telebot.TeleBot:
  bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

  @bot.message_handler(commands=["start", "help"])
  def handle_start(message: telebot.types.Message) -> None:
    welcome_text = (
        "🤖 **Chào mừng bạn đến với Bot Tiện Ích Đa Năng!**\n\n"
        "Gửi link bất kỳ để tải xuống:\n"
        "• 🎵 **TikTok** (Không logo / Full HD)\n"
        "• 📺 **YouTube** (Video Full HD hoặc tách MP3)\n"
        "• 📘 **Facebook** (Video công khai)\n"
        "• 📌 **Pinterest** (Hình ảnh & Video)\n\n"
        "👉 *Chỉ cần dán link trực tiếp vào khung chat này là bot tự động tải!*"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

  @bot.message_handler(func=lambda message: True)
  def handle_link(message: telebot.types.Message) -> None:
    if message.chat.type != "private":
      return

    text = message.text
    if not text or not text.startswith("http"):
      bot.reply_to(message, "⚠️ Vui lòng gửi một đường dẫn (link) hợp lệ nhé!")
      return

    sent_msg = bot.reply_to(message, "⏳ Đang xử lý và tải xuống, bạn đợi chút nhé...")
    
    # Thư mục lưu tạm file
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
        "max_filesize": 50 * 1024 * 1024,  # Giới hạn 50MB để gửi qua Telegram miễn phí
    }

    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        bot.send_chat_action(message.chat.id, "upload_video")
        info = ydl.extract_info(text, download=True)
        filename = ydl.prepare_filename(info)

      # Gửi file video về cho người dùng
      with open(filename, "rb") as f:
        bot.send_video(message.chat.id, f, reply_to_message_id=message.message_id)

      # Xóa file tạm sau khi gửi xong để nhẹ server
      os.remove(filename)
      bot.delete_message(message.chat.id, sent_msg.message_id)

    except Exception as e:
      logger.error(f"Lỗi tải xuống: {e}")
      try:
        bot.edit_message_text(
            "❌ Không thể tải xuống video này (link có thể bị lỗi, riêng tư hoặc dung lượng quá lớn >50MB).",
            message.chat.id,
            sent_msg.message_id
        )
      except Exception:
        pass

  return bot


def main() -> None:
  bot = build_bot()
  
  try:
    bot.remove_webhook()
    time.sleep(1)
  except Exception:
    pass

  logger.info("Utility Bot đang chạy ngầm mượt mà...")

  while True:
    try:
      bot.polling(none_stop=True, interval=3, timeout=30)
    except Exception as e:
      logger.error(f"Lỗi kết nối polling: {e}")
      time.sleep(5)


if __name__ == "__main__":
  main()
