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
        "🤖 **Bot Tải Video & MP3 Đa Năng**\n\n"
        "• **Tải Video:** Chỉ cần gửi link TikTok, YouTube, Facebook.\n"
        "• **Tải MP3:** Gửi link kèm chữ `mp3` ở cuối (Ví dụ: `link_youtube mp3`)"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

  @bot.message_handler(func=lambda message: True)
  def handle_link(message: telebot.types.Message) -> None:
    if message.chat.type != "private":
      return

    text = message.text
    if not text or not "http" in text:
      bot.reply_to(message, "⚠️ Vui lòng gửi một đường dẫn (link) hợp lệ nhé!")
      return

    # Kiểm tra xem người dùng có muốn lấy MP3 không
    is_mp3 = "mp3" in text.lower()
    # Tách lấy link sạch (bỏ chữ mp3 đi nếu có)
    clean_url = text.replace("mp3", "").replace("MP3", "").strip()

    action_name = "tách file MP3 🎵" if is_mp3 else "tải video 🎬"
    sent_msg = bot.reply_to(message, f"⏳ Đang {action_name}, chờ chút nha...")
    
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    # Cấu hình yt-dlp cho video hoặc mp3
    if is_mp3:
      ydl_opts = {
          "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
          "format": "bestaudio/best",
          "postprocessors": [{
              "key": "FFmpegExtractAudio",
              "preferredcodec": "mp3",
              "preferredquality": "192",
          }],
          "noplaylist": True,
          "http_headers": {
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          }
      }
    else:
      ydl_opts = {
          "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
          "format": "best",
          "noplaylist": True,
          "http_headers": {
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          }
      }

    filename = None
    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if is_mp3:
          bot.send_chat_action(message.chat.id, "upload_audio")
        else:
          bot.send_chat_action(message.chat.id, "upload_video")

        info = ydl.extract_info(clean_url, download=True)
        filename = ydl.prepare_filename(info)
        
        if is_mp3:
          filename = os.path.splitext(filename)[0] + ".mp3"

      file_size_mb = os.path.getsize(filename) / (1024 * 1024)
      render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://chatgpt-5trb.onrender.com")
      file_basename = os.path.basename(filename)
      direct_link = f"{render_url}/downloads/{file_basename}"

      if file_size_mb > 50:
        response_text = (
            f"📦 **File nặng {file_size_mb:.1f}MB:**\n\n"
            f"Vượt quá giới hạn 50MB của Telegram Bot API. Em bấm vào link dưới đây để tải trực tiếp nhé:\n"
            f"👉 [Tải File Ngay]({direct_link})"
        )
        bot.edit_message_text(response_text, message.chat.id, sent_msg.message_id, parse_mode="Markdown")
      else:
        if is_mp3:
          with open(filename, "rb") as f:
            bot.send_audio(message.chat.id, f, reply_to_message_id=message.message_id)
        else:
          with open(filename, "rb") as f:
            bot.send_video(message.chat.id, f, reply_to_message_id=message.message_id)
        bot.delete_message(message.chat.id, sent_msg.message_id)

      if filename and os.path.exists(filename):
        os.remove(filename)

    except Exception as e:
      logger.error(f"Lỗi xử lý: {e}")
      try:
        bot.edit_message_text(
            "❌ Không thể xử lý link này. Hãy thử lại với link khác nhé!",
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

  logger.info("Bot đang chạy mượt mà...")

  while True:
    try:
      bot.polling(none_stop=True, interval=3, timeout=30)
    except Exception as e:
      logger.error(f"Lỗi kết nối polling: {e}")
      time.sleep(5)


if __name__ == "__main__":
  main()
