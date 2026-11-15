import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from openai import OpenAI

# --- WEB SERVER MINI (CHỐNG NGỦ ĐÔNG TRÊN RENDER) ---
class HealthCheckHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"AI ChatGPT Bot is running smoothly!")

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

# CẤU HÌNH TOKEN VÀ API KEY MỚI NHẤT
TELEGRAM_BOT_TOKEN = "9015116230:AAFdK09k3vOv9tuccDRBXaANCb4czFozZx8"
OPENAI_API_KEY = "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"

# Khởi tạo OpenAI client (Sử dụng model GPT-4o thông minh)
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-ai-bot")


def build_bot() -> telebot.TeleBot:
  bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

  # Xóa webhook cũ đang bị kẹt (phòng hờ)
  try:
    bot.remove_webhook()
  except Exception:
    pass

  @bot.message_handler(commands=["start"])
  def handle_start(message: telebot.types.Message) -> None:
    bot.reply_to(
        message,
        "Xin chào! Tôi là trợ lý AI phiên bản cao cấp tích hợp GPT-4o. Bạn"
        " muốn hỏi gì hoặc cần tôi giúp gì nào?",
    )

  # NHẬN TIN NHẮN CHAT VÀ GỬI CHO AI XỬ LÝ
  @bot.message_handler(func=lambda message: True)
  def handle_chat_message(message: telebot.types.Message) -> None:
    if message.chat.type != "private":
      return  # Chỉ trả lời trong chat riêng tư

    user_text = message.text
    if not user_text:
      return

    try:
      # Hiển thị trạng thái "đang soạn tin..."
      bot.send_chat_action(message.chat.id, "typing")

      # Gọi API OpenAI GPT-4o
      response = client.chat.completions.create(
          model="gpt-4o",
          messages=[
              {
                  "role": "system",
                  "content": (
                      "Bạn là một trợ lý AI thông minh, thân thiện và hữu ích."
                  ),
              },
              {"role": "user", "content": user_text},
          ],
          temperature=0.7,
          max_tokens=1500,
      )

      ai_reply = response.choices[0].message.content
      bot.reply_to(message, ai_reply, parse_mode="Markdown")

    except Exception as e:
      logger.error(f"Lỗi khi gọi OpenAI API: {e}")
      bot.reply_to(
          message,
          "Xin lỗi, hiện tại hệ thống AI đang bận hoặc gặp sự cố nhỏ. Bạn thử"
          " lại sau nhé!",
      )

  return bot


def main() -> None:
  bot = build_bot()
  logger.info("AI ChatGPT Bot đang chạy ngầm mượt mà...")
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  main()
