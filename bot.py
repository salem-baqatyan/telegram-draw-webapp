import logging
import json
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
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

# 🎯 تخزين حالة اللعبة: {group_chat_id: {'artist_id': int, 'correct_word': str}}
# ونخزن آخر chat_id للمستخدم (كما كان في السابق)
game_states = {}
last_user_chat_id = {}
scores = {} # {user_id: points}

# ------------------------------------
# 1. معالج بدء اللعبة (في المجموعة)
# ------------------------------------
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # التحقق مما إذا كانت هناك لعبة نشطة بالفعل
    if chat_id in game_states and game_states[chat_id].get('artist_id'):
        await update.message.reply_text("هناك جولة رسم قائمة حالياً. يرجى الانتظار حتى تنتهي أو يتم تخمين الكلمة.")
        return

    bot_username = (await context.bot.get_me()).username
    # نستخدم Deep Link لربط المستخدم بالمجموعة
    deep_link = f"https://t.me/{bot_username}?start={chat_id}"
    
    keyboard = [
        [InlineKeyboardButton("🎨 ابدأ الرسم واختَر الكلمة", url=deep_link)]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "حان دور الرسام! اضغط الزر أدناه للانتقال للخاص وبدء الرسم.\nسيتم إرسال رسمتك لهذه المجموعة 🎨",
        reply_markup=markup
    )

# ------------------------------------
# 2. معالج /start (في الخاص)
# ------------------------------------
async def start_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # إذا كانت محادثة خاصة (private)
    if chat_type == "private":
        keyboard = [
            # 💡 سيتم تغيير الرسالة المرسلة من الـ WebApp لكي تتضمن الكلمة
            [KeyboardButton("🎨 فتح لوحة الرسم", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "اضغط زر فتح لوحة الرسم لاختيار كلمتك وبدء الرسم:", 
            reply_markup=markup
        )
    # لا حاجة لـ 'else' لأننا نتعامل مع المجموعات في 'start_game'

# ------------------------------------
# 3. معالج بيانات الـ WebApp (الصورة + الكلمة)
# ------------------------------------
async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = update.effective_message.web_app_data.data
    user_id = update.effective_user.id
    user = update.effective_user
    
    # الحصول على chat_id المحفوظ (المجموعة المستهدفة)
    target_chat_id = last_user_chat_id.get(user_id)
    if not target_chat_id:
        await update.effective_message.reply_text("❌ لم يتم تحديد المجموعة المستهدفة. ابدأ اللعبة من المجموعة أولاً.")
        return

    # 1. تحليل البيانات
    # نتوقع البيانات بالصيغة: "DOODLE_DATA::[image_url]::[word]"
    match = re.search(r"^DOODLE_URL::(.+?)::(.+)", data, re.DOTALL)
    
    if match:
        image_url = match.group(1).strip()
        correct_word = match.group(2).strip()
        
        # 2. تحديث حالة اللعبة
        game_states[target_chat_id] = {
            'artist_id': user_id,
            'correct_word': correct_word,
            'guessed': False # إضافة حالة التخمين
        }
        
        # 3. إرسال الصورة للمجموعة المستهدفة
        user_mention = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
        caption = f"🎨 رسمة جديدة بواسطة: {user_mention}\n\n**خمنوا الكلمة الآن!** 🤫"
        
        await context.bot.send_photo(
            chat_id=target_chat_id,
            photo=image_url,
            caption=caption,
            parse_mode='HTML'
        )
        
        # 4. إرسال رسالة تأكيد للرسام في الخاص
        await update.effective_message.reply_text(f"✅ تم إرسال رسمتك للمجموعة بنجاح!\nالكلمة الصحيحة هي: **{correct_word}**\nانتظر الآن تخمين أصدقائك.")
        
        print(f"DEBUG: Game started in chat {target_chat_id}. Artist: {user_id}, Word: {correct_word}")
        return

    # 🔴 الحالة الافتراضية
    await update.effective_message.reply_text("تم استلام بيانات مجهولة من WebApp.")

# ------------------------------------
# 4. معالج التخمينات (في المجموعة)
# ------------------------------------
async def guess_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_chat_id = update.message.chat_id
    guesser_id = update.effective_user.id
    guesser = update.effective_user
    guess_text = update.message.text.strip().lower() # تحويل الكلمة المُخمّنة إلى lowercase
    
    # 1. التحقق من وجود لعبة نشطة وحالة التخمين
    if group_chat_id not in game_states:
        return # لا توجد لعبة نشطة

    game_state = game_states[group_chat_id]
    correct_word = game_state.get('correct_word', '').strip().lower()
    artist_id = game_state.get('artist_id')
    
    if game_state.get('guessed'):
        return # تم التخمين في هذه الجولة بالفعل

    # 2. منع الرسام من التخمين
    if guesser_id == artist_id:
        return # الرسام لا يمكنه التخمين في رسمته

    # 3. التحقق من التخمين
    if guess_text == correct_word:
        game_states[group_chat_id]['guessed'] = True # تحديد أن الكلمة قد خمنت
        
        # 4. تسجيل النقاط
        # نقطة للرسام
        scores[artist_id] = scores.get(artist_id, 0) + 1
        # نقطة للمخمن
        scores[guesser_id] = scores.get(guesser_id, 0) + 1
        
        artist_info = await context.bot.get_chat_member(group_chat_id, artist_id)
        artist_name = artist_info.user.first_name
        guesser_name = guesser.first_name
        
        # 5. إرسال رسالة الفوز والنتائج
        
        # جلب قائمة النقاط
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_scores = "\n".join([
            f"- {await get_user_name(context, user_id, group_chat_id)}: {score} نقطة" 
            for user_id, score in sorted_scores[:5] # عرض أول 5 نتائج
        ])

        final_message = (
            f"🎉 **تخمين صحيح!** 🎉\n"
            f"الكلمة الصحيحة هي: **{correct_word}**\n"
            f"الرسام: <a href='tg://user?id={artist_id}'>{artist_name}</a> (+1 نقطة)\n"
            f"المخمن: <a href='tg://user?id={guesser_id}'>{guesser_name}</a> (+1 نقطة)\n\n"
            f"--- **النتائج الحالية** ---\n"
            f"{top_scores or 'لا توجد نقاط بعد!'}"
        )
        
        await update.message.reply_text(final_message, parse_mode='HTML')
        
        # 6. مسح حالة اللعبة لبدء جولة جديدة
        del game_states[group_chat_id]
        
    # 7. معالج لعرض النتائج يدوياً
async def show_scores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_chat_id = update.message.chat_id
    if not scores:
        await update.message.reply_text("لا توجد نقاط مسجلة بعد. ابدأ اللعب!")
        return

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    score_list = []
    
    for user_id, score in sorted_scores:
        name = await get_user_name(context, user_id, group_chat_id)
        score_list.append(f"- {name}: **{score}** نقطة")
        
    message = "🏆 **النتائج الحالية للعبة خمن وارسم** 🏆\n" + "\n".join(score_list)
    await update.message.reply_text(message, parse_mode='Markdown')

# دالة مساعدة للحصول على اسم المستخدم
async def get_user_name(context, user_id, chat_id):
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.user.first_name
    except:
        return f"مستخدم غير معروف ({user_id})"

# ---------------------------
# 🚀 التشغيل
# ---------------------------
def main():
    global application
    application = Application.builder().token(TOKEN).build()
    
    # معالج بدء اللعبة في المجموعة
    application.add_handler(MessageHandler(
        filters.Regex(re.compile(r"^(خمن وارسم|ارسم وخمن)$", re.IGNORECASE)) & filters.ChatType.GROUPS, 
        start_game
    ))
    
    # معالج الأمر /start في الخاص (يستقبل Deep Link)
    application.add_handler(CommandHandler("start", start_private, filters=filters.ChatType.PRIVATE))
    
    # معالج بيانات الـ WebApp (للصورة والكلمة)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    
    # معالج التخمينات (أي رسالة نصية في المجموعة)
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, guess_handler))
    
    # معالج عرض النتائج
    application.add_handler(CommandHandler("scores", show_scores))
    
    logger.info("Bot running with polling...")
    print("\n\n--- BOT STARTED. Ready for 'خمن وارسم' and Guessing. ---")
    application.run_polling(poll_interval=1.0)


if __name__ == "__main__":
    main()