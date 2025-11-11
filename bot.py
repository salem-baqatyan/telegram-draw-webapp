# #bot.py
# from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
# from telegram.ext import Application, CommandHandler, ContextTypes

# # ⚠️ تم تحديث هذه القيم بناءً على طلبك
# BOT_TOKEN = "8364414600:AAGB1lQRrjoc_9KGLvOVvlwWXMF7n8PXVZg"
# WEBAPP_URL = "https://telegram-draw-webappsendtogroup.vercel.app" 
# # تأكد أن /draw موجودة في رابط الموقع إذا كان هو المسار الفعلي.
# # إذا كانت صفحة الرسم هي الجذر، استخدم: "https://telegram-draw-webappsendtogroup.vercel.app"
# # سأفترض هنا أن صفحة الرسم هي على المسار /

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     # استخدام effective_chat.id لضمان العمل في المجموعات والقنوات
#     chat_id = update.effective_chat.id
    
#     # بناء الرابط مع تمرير الـ chat_id كمعامل استعلام
#     link = f"{WEBAPP_URL}?chat_id={chat_id}"

#     keyboard = InlineKeyboardMarkup([
#         [InlineKeyboardButton("🎨 افتح لوحة الرسم", url=link)]
#     ])

#     await update.message.reply_text(
#         "افتح لوحة الرسم وارسم ما تريد، ثم اضغط حفظ لإرسالها هنا:",
#         reply_markup=keyboard
#     )

# def main():
#     app = Application.builder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("draw", start))

#     print("✅ Bot running...")
#     app.run_polling(poll_interval=1.0) # استخدام run_polling بدل app.run_polling() إذا كنت تستخدم إصدار أحدث

# if __name__ == "__main__":
#     main()