#server.py
from flask import Flask, request, jsonify # ✅
from flask_cors import CORS
import requests
import base64
import io
import json
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

# ******************************
# ⚠️ المتغيرات الأساسية (عليك تحديثها لاحقاً)
# ******************************
BOT_TOKEN = "8364414600:AAGB1lQRrjoc_9KGL_OVvlwWXMF7n8PXVZg" 
# رابط موقع Vercel (لا يتغير)
WEBAPP_URL = "https://telegram-draw-webappsendtogroup.vercel.app" 
# الرابط الذي ستحصل عليه من Render بعد النشر
# سيتم تحديثه تلقائياً عند النشر، لكن يمكنك استخدام متغير بيئة إذا أردت
RENDER_WEBHOOK_URL = "https://api.telegram.org/bot8364414600:AAGB1lQRrjoc_9KGL_OVvlwWXMF7n8PXVZg/setWebhook?url=https://telegram-draw-api-bot.onrender.com/webhook" 

# ******************************
# 🌐 تهيئة Flask
# ******************************
app = Flask(__name__)
# تفعيل CORS: ضروري للسماح لـ Vercel (الموقع) بإرسال طلبات POST إلى خادم Flask
# نحدد المصدر بشكل صريح لضمان الأمان
CORS(app, resources={r"/api/*": {"origins": WEBAPP_URL}})

# إعداد logging لـ Flask
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ******************************
# 🎨 نقطة نهاية WebApp API (لإرسال الصورة)
# ******************************
@app.route("/api/send_image", methods=["POST"])
def send_image():
    try:
        data = request.get_json()
        chat_id = data.get("chat_id")
        image_data = data.get("image_data") 

        if not chat_id or not image_data:
            return jsonify({"ok": False, "error": "Missing chat_id or image_data"}), 400

        # تحويل بيانات الصورة Base64 إلى بايت (ملف)
        image_bytes = base64.b64decode(image_data)
        
        # استخدام io.BytesIO لإنشاء كائن يشبه الملف
        files = {'photo': ('drawing.jpg', io.BytesIO(image_bytes), 'image/jpeg')}
        
        # إعداد طلب API لإرسال الصورة (sendPhoto)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        
        # إرسال طلب POST إلى تليجرام
        res = requests.post(url, data={"chat_id": chat_id}, files=files)
        
        if res.status_code == 200 and res.json().get("ok"):
            return jsonify({"ok": True, "message": "Image sent successfully"}), 200
        else:
            logger.error(f"Telegram API Error: {res.text}")
            return jsonify({"ok": False, "error": "Telegram API Error", "details": res.text}), 500

    except Exception as e:
        logger.error(f"Internal Server Error: {e}")
        return jsonify({"ok": False, "error": f"Internal Server Error: {str(e)}"}), 500

# ******************************
# 🤖 وظيفة البوت Webhook Handlers
# ******************************

async def handle_start_command(update: Update):
    """يعالج أمر /draw."""
    if not update.message or not update.effective_chat:
        return
        
    chat_id = update.effective_chat.id
    # بناء الرابط مع تمرير الـ chat_id كمعامل استعلام
    link = f"{WEBAPP_URL}?chat_id={chat_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 افتح لوحة الرسم", url=link)]
    ])

    await update.message.reply_text(
        "افتح لوحة الرسم وارسم ما تريد، ثم اضغط حفظ لإرسالها هنا:",
        reply_markup=keyboard
    )

@app.route("/webhook", methods=["POST"])
async def webhook_handler():
    """نقطة نهاية لاستقبال تحديثات Telegram."""
    try:
        # قراءة التحديث من الطلب
        data = request.get_json(force=True)
        update = Update.de_json(data, None)

        # تجهيز التطبيق لمعالجة التحديث
        # ملاحظة: Telegram API for Python لا يتطلب ContextTypes هنا
        if update.message and update.message.text and update.message.text.startswith('/draw'):
            await handle_start_command(update)

        return jsonify({"status": "ok"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ******************************
# ⚙️ وظيفة لتعيين Webhook (يتم تشغيلها مرة واحدة)
# ******************************

def set_webhook(url):
    """يرسل طلب إلى Telegram لتعيين Webhook."""
    try:
        # تأكد من أن الرابط هو رابط مشروع Render الفعلي متبوعاً بـ /webhook
        webhook_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={url}"
        response = requests.get(webhook_url)
        
        if response.status_code == 200 and response.json().get("ok"):
            logger.info("✅ Webhook set successfully.")
            logger.info(f"Telegram response: {response.text}")
            return True
        else:
            logger.error("❌ Failed to set Webhook.")
            logger.error(f"Telegram response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False

# ******************************
# 🚀 تشغيل الخادم
# ******************************

if __name__ == "__main__":
    # تشغيل Flask على خادم محلي فقط لأغراض التطوير
    logger.info("Running locally. Webhook needs to be set manually.")
    app.run(host="0.0.0.0", port=5000)