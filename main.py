import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- ТВОИ ДАННЫЕ ---
TOKEN = "8813591285:AAFviC_uOYTB-4x9HaEDrZRQUtCaOya1RrY"
ADMIN_ID = 1431254201

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- ВОПРОСЫ ---
QUESTIONS = [
    {
        "q": "Хочешь ли ты в универе заниматься активной творческой деятельностью и быть в центре коллектива?",
        "options": [
            ("Да, очень хочу!", "active_yes"),
            ("Скорее да, чем нет", "active_maybe"),
            ("Не уверен, но хочу попробовать", "active_try"),
        ],
    },
    {
        "q": "Готов ли ты пробовать себя в творчестве, даже если у тебя пока нет опыта?",
        "options": [
            ("Да, я открыт к новому", "exp_open"),
            ("Да, но немного волнуюсь", "exp_scared"),
            ("Я уже что-то умею", "exp_yes"),
        ],
    },
    {
        "q": "Что тебя больше зажигает в творчестве?",
        "options": [
            ("Движение, танец, пластика", "fire_dance"),
            ("Вокал, музыка, ритм, мелодия", "fire_music"),
            ("Перевоплощение, игра на сцене, образы", "fire_theatre"),
        ],
    },
    {
        "q": "Что бы ты хотел делать в студии?",
        "options": [
            ("Петь или играть на инструменте", "do_music"),
            ("Танцевать", "do_dance"),
            ("Играть на сцене", "do_theatre"),
        ],
    },
]

user_answers = {}
casting_data = {}
casting_users = {}

# ==================== СТАРТ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_answers.pop(user_id, None)
    casting_data.pop(user_id, None)
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("🎯 Пройти опрос", callback_data="start_quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🎬 **ВСТУПАЙ В «ФЬЮЖН»!**\n\n"
        "Пройди опрос и заполни анкету, чтобы попасть на кастинг.\n\n"
        "👇 **Нажми на кнопку!**"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    user_answers.pop(user_id, None)
    casting_data.pop(user_id, None)
    context.user_data.clear()
    
    user_answers[user_id] = []
    await ask_question(update, context, 0)


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int):
    question = QUESTIONS[q_index]
    keyboard = [
        [InlineKeyboardButton(text, callback_data=f"q{q_index}|{value}")]
        for text, value in question["options"]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"**Вопрос {q_index + 1} из {len(QUESTIONS)}**\n\n{question['q']}"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.split("|")
    q_index = int(data[0].replace("q", ""))
    answer = data[1]

    user_answers.setdefault(user_id, []).append(answer)

    if q_index + 1 < len(QUESTIONS):
        await ask_question(update, context, q_index + 1)
    else:
        casting_data[user_id] = {}
        await ask_consent(update, context, user_id)


# ==================== СОГЛАСИЕ ====================

async def ask_consent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("✅ Да, соглашаюсь", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ Нет, не соглашаюсь", callback_data="consent_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📋 **Согласие на обработку персональных данных**\n\nТы соглашаешься?"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def consent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "consent_no":
        await query.edit_message_text("😔 Ок. Если передумаешь — возвращайся!", parse_mode="Markdown")
        casting_data.pop(user_id, None)
        user_answers.pop(user_id, None)
        return
    
    casting_data[user_id]["consent"] = True
    await ask_name(update, context, user_id)


# ==================== АНКЕТА (ТЕКСТ) ====================

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    text = "📝 **Шаг 1 из 4: Имя и фамилия**\n\nНапиши свои **имя и фамилию**."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data["waiting_for"] = "name"


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    waiting_for = context.user_data.get("waiting_for")
    
    if waiting_for == "name":
        casting_data.setdefault(user_id, {})["name"] = text
        context.user_data["waiting_for"] = "age"
        await update.message.reply_text(
            "📝 **Шаг 2 из 4: Возраст**\n\nСколько тебе лет? Напиши число 👇",
            parse_mode="Markdown"
        )
    
    elif waiting_for == "age":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Напиши число.")
            return
        casting_data.setdefault(user_id, {})["age"] = text
        context.user_data["waiting_for"] = None
        await ask_direction(update, context, user_id)
    
    elif waiting_for == "experience_place":
        casting_data.setdefault(user_id, {})["experience_place"] = text
        context.user_data["waiting_for"] = None
        # ОТПРАВЛЯЕМ ВСЁ И ФИНАЛЬНОЕ СООБЩЕНИЕ
        await finish_casting(update, context, user_id)
    
    else:
        await update.message.reply_text("Нажми /start, чтобы начать")


# ==================== АНКЕТА (КНОПКИ) ====================

async def ask_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("🎵 Вокал / Музыка", callback_data="dir_music")],
        [InlineKeyboardButton("💃 Танец", callback_data="dir_dance")],
        [InlineKeyboardButton("🎭 Театр", callback_data="dir_theatre")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📝 **Шаг 3 из 4: Выбери направление**",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📝 **Шаг 3 из 4: Выбери направление**",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def direction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    direction = query.data.replace("dir_", "")
    casting_data[user_id]["direction"] = direction
    await ask_experience(update, context, user_id)


async def ask_experience(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("🌱 Нет опыта", callback_data="exp_none")],
        [InlineKeyboardButton("🌿 До 1 года", callback_data="exp_beginner")],
        [InlineKeyboardButton("🌳 1-3 года", callback_data="exp_intermediate")],
        [InlineKeyboardButton("🔥 3+ года", callback_data="exp_pro")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📝 **Шаг 4 из 4: Опыт**\n\nКакой у тебя опыт?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📝 **Шаг 4 из 4: Опыт**\n\nКакой у тебя опыт?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def experience_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    experience = query.data.replace("exp_", "")
    casting_data[user_id]["experience"] = experience
    context.user_data["waiting_for"] = "experience_place"
    
    await query.edit_message_text(
        "📝 **Где ты занимался творчеством раньше?**\n\nНапиши в сообщении. Если ничего не было — напиши «Нигде».",
        parse_mode="Markdown"
    )


# ==================== ФИНАЛ ====================

async def finish_casting(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = casting_data.get(user_id, {})
    
    direction_map = {
        "music": "🎵 Вокал / Музыка",
        "dance": "💃 Танец",
        "theatre": "🎭 Театр",
    }
    
    experience_map = {
        "none": "🌱 Нет опыта",
        "beginner": "🌿 До 1 года",
        "intermediate": "🌳 1-3 года",
        "pro": "🔥 3+ года",
    }
    
    direction_key = data.get("direction", "music")
    answers = user_answers.get(user_id, [])
    answers_text = "\n".join([f"• {a}" for a in answers]) if answers else "Нет ответов"
    
    # --- ОТПРАВКА АДМИНУ ---
    admin_message = (
        f"📩 **НОВАЯ ЗАЯВКА НА КАСТИНГ!**\n\n"
        f"👤 Имя и фамилия: {data.get('name', '—')}\n"
        f"📅 Возраст: {data.get('age', '—')}\n"
        f"🎭 Направление: {direction_map.get(direction_key, '—')}\n"
        f"📊 Опыт: {experience_map.get(data.get('experience', ''), '—')}\n"
        f"📍 Где занимался: {data.get('experience_place', '—')}\n\n"
        f"📝 Ответы на опрос:\n{answers_text}\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{update.effective_user.username or 'нет'}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    
    # --- ФИНАЛЬНОЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЮ ---
    recommendations = {
        "music": "🎤 **Для вокалистов и музыкантов:**\n• Возьми минусовку\n• Приходи распетым\n• Если играешь — бери инструмент",
        "dance": "💃 **Для танцоров:**\n• Удобная одежда\n• Возьми музыку\n• Будь готов к импровизации",
        "theatre": "🎭 **Для театралов:**\n• Подготовь монолог (1-2 мин)\n• Можно стихотворение\n• Будь готов к этюдам",
    }
    
    final_text = (
        f"✅ **Заявка отправлена!**\n\n"
        f"Спасибо! Мы свяжемся с тобой.\n\n"
        f"---\n\n"
        f"📌 **Подписывайся на нас:**\n"
        f"📱 Telegram: https://t.me/fusion_nstu\n"
        f"📱 ВКонтакте: https://vk.com/fusion_nstu\n"
        f"📱 Instagram: https://www.instagram.com/fusion_nstu\n\n"
        f"---\n\n"
        f"{recommendations.get(direction_key, '')}\n\n"
        f"🔥 **Ждём тебя!**"
    )
    
    # ОТПРАВЛЯЕМ НОВОЕ СООБЩЕНИЕ
    await context.bot.send_message(chat_id=user_id, text=final_text, parse_mode="Markdown")
    
    if user_id not in casting_users:
        casting_users[user_id] = direction_key
    
    casting_data.pop(user_id, None)
    user_answers.pop(user_id, None)
    context.user_data.clear()


# ==================== РАССЫЛКА ====================

async def send_casting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Использование: `/send_casting [направление] [дата]`\n"
            "Пример: `/send_casting вокал 25 июля, 18:00`",
            parse_mode="Markdown"
        )
        return
    
    direction_input = args[0].lower()
    date_time = " ".join(args[1:])
    
    direction_map_input = {
        "вокал": "music", "музыка": "music",
        "танец": "dance",
        "театр": "theatre",
        "все": "all",
    }
    
    direction_key = direction_map_input.get(direction_input)
    if not direction_key:
        await update.message.reply_text("⚠️ Неизвестное направление. Доступные: вокал, танец, театр, музыка, все")
        return
    
    users_to_send = []
    if direction_key == "all":
        users_to_send = list(casting_users.items())
    else:
        users_to_send = [(uid, d) for uid, d in casting_users.items() if d == direction_key]
    
    if not users_to_send:
        await update.message.reply_text(f"📭 Нет заявок на «{direction_input}».")
        return
    
    await update.message.reply_text(f"📤 Рассылка {len(users_to_send)} пользователям...")
    
    success = 0
    fail = 0
    direction_name_ru = {"music": "Вокал/Музыка", "dance": "Танец", "theatre": "Театр"}
    
    for user_id, user_direction in users_to_send:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎬 **Приглашение на кастинг!**\n\n"
                    f"Направление: **{direction_name_ru.get(user_direction, '')}**\n"
                    f"📅 Дата: **{date_time}**\n\n"
                    f"Ждём тебя! 🔥"
                ),
                parse_mode="Markdown"
            )
            success += 1
        except Exception as e:
            fail += 1
            logging.error(f"Ошибка {user_id}: {e}")
    
    await update.message.reply_text(f"✅ Отправлено: {success}\n❌ Не доставлено: {fail}")


# ==================== ЗАПУСК ====================

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_casting", send_casting))
    app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_quiz"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^q\d+\|"))
    app.add_handler(CallbackQueryHandler(consent_handler, pattern=r"^consent_"))
    app.add_handler(CallbackQueryHandler(direction_handler, pattern=r"^dir_"))
    app.add_handler(CallbackQueryHandler(experience_handler, pattern=r"^exp_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Бот запущен в режиме Polling!")
    app.run_polling()

if __name__ == "__main__":
    main()
