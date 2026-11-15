import os
import time
import queue
import threading
import telebot
from flask import Flask

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Lỗi: Chưa thiết lập biến môi trường BOT_TOKEN trên Render!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

VIP_CHAT_ID = -1003910292149 

# Tạo một hàng đợi (queue) chứa các video cần gửi
video_queue = queue.Queue()

@app.route('/')
def home():
    return "Bot is running successfully with Queue!"

@app.route('/status')
def status():
    return f"Số video đang chờ trong hàng đợi: {video_queue.qsize()}"

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "Bot đã sẵn sàng! Tính năng hàng đợi chống spam 429 đã bật. Bạn cứ forward video thoải mái, bot sẽ tự động xếp hàng gửi lần lượt! 🚀")

# Khi nhận được video, ném thẳng vào hàng đợi để xử lý tuần tự
@bot.message_handler(content_types=['video'])
def handle_video(message):
    video_file_id = message.video.file_id
    video_queue.put((message, video_file_id))
    bot.reply_to(message, f"📥 Đã đưa vào hàng đợi! (Còn {video_queue.qsize()} video đang chờ gửi)")

# Luồng chuyên làm nhiệm vụ lôi video từ hàng đợi ra gửi để tránh xung đột và nghẽn mạng
def process_video_queue():
    while True:
        try:
            message, video_file_id = video_queue.get()
            
            success = False
            while not success:
                try:
                    # Gửi video lên nhóm VIP
                    bot.send_video(chat_id=VIP_CHAT_ID, video=video_file_id)
                    bot.reply_to(message, "✅ Đã đẩy 1 video lên nhóm VIP thành công!")
                    success = True
                    time.sleep(1.5) # Nghỉ nhẹ 1.5 giây giữa các video để hạn chế tối đa việc bị dính 429 lần nữa
                    
                except telebot.apihelper.ApiTelegramException as e:
                    if e.error_code == 429:
                        # Lấy thời gian Telegram bắt chờ
                        retry_after = getattr(e, 'result_json', {}).get('parameters', {}).get('retry_after', 10)
                        print(f"⚠️ Bị giới hạn 429! Đang tạm dừng hàng đợi, sẽ thử lại sau {retry_after} giây...")
                        time.sleep(retry_after + 1) # Ngủ đúng thời gian + dư 1 giây cho chắc ăn
                    else:
                        print(f"Lỗi Telegram khác: {e}")
                        bot.reply_to(message, f"❌ Lỗi khi gửi video: {e}")
                        success = True # Thoát vòng lặp để chuyển sang video tiếp theo nếu là lỗi không khắc phục được
                except Exception as ex:
                    print(f"Lỗi không xác định: {ex}")
                    success = True
            
            video_queue.task_done()
            
        except Exception as e:
            print(f"Lỗi trong luồng queue: {e}")
            time.sleep(1)

def run_bot():
    # Khởi động luồng nền xử lý hàng đợi video độc lập
    queue_thread = threading.Thread(target=process_video_queue)
    queue_thread.daemon = True
    queue_thread.start()
    
    bot.infinity_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
