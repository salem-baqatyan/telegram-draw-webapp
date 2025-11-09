#!/usr/bin/env python3
import logging
import re
import asyncio

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    Message,
)

# ====== CONFIG ======
# يجب استخدام متغير بيئة للتوكن في الإنتاج، لكننا نستخدم الثابت هنا للمثال.
TOKEN = "8364414600:AAGB1lQRrjoc_9KGLvOVvlwWXMF7n8PXVZg"
WEBAPP_URL = "https://telegram-draw-webappsendtogroup.vercel.app/"
# ====================

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# نخزن آخر chat_id للمستخدم حتى نعرف لمن نرسل الصورة القادمة (اختياري في Aiogram)
# في Aiogram، يمكننا الاعتماد على chat_id في الرسائل القادمة بشكل مباشر.
# لكن سنحتفظ بها لتقليد المنطق الأصلي، مع العلم أننا نستخدمها مباشرة في webapp_data_handler
last_user_chat_id = {}


# 🎨 معالج أمر /start
async def start_command(message: Message):
    """
    يرسل رسالة الترحيب مع زر WebApp.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # حفظ آخر chat_id (للتوافق مع المنطق الأصلي)
    last_user_chat_id[user_id] = chat_id
    
    logger.info(f"[/start] command received. User {user_id} chat {chat_id} saved.")

    # إنشاء زر WebApp
    keyboard = [
        [
            KeyboardButton(
                text="🎨 فتح لوحة الرسم",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]
    
    markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False  # يمكن تعديلها حسب الحاجة
    )
    
    await message.reply(
        text="اضغط زر فتح لوحة الرسم:",
        reply_markup=markup
    )


# 🖼️ معالج بيانات WebApp
async def webapp_data_handler(message: Message):
    """
    يستقبل البيانات المرسلة من WebApp بعد إغلاقها.
    """
    # الوصول إلى بيانات WebApp
    data = message.web_app_data.data
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    logger.info(f"[WebApp Data] Received data from user {user_id} in chat {chat_id}")

    # محاولة مطابقة نمط URL
    match_url = re.search(r"^DOODLE_URL::(.+)", data, re.DOTALL)
    
    if match_url:
        image_url = match_url.group(1)
        
        # إرسال الصورة باستخدام URL
        await message.bot.send_photo(
            chat_id=chat_id,
            photo=image_url,
            caption="🖼️ رسمتك من ImgBB!"
        )
        logger.info("DEBUG: Sent photo via URL fallback (Aiogram).")
        return

    # 🔴 الحالة الافتراضية
    await message.reply(text="تم استلام بيانات مجهولة من WebApp.")


# 🚀 الدالة الرئيسية للتشغيل
async def main():
    # إنشاء البوت والـ Dispatcher
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    
    # تسجيل المعالجات
    # F.text == "/start" هو بديل CommandHandler في Aiogram
    dp.message.register(start_command, F.text == "/start")
    
    # F.web_app_data هي مرشح مدمج للرسائل التي تحتوي على بيانات WebApp
    dp.message.register(webapp_data_handler, F.web_app_data)
    
    logger.info("Bot running with polling (Aiogram 3)...")
    print("\n\n--- BOT STARTED. READY for DOODLE_URL. ---")
    
    # بدء التشغيل بالـ polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # تشغيل الدالة الرئيسية بشكل غير متزامن
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")