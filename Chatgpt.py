import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import telebot

# --- WEB SERVER MINI (CHỐNG NGỦ ĐÔNG TRÊN RENDER) ---
class HealthCheckHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"AI Gemini Bot is running smoothly!")

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

# TELEGRAM TOKEN
TELEGRAM_BOT_TOKEN = "9015116230:AAFdK09k3vOv9tuccDRBXaANCb4czFozZx8"

# LẤY GEMINI API KEY AN TOÀN TỪ RENDER
GEMINI_API_KEY = os.environ.get("GEMINI_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-ai-bot")


def ask_gemini(prompt: str) -> str:
  url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
  headers = {"Content-Type": "application/json"}
  data = {
      "contents": [{
          "parts": [{
              "text": (
                  "Bạn là một trợ lý AI thông minh, thân thiện và hữu ích."
                  f" Câu hỏi của người dùng: {prompt}"
              )
          }]
      }]
  }

  try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    res_json = response.json()
    # Lấy câu trả lời từ cấu trúc JSON của Gemini
    return res_json["candidates"][0]["content"]["parts"][0]["text"]
  except Exception as e:
    logger.error(f"Lỗi gọi Gemini API: {e}")
    return ""


def build_bot() -> telebot.TeleBot:
  bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

  try:
    bot.remove_webhook()
  except Exception:
    pass

  @bot.message_handler(commands=["start"])
  def handle_start(message: telebot.types.Message) -> None:
    bot.reply_to(
        message,
        "Xin chào! Tôi là trợ lý AI thông minh tích hợp Google Gemini miễn"
        " phí. Bạn muốn hỏi gì nào?",
    )

  @bot.message_handler(func=lambda message: True)
  def handle_chat_message(message: telebot.types.Message) -> None:
    if message.chat.type != "private":
      return

    user_text = message.text
    if not user_text:
      return

    try:
      bot.send_chat_action(message.chat.id, "typing")

      ai_reply = ask_gemini(user_text)
      if not ai_reply:
        ai_reply = "Xin lỗi, hiện tại hệ thống AI đang bận. Bạn thử lại sau nhé!"

      bot.reply_to(message, ai_reply, parse_mode="Markdown")

    except Exception as e:
      logger.error(f"Lỗi bot: {e}")
      bot.reply_to(message, "Đã có lỗi xảy ra, bạn thử lại sau nhé!")

  return bot


def main() -> None:
  bot = build_bot()
  logger.info("AI Gemini Bot đang chạy ngầm mượt mà...")
  bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
  main()
