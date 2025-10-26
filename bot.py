#!/usr/bin/env python3
import logging
import json
import base64
import re
import requests
import io
import random # 🌟 جديد: لاستخدام العشوائية في اختيار الكلمات

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
WEBAPP_URL = "https://telegram-draw-webapp.vercel.app/"
# ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🌟 جديد: قائمة الكلمات
WORD_LIST = [
    "شجرة", "قارب", "طائرة", "جبل", "قلم", 
    "كتاب", "هاتف", "سيارة", "ساعة", "نظارة", 
    "وردة", "شمس", "قمر", "مطر", "كمبيوتر"
]

# 🌟 جديد: لتخزين الكلمات التي تم اختيارها مسبقاً لكل مستخدم (حتى لا يتم تكرارها مؤقتاً)
# يمكن توسيع هذا ليصبح قاعدة بيانات إذا احتجت إلى تخزين دائم
selected_words_history = {}

last_user_chat_id = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    last_user_chat_id[user_id] = chat_id
    
    print(f"DEBUG: /start command received. User {user_id} chat {chat_id} saved.")

    # 🌟 جديد: اختيار 3 كلمات عشوائية غير مكررة
    
    # الحصول على الكلمات المستخدمة مؤقتاً لهذا المستخدم
    history = selected_words_history.get(user_id, [])
    
    # الكلمات المتاحة للاختيار
    available_words = [word for word in WORD_LIST if word not in history]

    if len(available_words) < 3:
        # إذا لم يكن هناك 3 كلمات متاحة، نبدأ القائمة من جديد (نمحو السجل)
        selected_words_history[user_id] = []
        available_words = WORD_LIST
        print("DEBUG: Word history reset for user.")

    # اختيار 3 كلمات عشوائياً
    chosen_words = random.sample(available_words, 3)
    
    # تحديث سجل الكلمات المستخدمة
    history.extend(chosen_words)
    selected_words_history[user_id] = history
    
    # 🌟 إنشاء أزرار Web App جديدة لكل كلمة
    keyboard = []
    for word in chosen_words:
        # 🚨 النقطة الرئيسية: نمرر الكلمة كمعامل (parameter) في رابط WebApp
        # يجب ترميز الكلمة (URL-encode) إذا كانت تحتوي على مسافات أو رموز خاصة، لكن للكلمات العربية البسيطة لا بأس
        word_url_encoded = requests.utils.quote(word)
        webapp_url_with_word = f"{WEBAPP_URL}?start_word={word_url_encoded}"

        # يتم استخدام زر 'WebAppInfo' هنا أيضاً، ولكن الزر نفسه يحمل الكلمة كعنوان
        keyboard.append([
            KeyboardButton(word, web_app=WebAppInfo(url=webapp_url_with_word))
        ])

    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # 🌟 إرسال الرسالة المطلوبة
    await update.message.reply_text(
        "اختر احد هذه الكلمات لكي ترسمها:", 
        reply_markup=markup
    )


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (بقية الدالة webapp_data_handler لا تحتاج لتعديل)
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    match_url = re.search(r"^DOODLE_URL::(.+)", data, re.DOTALL)
    if match_url:
        image_url = match_url.group(1)
        # 🌟 ملاحظة: يمكنك هنا إضافة الكلمة المرسومة في الـ Caption إذا كانت البيانات متوفرة
        # لكن حالياً، الكود يرسل الصورة فقط.
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