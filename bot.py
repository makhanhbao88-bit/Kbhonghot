import os
import threading
import telebot
from flask import Flask

# Lấy token từ biến môi trường của Render
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Lỗi: Chưa thiết lập biến môi trường BOT_TOKEN trên Render!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Trang chủ giả lập để Render ping và thấy port mở
@app.route('/')
def home():
    return "Bot is running successfully!"

# Xử lý lệnh /start trên Telegram
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_name = message.from_user.first_name or "bạn"
    bot.reply_to(message, f"Xin chào {user_name}! Bot đã hoạt động ngon lành trên Render rồi nhé 🚀")

# Xử lý lệnh /help
@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "Danh sách lệnh:\n/start - Bắt đầu\n/help - Hướng dẫn")

# Phản hồi lại tin nhắn văn bản thông thường
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    bot.reply_to(message, f"Bạn vừa nói: {message.text}")

# Hàm chạy bot Telegram ngầm
def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    # Khởi động luồng chạy bot Telegram riêng biệt
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Lấy cổng port do Render cấp tự động (hoặc mặc định là 10000)
    port = int(os.environ.get("PORT", 10000))
    
    # Chạy Flask web server để qua mặt lỗi "No open ports detected" của Render
    app.run(host='0.0.0.0', port=port)
