import logging
import os
import re
from pathlib import Path

import telebot
from dotenv import load_dotenv


# Giá trị "video" có thể là URL HTTPS trỏ thẳng tới MP4 hoặc Telegram file_id.
# Các URL dưới đây là video mẫu công khai; thay bằng video của bạn khi cần.
VIDEO_DATABASE = {
    "flower_demo": {
        "video": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "caption": "Video mẫu: hoa",
    },
    "sintel_demo": {
        "video": "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "caption": "Video mẫu: Sintel",
    },
    "bunny_demo": {
        "video": "https://media.w3.org/2010/05/bunny/trailer.mp4",
        "caption": "Video mẫu: Big Buck Bunny",
    },
    "album_01": {
        "path": "../attached_assets/GTok-5ABBE918-3444-49B5-A644-F3C6F8CF0670_1793356313012.mp4",
        "caption": "Album 01",
    },
    "album_02": {
        "paths": [
            "../attached_assets/IMG_6443_1793361727906.MP4",
            "../attached_assets/IMG_6444_1793361746455.MP4",
            "../attached_assets/IMG_6445_1793361888871.MP4",
        ],
        "caption": "Album 02",
    },
}

PAYLOAD_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram-video-bot")


def build_bot() -> telebot.TeleBot:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Chưa cấu hình BOT_TOKEN. Hãy thêm token trong Replit Secrets "
            "hoặc trong file .env khi chạy trên máy cá nhân."
        )

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=["start"])
    def handle_start(message: telebot.types.Message) -> None:
        parts = (message.text or "").strip().split(maxsplit=1)
        if len(parts) == 1:
            bot.reply_to(
                message,
                "Xin chào! Hãy mở link dạng "
                "https://t.me/<ten_bot>?start=album_01 để nhận video.",
            )
            return

        code = parts[1].strip()
        if not PAYLOAD_PATTERN.fullmatch(code):
            bot.reply_to(message, "Mã video không hợp lệ.")
            return

        video = VIDEO_DATABASE.get(code)
        if video is None:
            bot.reply_to(message, "Không tìm thấy video cho mã này.")
            return

        logger.info("Nhận lệnh /start cho mã video %s.", code)
        video_source = video.get("video", "").strip()
        local_paths = video.get("paths")
        if local_paths is None:
            local_path = video.get("path", "").strip()
            local_paths = [local_path] if local_path else []

        if not video_source and not local_paths:
            bot.reply_to(
                message,
                "Video này chưa được cấu hình URL, file_id hoặc đường dẫn tệp. "
                "Hãy xem hướng dẫn trong README.md.",
            )
            return

        try:
            sent_count = 0
            if local_paths:
                if len(local_paths) > 1:
                    bot.reply_to(
                        message,
                        f"Đang gửi {len(local_paths)} video; quá trình có thể mất một lúc.",
                    )
                for index, local_path in enumerate(local_paths, start=1):
                    logger.info(
                        "Đang gửi video %d/%d cho mã %s.",
                        index,
                        len(local_paths),
                        code,
                    )
                    media_path = (
                        Path(__file__).resolve().parent / local_path
                    ).resolve()
                    caption = video.get("caption") or None
                    if caption and len(local_paths) > 1:
                        caption = f"{caption} · video {index}/{len(local_paths)}"
                    with media_path.open("rb") as video_file:
                        bot.send_video(
                            chat_id=message.chat.id,
                            video=video_file,
                            caption=caption,
                            supports_streaming=True,
                            timeout=300,
                        )
                    sent_count += 1
                logger.info("Đã gửi %d video cho mã %s.", sent_count, code)
            else:
                bot.send_video(
                    chat_id=message.chat.id,
                    video=video_source,
                    caption=video.get("caption") or None,
                    supports_streaming=True,
                    timeout=300,
                )
        except Exception as error:
            error_code = getattr(error, "error_code", None)
            error_description = getattr(error, "description", None)
            if error_description:
                safe_description = str(error_description).replace(
                    token, "[token ẩn]"
                )
                safe_description = re.sub(
                    r"https?://\S+", "[URL ẩn]", safe_description
                )
                safe_description = safe_description[:250]
            else:
                safe_description = "không có"
            logger.error(
                "Không gửi được video (loại lỗi: %s, mã Telegram: %s, "
                "chi tiết: %s).",
                type(error).__name__,
                error_code if error_code is not None else "không có",
                safe_description,
            )
            if sent_count and sent_count < len(local_paths):
                bot.reply_to(
                    message,
                    f"Đã gửi {sent_count}/{len(local_paths)} video; các video còn "
                    "lại chưa gửi được. Hãy thử mở link lại.",
                )
                return
            bot.reply_to(
                message,
                "Bot chưa gửi được video này. Hãy kiểm tra nguồn video và thử lại.",
            )

    @bot.message_handler(content_types=["video"])
    def handle_video_upload(message: telebot.types.Message) -> None:
        # Chỉ trả file_id trong chat riêng, không đăng nó vào nhóm.
        if message.chat.type != "private" or message.video is None:
            return
        bot.reply_to(
            message,
            "file_id của video:\n"
            f"{message.video.file_id}\n\n"
            "Sao chép mã này vào VIDEO_DATABASE trong bot.py.",
        )

    return bot


def main() -> None:
    try:
        bot = build_bot()
    except RuntimeError as error:
        raise SystemExit(str(error)) from None

    try:
        account = bot.get_me()
    except telebot.apihelper.ApiTelegramException as error:
        error_code = getattr(error, "error_code", "unknown")
        logger.error(
            "Telegram từ chối yêu cầu xác thực (mã lỗi: %s). "
            "Hãy kiểm tra BOT_TOKEN trong Replit Secrets.",
            error_code,
        )
        raise SystemExit(1) from None
    except Exception as error:
        logger.error(
            "Không kết nối được Telegram khi xác thực (loại lỗi: %s).",
            type(error).__name__,
        )
        raise SystemExit(1) from None

    logger.info("Đã kết nối Telegram với bot @%s.", account.username)
    try:
        bot.delete_webhook(drop_pending_updates=False)
    except Exception as error:
        logger.error(
            "Không thể xóa webhook để chuyển sang polling "
            "(loại lỗi: %s).",
            type(error).__name__,
        )
        raise SystemExit(1) from None

    logger.info("Đã chuyển bot sang polling; giữ các update đang chờ.")
    logger.info("Bot đang chạy. Nhấn Ctrl+C để dừng.")
    try:
        bot.infinity_polling(skip_pending=False)
    except KeyboardInterrupt:
        logger.info("Đã dừng bot.")


if __name__ == "__main__":
    main()
