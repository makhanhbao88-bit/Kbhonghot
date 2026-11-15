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
    self.wfile.write(b"Unlimited Downloader Bot is running smoothly!")

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
        "🚀 **Bot Tải Video Không Giới Hạn**\n\n"
        "Gửi link TikTok, YouTube, Facebook, Pinterest bất kỳ:\n"
        "• Dưới 50MB: Bot gửi video trực tiếp.\n"
        "• Trên 50MB (video nặng): Bot cung cấp link tải trực tiếp tốc độ cao ngay lập tức!\n"
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

    sent_msg = bot.reply_to(message, "⏳ Đang xử lý video chất lượng cao, đợi chút nha...")
    
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    # Cấu hình tải chất lượng tốt nhất không giới hạn định dạng
    ydl_opts = {
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
    }

    filename = None
    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        bot.send_chat_action(message.chat.id, "upload_video")
        info = ydl.extract_info(text, download=True)
        filename = ydl.prepare_filename(info)

      file_size_mb = os.path.getsize(filename) / (1024 * 1024)
      
      # Lấy domain render hiện tại để làm link tải nếu file quá nặng
      render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://chatgpt-5trb.onrender.com")
      file_basename = os.path.basename(filename)
      direct_link = f"{render_url}/downloads/{file_basename}"

      if file_size_mb > 50:
        # Nếu nặng hơn 50MB, gửi link trực tiếp từ server Render của em
        response_text = (
            f"📦 **Video này khá nặng ({file_size_mb:.1f}MB):**\n\n"
            f"Do Telegram giới hạn file gửi trực tiếp qua bot dưới 50MB, em bấm vào link dưới đây để tải trực tiếp bản Full HD về máy nhé:\n"
            f"👉 [Tải Video Ngay ({file_size_mb:.1f}MB)]({direct_link})"
        )
        bot.edit_message_text(response_text, message.chat.id, sent_msg.message_id, parse_mode="Markdown")
      else:
        # Dưới 50MB gửi file trực tiếp bình thường
        with open(filename, "rb") as f:
          bot.send_video(message.chat.id, f, reply_to_message_id=message.message_id)
        bot.delete_message(message.chat.id, sent_msg.message_id)
        
        # Xóa file ngay sau khi gửi để nhẹ server
        if filename and os.path.exists(filename):
          os.remove(filename)

    except Exception as e:
      logger.error(f"Lỗi tải xuống: {e}")
      try:
        bot.edit_message_text(
            "❌ Không thể tải xuống video này. Link có thể ở chế độ riêng tư hoặc bị lỗi.",
            message.chat.id,
            sent_msg.message_id
        )
      except Exception:
        pass
      if filename and os.path.exists(filename):
        os.remove(filename)

  return bot


def main() -> None:
  bot = build_bot()
  
  try:
    bot.remove_webhook()
    time.sleep(1)
  except Exception:
    pass

  logger.info("Unlimited Bot đang chạy ngầm mượt mà...")

  while True:
    try:
      bot.polling(none_stop=True, interval=3, timeout=30)
    except Exception as e:
      logger.error(f"Lỗi kết nối polling: {e}")
      time.sleep(5)


if __name__ == "__main__":
  main()
