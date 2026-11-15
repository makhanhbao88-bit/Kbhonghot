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

# ID nhóm VIP của bạn
VIP_CHAT_ID = -1003910292149 

@app.route('/')
def home():
    return "Bot is running successfully!"

# Xử lý lệnh /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Bot đã sẵn sàng! Hãy chuyển tiếp (forward) bất kỳ video nào vào đây, mình sẽ tự động đăng ẩn danh lên nhóm VIP giúp bạn 🚀")

# Bắt tất cả tin nhắn dạng VIDEO được gửi/chuyển tiếp tới bot
@bot.message_handler(content_types=['video'])
def handle_video(message):
    try:
        # Lấy file_id của video (bỏ qua caption cũ và tên người forward)
        video_file_id = message.video.file_id
        
        # Gửi video sang nhóm VIP sạch sẽ, không caption, không tên
        bot.send_video(chat_id=VIP_CHAT_ID, video=video_file_id)
        
        # Phản hồi nhẹ xác nhận cho bạn biết đã xong
        bot.reply_to(message, "Đã đẩy video lên nhóm VIP ẩn danh thành công! ✅")
        
    except Exception as e:
        bot.reply_to(message, f"Có lỗi xảy ra: {e}")

# Hàm chạy bot ngầm bằng luồng riêng
def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Lấy port từ Render (mặc định 10000) để qua mặt lỗi kiểm tra port
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
