#!/usr/bin/env python3
import logging
import json
import base64
import re
import requests
import io
import random

from telegram import (
    Update,
    # 🚨 تغيير: سنستخدم InlineKeyboardMarkup بدلاً من ReplyKeyboardMarkup
    # ReplyKeyboardMarkup, 
    # KeyboardButton, 
    InlineKeyboardMarkup, # 🌟 جديد
    InlineKeyboardButton, # 🌟 جديد
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

last_user_group_chat_id = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user_id = update.message.from_user.id
    
    # 🔴 التعديل الأول: التحقق من أن الدردشة هي مجموعة
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("👋 مرحباً! للبدء، أضفني إلى مجموعة واستخدم الأمر /start هناك.")
        return

    # 🟢 حفظ chat_id المجموعة لغرض الإرسال لاحقاً
    group_chat_id = chat.id
    last_user_group_chat_id[user_id] = group_chat_id
    
    print(f"DEBUG: /start received. User {user_id} in chat {group_chat_id} ({chat.type}).")
    print(f"DEBUG: Saved group chat ID {group_chat_id} for user {user_id}")

    # 🔴 التعديل الثاني: إنشاء زر موحد لفتح Web App بدون تحديد كلمة
    # (الكلمة سيتم اختيارها لاحقاً من داخل الـ Web App)
    keyboard_layout = [
        [
            InlineKeyboardButton(
                text="🎨 ابدأ الرسم! (اختر الكلمة داخل اللوحة)", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard_layout)
    
    await update.message.reply_text(
        "اضغط على الزر أدناه لفتح لوحة الرسم واختيار كلمة اللعبة:", 
        reply_markup=markup
    )


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 🌟 التعديل الثالث: منطق استخراج الكلمة والرابط من الـ Web App
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    
    # 🚨 البادئة الجديدة: DOODLE_DATA::[URL]::[WORD]
    match_data = re.search(r"^DOODLE_DATA::(.+)::(.+)", data, re.DOTALL)
    
    if match_data:
        image_url = match_data.group(1)
        # الكلمة مشفرة لضمان التعامل مع الحروف العربية
        drawn_word_encoded = match_data.group(2) 
        drawn_word = requests.utils.unquote(drawn_word_encoded) # فك التشفير
        
        caption = f"🎨 رسم جديد من @{user_name}!\n\n**الكلمة:** {drawn_word} ✍️\n\nتخميناتكم؟"
        
        # 🔴 التعديل الرابع: إرسال الصورة إلى المجموعة
        # استخدام chat_id الذي تم حفظه عند استخدام /start
        target_chat_id = last_user_group_chat_id.get(user_id)
        
        if not target_chat_id:
            await update.effective_message.reply_text(
                "⚠️ فشل الإرسال: لم يتم العثور على مجموعة نشطة بدأت فيها اللعبة. يرجى استخدام /start في المجموعة أولاً."
            )
            return

        # إرسال الصورة إلى المجموعة
        try:
            await context.bot.send_photo(
                chat_id=target_chat_id,
                photo=image_url,
                caption=caption,
                parse_mode="Markdown"
            )
            # إرسال رسالة تأكيد في الخاص للمستخدم (الذي ضغط على زر الحفظ)
            await update.effective_message.reply_text(f"✅ تم إرسال رسمتك ({drawn_word}) إلى المجموعة بنجاح!")
            print(f"DEBUG: Photo sent successfully to group {target_chat_id}.")

        except Exception as e:
            logger.error(f"FATAL ERROR: Failed to send photo to group {target_chat_id}. Error: {e}")
            await update.effective_message.reply_text(
                f"❌ حدث خطأ أثناء إرسال الصورة إلى المجموعة. تأكد أن البوت مشرف ولديه صلاحية نشر الوسائط. (الخطأ: {e.args[0] if e.args else 'غير معروف'})"
            )

    else:
        # الحالة الافتراضية
        await update.effective_message.reply_text("تم استلام بيانات مجهولة من WebApp. (البيانات: " + data[:50] + "...)")

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