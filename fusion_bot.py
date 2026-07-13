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
            ("Драйв, движение и энергия", "fire_dance"),
            ("Глубокие эмоции и переживания", "fire_emotions"),
            ("Азарт перевоплощения и игры", "fire_theatre"),
        ],
    },
    {
        "q": "Что бы ты хотел делать в студии?",
        "options": [
            ("Петь или играть на инструменте", "do_music"),
            ("Танцевать и двигаться", "do_dance"),
            ("Играть на сцене, перевоплощаться в образы", "do_theatre"),
        ],
    },
]

user_answers = {}
casting_data = {}
casting_users = {}

# --- /START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎯 Пройти опрос", callback_data="start_quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🎬 **ВСТУПАЙ В «ФЬЮЖН»!**\n\n"
        "Мы — студия, где музыка, вокал, танец и театр сплавляются в одно целое.\n"
        "Здесь рождаются крутые проекты, живёт энергия и драйв.\n\n"
        "Пройди короткий опрос, заполни анкету — и мы пригласим тебя на кастинг.\n"
        "Это твой шанс найти своё место и зажечь!\n\n"
        "**Нажми на кнопку! 👇**"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
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
        await after_quiz(update, context, user_id)


async def after_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    answers = user_answers.get(user_id, [])
    
    # Определяем направление
    direction = "music"
    if len(answers) >= 4:
        fire = answers[2]
        do = answers[3]
        if "dance" in fire or "dance" in do:
            direction = "dance"
        elif "theatre" in fire or "theatre" in do:
            direction = "theatre"
        elif "music" in do:
            direction = "music"
    
    direction_map = {
        "music": "🎵 Музыка / Вокал",
        "dance": "💃 Танец",
        "theatre": "🎭 Театр",
    }
    
    # Отправка админу
    try:
        admin_message = (
            f"📩 **Результаты опроса!**\n\n"
            f"👤 Пользователь: {update.effective_user.first_name} (@{update.effective_user.username or 'нет'})\n"
            f"🆔 ID: {user_id}\n\n"
            f"🏆 **Рекомендация:** {direction_map.get(direction, '—')}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    except Exception as e:
        print(f"Не удалось отправить админу: {e}")

    casting_data[user_id] = {"direction": direction}
    await ask_full_name(update, context, user_id)


# ==================== АНКЕТА ====================

async def ask_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    text = (
        "📝 **Теперь заполни анкету для кастинга**\n\n"
        "**Шаг 1 из 3: ФИО**\n\n"
        "Напиши свои **фамилию, имя и отчество**."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data["waiting_for"] = "full_name"


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    waiting_for = context.user_data.get("waiting_for")
    
    if waiting_for == "full_name":
        casting_data.setdefault(user_id, {})["full_name"] = text
        context.user_data["waiting_for"] = "age"
        await update.message.reply_text(
            "📝 **Шаг 2 из 3: Возраст**\n\n"
            "Сколько тебе лет?\n\n"
            "Напиши число в сообщении 👇",
            parse_mode="Markdown"
        )
    
    elif waiting_for == "age":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Напиши число.")
            return
        casting_data.setdefault(user_id, {})["age"] = text
        await ask_confirm_direction(update, context, user_id)
    
    else:
        await update.message.reply_text("Нажми /start, чтобы начать")


async def ask_confirm_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    direction = casting_data.get(user_id, {}).get("direction", "music")
    
    direction_map = {
        "music": "🎵 Музыка / Вокал",
        "dance": "💃 Танец",
        "theatre": "🎭 Театр",
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ Всё верно", callback_data="dir_confirm")],
        [InlineKeyboardButton("🔄 Хочу изменить", callback_data="dir_change")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📝 **Шаг 3 из 3: Подтверждение направления**\n\n"
        f"По результатам опроса тебе подходит: **{direction_map.get(direction, '—')}**\n\n"
        f"Ты согласен?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.user_data["waiting_for"] = None


async def direction_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "dir_change":
        keyboard = [
            [InlineKeyboardButton("🎵 Вокал / Музыка", callback_data="dir_set_music")],
            [InlineKeyboardButton("💃 Танец", callback_data="dir_set_dance")],
            [InlineKeyboardButton("🎭 Театр", callback_data="dir_set_theatre")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выбери направление:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    # dir_confirm или dir_set_*
    if query.data.startswith("dir_set_"):
        direction = query.data.replace("dir_set_", "")
        casting_data[user_id]["direction"] = direction
    elif query.data == "dir_confirm":
        direction = casting_data.get(user_id, {}).get("direction", "music")
    
    await ask_experience(update, context, user_id)


async def ask_experience(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    if user_id is None:
        user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🌱 Нет опыта", callback_data="exp_none")],
        [InlineKeyboardButton("🌿 До 1 года", callback_data="exp_beginner")],
        [InlineKeyboardButton("🌳 1-3 года", callback_data="exp_intermediate")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "📝 **Финальный шаг: Опыт**\n\n"
            "Какой у тебя опыт в выбранной сфере?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "📝 **Финальный шаг: Опыт**\n\n"
            "Какой у тебя опыт в выбранной сфере?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def experience_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    experience = query.data.replace("exp_", "")
    casting_data[user_id]["experience"] = experience
    data = casting_data.get(user_id, {})
    
    direction_map = {
        "music": "🎵 Музыка / Вокал",
        "dance": "💃 Танец",
        "theatre": "🎭 Театр",
    }
    
    experience_map = {
        "none": "🌱 Нет опыта",
        "beginner": "🌿 До 1 года",
        "intermediate": "🌳 1-3 года",
    }
    
    direction_key = data.get("direction", "music")
    
    admin_message = (
        f"📩 **НОВАЯ ЗАЯВКА НА КАСТИНГ!**\n\n"
        f"👤 ФИО: {data.get('full_name', '—')}\n"
        f"📅 Возраст: {data.get('age', '—')}\n"
        f"🎭 Направление: {direction_map.get(direction_key, '—')}\n"
        f"📊 Опыт: {experience_map.get(experience, '—')}\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{update.effective_user.username or 'нет'}"
    )
    
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
        await query.edit_message_text(
            "✅ **Заявка отправлена!**\n\n"
            "Спасибо! Мы свяжемся с тобой в ближайшее время.",
            parse_mode="Markdown"
        )
        
        if user_id not in casting_users:
            casting_users[user_id] = direction_key
        
    except Exception as e:
        await query.edit_message_text("⚠️ Что-то пошло не так, попробуй позже.")
        print(f"Ошибка: {e}")
    
    casting_data.pop(user_id, None)
    context.user_data.pop("waiting_for", None)


# ==================== РАССЫЛКА ====================

async def send_casting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет доступа.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Использование:\n"
            "`/send_casting [направление] [дата и время]`\n\n"
            "Направления:\n"
            "• вокал\n"
            "• танец\n"
            "• театр\n"
            "• музыка\n"
            "• все\n\n"
            "Примеры:\n"
            "`/send_casting вокал 25 июля, 18:00`\n"
            "`/send_casting все 30 июля, 12:00`",
            parse_mode="Markdown"
        )
        return
    
    direction_input = args[0].lower()
    date_time = " ".join(args[1:])
    
    direction_map_input = {
        "вокал": "music",
        "музыка": "music",
        "танец": "dance",
        "театр": "theatre",
        "все": "all",
    }
    
    direction_key = direction_map_input.get(direction_input)
    if not direction_key:
        await update.message.reply_text(
            "⚠️ Неизвестное направление.\n\n"
            "Доступные: вокал, танец, театр, музыка, все"
        )
        return
    
    users_to_send = []
    if direction_key == "all":
        users_to_send = list(casting_users.items())
    else:
        users_to_send = [(uid, d) for uid, d in casting_users.items() if d == direction_key]
    
    if not users_to_send:
        await update.message.reply_text(f"📭 Нет заявок на направление «{direction_input}».")
        return
    
    await update.message.reply_text(f"📤 Начинаю рассылку {len(users_to_send)} пользователям...")
    
    success = 0
    fail = 0
    
    direction_emoji = {
        "music": "🎵",
        "dance": "💃",
        "theatre": "🎭",
    }
    
    direction_name_ru = {
        "music": "Вокал / Музыка",
        "dance": "Танец",
        "theatre": "Театр",
    }
    
    for user_id, user_direction in users_to_send:
        try:
            emoji = direction_emoji.get(user_direction, "🎭")
            dir_name = direction_name_ru.get(user_direction, "")
            
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎬 **Приглашение на кастинг!**\n\n"
                    f"{emoji} Направление: **{dir_name}**\n"
                    f"📅 Дата и время: **{date_time}**\n\n"
                    f"Ждём тебя в студии «Фьюжн»! 🔥"
                ),
                parse_mode="Markdown"
            )
            success += 1
        except Exception as e:
            fail += 1
            print(f"Не удалось отправить {user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ **Рассылка завершена!**\n\n"
        f"📨 Отправлено: {success}\n"
        f"❌ Не доставлено: {fail}"
    )


# ==================== ЗАПУСК ====================

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_casting", send_casting))
    app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_quiz"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^q\d+\|"))
    app.add_handler(CallbackQueryHandler(direction_confirm_handler, pattern=r"^(dir_confirm|dir_change|dir_set_)"))
    app.add_handler(CallbackQueryHandler(experience_handler, pattern=r"^exp_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
