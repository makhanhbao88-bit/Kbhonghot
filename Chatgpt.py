import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import google.generativeai as genai
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6LD6GGVhuR00Rz9Nnu8xX6xDNoJr1kHNV3Ff9qD7gt6WQ")

genai.configure(api_key=GEMINI_API_KEY)

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
        "🤖 **Bot Tiện Ích Sáng Tạo Nội Dung & Affiliate TikTok**\n\n"
        "🎬 **Tải Video / MP3:**\n"
        "• Gửi link TikTok, YouTube, Facebook để tải video không giới hạn.\n"
        "• Gửi link kèm chữ `mp3` để tách nhạc.\n\n"
        "🛡️ **Kiểm tra vi phạm trước khi đăng:**\n"
        "• Gửi file video trực tiếp vào bot để AI phân tích rủi ro, chỉ ra lỗi và hướng dẫn sửa.\n\n"
        "📜 **Cẩm nang TikTok:**\n"
        "• Gõ `/rules` để xem danh sách hành vi cấm."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

  @bot.message_handler(commands=["rules", "luat"])
  def handle_rules(message: telebot.types.Message) -> None:
    rules_text = (
        "🛡️ **CẨM NANG NÉ TRÁNH VI PHẠM TIKTOK (AFFILIATE)**\n\n"
        "**1. Gian lận thương mại & Điều hướng:**\n"
        "• Không điều hướng ra nền tảng khác (zalo, sđt, link bio).\n"
        "• Không thổi phồng công dụng sản phẩm (mỹ phẩm, TPCN tránh từ 'chữa khỏi', 'giảm cân thần tốc').\n"
        "• Không bán hàng giả, hàng kém chất lượng.\n\n"
        "**2. Bản quyền & Nội dung rác (Unoriginal):**\n"
        "• Không reup video thô; bắt buộc biên tập sáng tạo lại (cắt ghép, lồng tiếng, đổi góc nhìn).\n"
        "• Dùng kho nhạc thương mại của TikTok, tránh dính bản quyền âm thanh.\n"
        "• Không để lộ logo Douyin hoặc watermark mờ của bên thứ 3.\n\n"
        "**3. An toàn & Hình ảnh:**\n"
        "• Mặc đồ lịch sự, không hở hang phản cảm.\n"
        "• Không chứa nội dung bạo lực, vũ khí, chất kích thích.\n"
    )
    bot.reply_to(message, rules_text, parse_mode="Markdown")

  @bot.message_handler(content_types=["video", "document"])
  def handle_video_check(message: telebot.types.Message) -> None:
    sent_msg = bot.reply_to(message, "🔍 Bot đang phân tích video, chờ chút nha...")
    
    video_path = "downloads"
    os.makedirs(video_path, exist_ok=True)
    
    local_video_path = None
    video_file = None

    try:
      if message.video:
        file_info = bot.get_file(message.video.file_id)
        local_video_path = os.path.join(video_path, f"{message.video.file_id}.mp4")
      elif message.document:
        file_info = bot.get_file(message.document.file_id)
        local_video_path = os.path.join(video_path, f"{message.document.file_id}.mp4")
      else:
        bot.edit_message_text("⚠️ Vui lòng gửi một tệp video hợp lệ nhé!", message.chat.id, sent_msg.message_id)
        return

      downloaded_file = bot.download_file(file_info.file_path)
      with open(local_video_path, "wb") as f:
        f.write(downloaded_file)

      bot.send_chat_action(message.chat.id, "typing")
      
      video_file = genai.upload_file(path=local_video_path)
      
      while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

      prompt = (
          "Bạn là một chuyên gia kiểm duyệt nội dung và chính sách an toàn của TikTok. "
          "Hãy phân tích video này dưới góc độ thuật toán và Tiêu chuẩn cộng đồng TikTok (đặc biệt cho kênh Affiliate). "
          "Hãy đưa ra đánh giá theo cấu trúc sau:\n"
          "1. **Mức độ rủi ro:** (Thấp / Trung bình / Cao)\n"
          "2. **Các lỗi có thể vi phạm:** (Ví dụ: hở hang, điều hướng sđt/zalo, thổi phồng công dụng sản phẩm, dính logo lạ, bản quyền, v.v.)\n"
          "3. **Lý do chi tiết:** Phân tích cụ thể đoạn nào có vấn đề.\n"
          "4. **Hướng dẫn chỉnh sửa:** Cần cắt bỏ, che hoặc sửa thế nào để an toàn 100% trước khi đăng."
      )

      analysis_model = genai.GenerativeModel("gemini-1.5-flash")
      response = analysis_model.generate_content([video_file, prompt])
      
      bot.edit_message_text(
          f"📊 **KẾT QUẢ KIỂM TRA VIDEO (AI SCANNER)**\n\n{response.text}",
          message.chat.id,
          sent_msg.message_id,
          parse_mode="Markdown"
      )

    except Exception as e:
      logger.error(f"Lỗi kiểm tra video: {e}")
      try:
        bot.edit_message_text(
            f"❌ Không thể phân tích video này. Chi tiết lỗi: {str(e)[:100]}",
            message.chat.id,
            sent_msg.message_id
        )
      except Exception:
        pass

    try:
      if video_file:
        genai.delete_file(video_file.name)
      if local_video_path and os.path.exists(local_video_path):
        os.remove(local_video_path)
    except Exception:
      pass

  @bot.message_handler(func=lambda message: True)
  def handle_link(message: telebot.types.Message) -> None:
    if message.chat.type != "private":
      return

    text = message.text
    if not text or not "http" in text:
      bot.reply_to(message, "⚠️ Vui lòng gửi link hợp lệ, gửi video để kiểm tra vi phạm, hoặc gõ `/rules` để xem luật TikTok nhé!")
      return

    is_mp3 = "mp3" in text.lower()
    clean_url = text.replace("mp3", "").replace("MP3", "").strip()

    action_name = "tách file MP3 🎵" if is_mp3 else "tải video 🎬"
    sent_msg = bot.reply_to(message, f"⏳ Đang {action_name}, chờ chút nha...")
    
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

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

  logger.info("Bot đa năng đang chạy mượt mà...")

  while True:
    try:
      bot.polling(none_stop=True, interval=3, timeout=30)
    except Exception as e:
      logger.error(f"Lỗi kết nối polling: {e}")
      time.sleep(5)


if __name__ == "__main__":
  main()
