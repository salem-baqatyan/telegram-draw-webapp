#!/usr/bin/env python3
import logging
import json
import base64
import re
import requests
import io


from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ====== CONFIG ======
TOKEN = "8364414600:AAGB1lQRrjoc_9KGLvOVvlwWXMF7n8PXVZg"
WEBAPP_URL = "https://salem-baqatyan.github.io/telegram-draw-webapp/"
# ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# نخزن آخر chat_id للمستخدم حتى نعرف لمن نرسل الصورة القادمة
last_user_chat_id = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    last_user_chat_id[user_id] = chat_id
    
    print(f"DEBUG: /start command received. User {user_id} chat {chat_id} saved.")

    keyboard = [
        [KeyboardButton("🎨 فتح لوحة الرسم", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("اضغط زر فتح لوحة الرسم:", reply_markup=markup)


# ... (بعد دالة start)

async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 🟢 الحالة 1: استقبال الصورة بصيغة Base64 مباشرة
    # match_base64 = re.search(r"^DOODLE_BASE64::(.+)", data, re.DOTALL)
    # if match_base64:
    #     print(f"\n--- DEBUG: Received DOODLE_BASE64 from user {user_id} ---")
    #     try:
    #         img_data = base64.b64decode(match_base64.group(1))
    #         image_file = io.BytesIO(img_data)
    #         image_file.name = f"doodle_{user_id}.jpeg"

    #         await context.bot.send_photo(
    #             chat_id=chat_id,
    #             photo=InputFile(image_file),
    #             caption="🖼️ رسمتك تم رفعها مباشرة عبر Telegram!"
    #         )
    #         print("DEBUG: Photo uploaded directly to Telegram API.")

    #     except Exception as e:
    #         logger.error(f"Error decoding base64 image: {e}")
    #         await update.effective_message.reply_text(f"❌ خطأ أثناء فك تشفير الصورة: {e}")
    #     return

    # 🔵 الحالة 2: إذا كانت DOODLE_URL كما في الكود السابق (احتياطي)
    match_url = re.search(r"^DOODLE_URL::(.+)", data, re.DOTALL)
    if match_url:
        image_url = match_url.group(1)
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_url,
            caption="🖼️ رسمتك من ImgBB!"
        )
        print("DEBUG: Sent photo via URL fallback.")
        return

    # 🔴 الحالة الافتراضية
    await update.effective_message.reply_text("تم استلام بيانات مجهولة من WebApp.")


# ---------------------------
# 🚀 التشغيل (بدون تغيير عن الكود السابق)
# ---------------------------
def main():
    global application
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    logger.info("Bot running with polling...")
    print("\n\n--- BOT STARTED. READY for DOODLE_URL. ---")
    application.run_polling(poll_interval=1.0)


if __name__ == "__main__":
    main()