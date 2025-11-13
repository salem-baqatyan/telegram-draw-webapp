import logging
import json
import re
import html # 💡 إضافة استيراد html
from unidecode import unidecode # 💡 إضافة استيراد unidecode (يجب تثبيتها: pip install unidecode)
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
# 💡 الدوال المساعدة لتنسيق وعرض اسم اللاعب
# ------------------------------------
def get_player_mention(player_data):
    """إنشاء إشارة (mention) للاعب."""
    user_id = player_data.get('id')
    # يجب استخدام الاسم الذي سيتم عرضه لتجنب الـ escape المزدوج
    name = player_data.get('name') 
    return f'<a href="tg://user?id={user_id}">{name}</a>'

def get_display_name(player_data, player_id):
    """الحصول على اسم مناسب للعرض."""
    username = player_data.get('username')
    name = player_data.get('first_name') # نستخدم first_name من object الـ User

    # ✅ 1. إذا عنده يوزر نيم نستخدمه مباشرة
    if username:
        return f"@{username}"

    # ✅ 2. إذا الاسم يحتوي على حروف إنجليزية، نستخدمه كما هو (مع الهروب لضمان التنسيق)
    if name and re.search(r'[A-Za-z]', name):
        return html.escape(name)

    # ✅ 3. إذا الاسم بالعربي، نحاول نحوله لإنجليزية تقريبية
    if name:
        try:
            transliterated = unidecode(name)
            clean_name = re.sub(r'[^A-Za-z0-9]', '', transliterated)
            # نستخدم الاسم المترجم إذا كان نظيفاً وطويلاً بما فيه الكفاية أو نعود للاسم الافتراضي
            if clean_name and len(clean_name) >= 3:
                return clean_name
            else:
                return html.escape(name) # نعود للاسم الأصلي مع الهروب
        except Exception:
            return html.escape(name) # فشل التحويل، نعود للاسم الأصلي مع الهروب

    # ✅ 4. إذا لا يوجد اسم أصلاً
    return f"Player_{player_id}"

# ------------------------------------
# 💡 الدالة الجديدة لتنسيق الجدول (مُعدَّلة لاستخدام الدوال الجديدة)
# ------------------------------------
async def format_scores_table(context, chat_id, current_artist_id=None):
    if not scores:
        return "لا توجد نقاط مسجلة بعد. ابدأ اللعب! 🎮"
    
    # 1. فرز النتائج تنازلياً
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    # 2. تجهيز الترويسة
    table_header = "\n**🏆 الترتيب الحالي للعبة خمن وارسم 🏆**\n"
    table_header += "```\n"
    table_header += "# | الاسم           | النقاط | الحالة\n"
    table_header += "--|----------------|--------|-------\n"
    
    table_rows = []
    
    # 3. بناء صفوف الجدول
    for index, (user_id, score) in enumerate(sorted_scores):
        
        # جلب بيانات المستخدم
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            user_data = member.user
            player_info = {
                'id': user_id,
                'first_name': user_data.first_name,
                'username': user_data.username
            }
            # الحصول على الاسم المنسق للعرض
            display_name = get_display_name(player_info, user_id)
            
        except Exception:
            display_name = f"Player_{user_id}" # اسم افتراضي إذا فشل الجلب
        
        # تحديد حالة الدور
        status_emoji = ""
        if user_id == current_artist_id:
            status_emoji = "✍️" # الرسام الحالي
        elif score > 0:
            status_emoji = "🎉" 
            
        # تنسيق السطر باستخدام padding
        row = "{:<2} | {:<14} | {:<6} | {}".format(
            index + 1,
            display_name[:14],  # اقتصار الاسم ليتناسب مع الجدول
            score,
            status_emoji
        )
        table_rows.append(row)
    
    # 4. تجميع الجدول
    table_footer = "```"
    # يتم استخدام Parse Mode: HTML للرسالة التي تحتوي على هذا الجدول.
    return table_header + "\n".join(table_rows) + table_footer


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
    # تم التعديل هنا: استخدام DOODLE_URL:: كما في الكود المرسل
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
# 4. معالج التخمينات (في المجموعة) - مُعدَّل
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
        scores[artist_id] = scores.get(artist_id, 0) + 1
        scores[guesser_id] = scores.get(guesser_id, 0) + 1
        
        # جلب معلومات الرسام والمخمن للعرض في الرسالة
        artist_info = await context.bot.get_chat_member(group_chat_id, artist_id)
        guesser_info = await context.bot.get_chat_member(group_chat_id, guesser_id)
        
        artist_mention = get_player_mention({'id': artist_id, 'name': artist_info.user.first_name})
        guesser_mention = get_player_mention({'id': guesser_id, 'name': guesser_info.user.first_name})
        
        # 5. إرسال رسالة الفوز والنتائج
        score_table = await format_scores_table(context, group_chat_id)

        final_message = (
            f"🎉 **تخمين صحيح! فائزان في هذه الجولة!** 🎉\n"
            f"الكلمة الصحيحة هي: **{correct_word}**\n"
            f"الرسام: {artist_mention} **(+1 نقطة)**\n"
            f"المخمن: {guesser_mention} **(+1 نقطة)**\n"
            f"\n{score_table}" # تضمين الجدول
        )
        
        await update.message.reply_text(final_message, parse_mode='HTML')
        
        # 6. مسح حالة اللعبة لبدء جولة جديدة
        del game_states[group_chat_id]

# ------------------------------------
# 7. معالج لعرض النتائج يدوياً
# ------------------------------------
async def show_scores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_chat_id = update.message.chat_id
    
    current_artist = None
    if group_chat_id in game_states:
        current_artist = game_states[group_chat_id]['artist_id']
        
    score_table = await format_scores_table(context, group_chat_id, current_artist)
    
    # نستخدم Parse Mode: HTML لأن تنسيق الجدول يعتمد على ```
    await update.message.reply_text(score_table, parse_mode='HTML') 


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