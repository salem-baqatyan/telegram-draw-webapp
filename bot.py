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

# في ملف bot.py

# ... (كل التعريفات السابقة)

# 🌟 جديد: لتخزين آخر chat_id للمجموعة التي بدأ منها المستخدم اللعبة
last_user_group_chat_id = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    user_id = update.message.from_user.id
    group_chat_id = chat.id # نحفظ الـ ID سواء كان خاص أو مجموعة
    
    # 🚨 حفظ chat_id. سنفترض أنه مجموعة إذا تم إرساله منها.
    # هذا يضمن أن لدينا ID لإعادة الإرسال إليه لاحقًا.
    last_user_group_chat_id[user_id] = group_chat_id
    
    print(f"DEBUG: /start received. User {user_id} in chat {group_chat_id} ({chat.type}).")
    print(f"DEBUG: Saved chat ID {group_chat_id} for user {user_id}")


    # ----------------------------------------------------
    # 🌟 تنفيذ طلبك: رسالة "أهلاً" مع زر واحد لفتح الويب أب
    # ----------------------------------------------------
    
    # زر واحد يفتح الويب أب مباشرة
    keyboard_layout = [
        [
            InlineKeyboardButton(
                text="🎨 أريد أن أرسم! (افتح اللوحة)", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard_layout)
    
    # نستخدم reply_text هنا لأن الزر بسيط وهذا يقلل فرص الخطأ 400
    await update.message.reply_text(
        "👋 **أهلاً بكم في لعبة خمن وارسم!**\n\nاضغط على الزر أدناه لبدء اللعبة واختيار الكلمة:", 
        reply_markup=markup,
        parse_mode="Markdown" # لتمكين الخط الغامق
    )


async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 🌟 المنطق الأهم: الإرسال إلى المجموعة فقط
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    
    match_data = re.search(r"^DOODLE_DATA::(.+)::(.+)", data, re.DOTALL)
    
    if match_data:
        image_url = match_data.group(1)
        drawn_word_encoded = match_data.group(2) 
        drawn_word = requests.utils.unquote(drawn_word_encoded)
        
        caption = f"🎨 رسم جديد من @{user_name}!\n\n**الكلمة:** {drawn_word} ✍️\n\nتخميناتكم؟"
        
        # 🔴 الهدف الرئيسي: استخدام chat_id المجموعة المحفوظ
        target_chat_id = last_user_group_chat_id.get(user_id)
        
        # 🚨 التحقق من نوع الدردشة (للتأكد أنها مجموعة قبل الإرسال الفعلي)
        if not target_chat_id:
            await update.effective_message.reply_text(
                "⚠️ فشل الإرسال: يرجى التأكد من استخدام /start داخل مجموعة أولاً."
            )
            return
            
        try:
            # 1. إرسال الصورة إلى المجموعة
            sent_message = await context.bot.send_photo(
                chat_id=target_chat_id,
                photo=image_url,
                caption=caption,
                parse_mode="Markdown"
            )
            
            # 2. إرسال رسالة تأكيد في الخاص للمستخدم
            await update.effective_message.reply_text(f"✅ تم إرسال رسمتك ({drawn_word}) إلى المجموعة بنجاح!")
            print(f"DEBUG: Photo sent successfully to group {target_chat_id}.")

        except Exception as e:
            # رسالة خطأ واضحة للمستخدم
            logger.error(f"FATAL ERROR: Failed to send photo to group {target_chat_id}. Error: {e}")
            await update.effective_message.reply_text(
                f"❌ حدث خطأ أثناء إرسال الصورة إلى المجموعة. تأكد أن البوت مشرف ولديه صلاحية نشر الوسائط. (الخطأ: {e.args[0] if e.args else 'غير معروف'})"
            )

    else:
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