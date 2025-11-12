#bot.py
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
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ====== CONFIG ======
TOKEN = "8364414600:AAFKCVNSd-_2hmcOVjYIZB1-9NOkz394z5o"
WEBAPP_URL = "https://telegram-draw-webapp.vercel.app/"
# ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# نخزن آخر chat_id للمستخدم حتى نعرف لمن نرسل الصورة القادمة
last_user_chat_id = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    chat_type = update.message.chat.type
    
    # إذا كان هناك معامل في الأمر (قادم من deep link)
    if context.args and len(context.args) > 0:
        group_chat_id = context.args[0]
        last_user_chat_id[user_id] = int(group_chat_id)
        print(f"DEBUG: User {user_id} came from group {group_chat_id}")
    else:
        last_user_chat_id[user_id] = chat_id
    
    print(f"DEBUG: /start command received. User {user_id} chat {chat_id} type {chat_type} saved.")

    # إذا كانت محادثة خاصة (private)
    if chat_type == "private":
        keyboard = [
            [KeyboardButton("🎨 فتح لوحة الرسم", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("اضغط زر فتح لوحة الرسم:", reply_markup=markup)
    
    # إذا كانت مجموعة أو قناة
    else:
        bot_username = (await context.bot.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start={chat_id}"
        
        keyboard = [
            [InlineKeyboardButton("🎨 ابدأ الرسم في الخاص", url=deep_link)]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "اضغط الزر أدناه للانتقال للخاص وبدء الرسم.\nسيتم إرسال رسمتك لهذه المجموعة تلقائياً! 🎨",
            reply_markup=markup
        )



async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user = update.effective_user
    
    # الحصول على chat_id المحفوظ (المجموعة أو الخاص)
    target_chat_id = last_user_chat_id.get(user_id, update.effective_chat.id)

    match_url = re.search(r"^DOODLE_URL::(.+)", data, re.DOTALL)
    if match_url:
        image_url = match_url.group(1)
        
        # إرسال الصورة للمجموعة أو الخاص مع منشن للرسام
        # استخدام mention بصيغة HTML
        user_mention = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
        caption = f"🎨 رسمة بواسطة: {user_mention}"
        
        await context.bot.send_photo(
            chat_id=target_chat_id,
            photo=image_url,
            caption=caption,
            parse_mode='HTML'
        )
        
        # إرسال رسالة تأكيد للمستخدم في الخاص
        if target_chat_id != update.effective_chat.id:
            await update.effective_message.reply_text("✅ تم إرسال رسمتك للمجموعة بنجاح!")
        
        print(f"DEBUG: Sent photo to chat {target_chat_id} with mention for user {user_id}")
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