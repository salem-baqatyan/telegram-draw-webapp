from flask import Flask, request, jsonify # ✅
from flask_cors import CORS # إذا كنت تستخدم CORS
import requests
import base64
import io

# ⚠️ تم تحديث هذه القيمة بناءً على طلبك
BOT_TOKEN = "8364414600:AAGB1lQRrjoc_9KGL_OVvlwWXMF7n8PXVZg" 

app = Flask(__name__)
# تفعيل CORS: ضروري للسماح لـ Vercel (الموقع) بإرسال طلبات POST إلى خادم Flask
CORS(app) 

@app.route("/api/send_image", methods=["POST"])
def send_image():
    try:
        data = request.get_json()
        chat_id = data.get("chat_id")
        image_data = data.get("image_data") # الصورة مشفرة بـ Base64

        if not chat_id or not image_data:
            return jsonify({"ok": False, "error": "Missing chat_id or image_data"}), 400

        # تحويل بيانات الصورة Base64 إلى بايت (ملف)
        # image_data هو جزء Base64 النظيف فقط
        image_bytes = base64.b64decode(image_data)
        
        # استخدام io.BytesIO لإنشاء كائن يشبه الملف
        files = {'photo': ('drawing.jpg', io.BytesIO(image_bytes), 'image/jpeg')}
        
        # إعداد طلب API لإرسال الصورة (sendPhoto)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        
        # إرسال طلب POST إلى تليجرام
        res = requests.post(url, data={"chat_id": chat_id}, files=files)
        
        # فحص استجابة تليجرام
        if res.status_code == 200 and res.json().get("ok"):
            return jsonify({"ok": True, "message": "Image sent successfully"}), 200
        else:
            print(f"Telegram API Error: {res.text}")
            return jsonify({"ok": False, "error": "Telegram API Error", "details": res.text}), 500

    except Exception as e:
        print(f"Internal Server Error: {e}")
        return jsonify({"ok": False, "error": f"Internal Server Error: {str(e)}"}), 500

# if __name__ == "__main__":
#     # عند التشغيل المحلي، استخدم هذا الأمر. في الاستضافة الفعلية، يفضل استخدام خادم إنتاج مثل Gunicorn
#     app.run(host="0.0.0.0", port=5000)