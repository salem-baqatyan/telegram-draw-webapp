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
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
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
selected_words_history = {}

# 🚨 تغيير: سنخزن آخر chat_id للمجموعة التي بدأ فيها المستخدم اللعبة
# المفتاح هو user_id والقيمة هي group_chat_id
last_user_group_chat_id = {}


# ----------------------------------------------------
# 🚀 دالة /start المُعدَّلة: التعامل مع الخاص والمجموعة
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat_id
    chat_type = update.effective_chat.type

    print(f"DEBUG: /start received. User {user_id} in chat {chat_id} ({chat_type}).")

    # 1. إذا كان الأمر في مجموعة (Group/Supergroup)
    if chat_type in ["group", "supergroup"]:
        # حفظ آخر group_chat_id لهذا المستخدم
        last_user_group_chat_id[user_id] = chat_id

        # 🚨 إنشاء زر "اذهب إلى خاص البوت"
        markup_group = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                text="اذهب الى خاص البوت", 
                url=f"https://t.me/{context.bot.username}?start=game"
            )]
        ])
        
        # 🚨 الرسالة في القروب
        await update.message.reply_text(
            "أهلاً بك في **لعبة ارسم وخمن**! 🎨", 
            reply_markup=markup_group,
            parse_mode="Markdown"
        )
        
        # 🚨 إرسال الرسالة الثانية في الخاص (نستدعي start مرة أخرى ولكن بشكل آمن)
        # نحتاج إلى اختيار الكلمات وإرسالها إلى الخاص الآن
        
        # 1. اختيار 3 كلمات عشوائية غير مكررة
        history = selected_words_history.get(user_id, [])
        available_words = [word for word in WORD_LIST if word not in history]
        if len(available_words) < 3:
            selected_words_history[user_id] = []
            available_words = WORD_LIST
            print("DEBUG: Word history reset for user.")

        chosen_words = random.sample(available_words, 3)
        history.extend(chosen_words)
        selected_words_history[user_id] = history
        
        # 2. إنشاء أزرار Web App جديدة لكل كلمة
        keyboard_layout_private = []
        for word in chosen_words:
            word_url_encoded = requests.utils.quote(word)
            webapp_url_with_word = f"{WEBAPP_URL}?start_word={word_url_encoded}"

            keyboard_layout_private.append([
                InlineKeyboardButton(
                    text=word, 
                    web_app=WebAppInfo(url=webapp_url_with_word)
                )
            ])
        markup_private = InlineKeyboardMarkup(keyboard_layout_private)

        # 3. إرسال الرسالة في الخاص (باستخدام user_id)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="اختر احد هذه الكلمات لكي ترسمها: 👇",
                reply_markup=markup_private
            )
        except Exception as e:
            # إذا كان البوت غير قادر على إرسال رسالة في الخاص
            await update.message.reply_text("⚠️ لم أستطع إرسال الكلمات لك في الخاص. يرجى التأكد من أنك بدأت البوت في الخاص أولاً.")
            logger.error(f"Failed to send private message to {user_id}: {e}")
            
    # 2. إذا كان الأمر في الخاص (Private)
    elif chat_type == "private":
        # إذا كان المستخدم في الخاص، ولا توجد كلمات معلقة للاختيار (أي لم يبدأ من مجموعة)، لا تفعل شيئًا أو يمكنك هنا عرض رسالة ترحيب عادية.
        await update.message.reply_text(
            "مرحباً! لاستخدام اللعبة، ابدأ الأمر `/start` في أي مجموعة تحتوي على هذا البوت.",
        )


# ----------------------------------------------------
# 🖼️ دالة webapp_data_handler المُعدَّلة: الإرسال إلى المجموعة
# ----------------------------------------------------
async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name

    # 🚨 التغيير: استخدام نمط جديد لفك ترميز URL والكلمة
    match_data = re.search(r"^DOODLE_DATA::(.+)::(.+)", data, re.DOTALL)
    
    # إذا لم يتم العثور على التنسيق الجديد، نعود للتحقق من التنسيق القديم (للسلامة)
    if not match_data:
        match_url = re.search(r"^DOODLE_URL::(.+)", data, re.DOTALL)
        if match_url:
            image_url = match_url.group(1)
            caption = f"🖼️ رسمتك من ImgBB!"
        else:
            await update.effective_message.reply_text("تم استلام بيانات مجهولة من WebApp.")
            return
            
        drawn_word = "غير معروفة" # الكلمة غير موجودة في التنسيق القديم

    else:
        # استخراج رابط الصورة والكلمة المستهدفة من التنسيق الجديد
        image_url = match_data.group(1)
        drawn_word_encoded = match_data.group(2)
        
        # 🌟 فك ترميز الكلمة المستهدفة (لأنها تأتي مشفرة من WebApp)
        # requests.utils.unquote تعمل بشكل جيد لفك ترميز الـ URL
        drawn_word = requests.utils.unquote(drawn_word_encoded)
        
        caption = f"🎨 رسم جديد من @{user_name}!\n\n**الكلمة:** {drawn_word} ✍️\n\nهل يمكنك تخمين ما رسمه؟"

        # -----------------------------------------------------------------
    # (المنطق المشترك: تحديد المجموعة والإرسال)
    # -----------------------------------------------------------------
    
    target_chat_id = last_user_group_chat_id.get(user_id)
    
    if not target_chat_id:
        await update.effective_message.reply_text("⚠️ فشل الإرسال: لم يتم العثور على مجموعة نشطة بدأت فيها اللعبة.")
        return

    # إرسال الصورة إلى المجموعة المستهدفة
    try:
        await context.bot.send_photo(
            chat_id=target_chat_id,
            photo=image_url,
            caption=caption, # استخدام التسمية التوضيحية التي تحتوي على الكلمة
            parse_mode="Markdown"
        )
        # إرسال رسالة تأكيد في الخاص للمستخدم
        await update.effective_message.reply_text(f"✅ تم إرسال رسمتك ({drawn_word}) إلى المجموعة بنجاح!")
        print("DEBUG: Sent photo successfully to the group.")

    except Exception as e:
        await update.effective_message.reply_text("❌ حدث خطأ أثناء إرسال الصورة إلى المجموعة. ربما تمت إزالة البوت منها؟")
        logger.error(f"Failed to send photo to group {target_chat_id}: {e}")

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