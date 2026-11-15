  # Xử lý khi người dùng gửi video để kiểm tra lỗi
  @bot.message_handler(content_types=["video", "document"])
  def handle_video_check(message: telebot.types.Message) -> None:
    sent_msg = bot.reply_to(message, "🔍 Bot đang phân tích video, chờ chút nha...")
    
    video_path = "downloads"
    os.makedirs(video_path, exist_ok=True)
    
    local_video_path = None
    video_file = None

    try:
      # Hỗ trợ cả gửi dạng video trực tiếp hoặc gửi dạng tệp (document)
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
      
      # Tải lên Google GenAI File API
      video_file = genai.upload_file(path=local_video_path)
      
      # Đợi xử lý file trên server Google
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

    # Dọn dẹp file rác
    try:
      if video_file:
        genai.delete_file(video_file.name)
      if local_video_path and os.path.exists(local_video_path):
        os.remove(local_video_path)
    except Exception:
      pass
