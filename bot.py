import os
import telebot

# Lấy token an toàn từ biến môi trường của Render
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError("Lỗi: Chưa thiết lập biến môi trường BOT_TOKEN trên Render hoặc giá trị bị trống!")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_name = message.from_user.first_name or "bạn"
    bot.reply_to(message, f"Xin chào {user_name}! Bot của bạn đã hoạt động mượt mà trên Render rồi nhé 🚀")

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "Danh sách lệnh hỗ trợ:\n/start - Khởi động bot\n/help - Xem hướng dẫn")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Trả lời lại bất kỳ tin nhắn nào người dùng gửi tới
    bot.reply_to(message, f"Bạn vừa nói: {message.text}")

if __name__ == '__main__':
    print("Bot đang khởi động và bắt đầu lắng nghe...")
    # Dùng infinity_polling để bot tự động kết nối lại khi mất mạng
    bot.infinity_polling()
