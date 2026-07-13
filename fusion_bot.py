import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = "8813591285:AAFviC_uOYTB-4x9HaEDrZRQUtCaOya1RrY"
ADMIN_ID = 1431254201

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========================= ДАННЫЕ =========================
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

# Глобальные хранилища
user_answers = {}
casting_data = {}
casting_users = {}  # user_id: direction


def get_direction_ru(direction: str) -> str:
    return {
        "music": "🎵 Вокал / Музыка",
        "dance": "💃 Танец",
        "theatre": "🎭 Театр",
    }.get(direction, "Не указано")


async def clear_user_data(user_id: int):
    user_answers.pop(user_id, None)
    casting_data.pop(user_id, None)
    casting_users.pop(user_id, None)


# ========================= ОСНОВНЫЕ ФУНКЦИИ =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await clear_user_data(user_id)
    context.user_data.clear()

    keyboard = [[InlineKeyboardButton("🎯 Пройти опрос", callback_data="start_quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🎬 **ВСТУПАЙ В «ФЬЮЖН»!**\n\n"
        "Пройди опрос и заполни анкету, чтобы попасть на кастинг.\n\n"
        "👇 **Нажми на кнопку!**",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    await clear_user_data(user_id)
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

    await update.callback_query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=reply_markup
    )


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


# ========================= СОГЛАСИЕ =========================
async def ask_consent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("✅ Да, соглашаюсь", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ Нет, не соглашаюсь", callback_data="consent_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        "📋 **Согласие на обработку персональных данных**\n\nТы соглашаешься?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def consent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "consent_no":
        await query.edit_message_text("😔 Ок. Если передумаешь — возвращайся!")
        await clear_user_data(user_id)
        return

    casting_data[user_id]["consent"] = True
    await ask_name(update, context, user_id)


# ========================= АНКЕТА =========================
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    await update.callback_query.edit_message_text(
        "📝 **Шаг 1 из 4: Имя и фамилию**\n\nНапиши свои **имя и фамилию**.",
        parse_mode="Markdown"
    )
    context.user_data["waiting_for"] = "name"


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
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
            await update.message.reply_text("⚠️ Пожалуйста, напиши **число**.")
            return
        casting_data.setdefault(user_id, {})["age"] = int(text)
        context.user_data["waiting_for"] = None
        await ask_direction(update, context, user_id)

    elif waiting_for == "experience_place":
        casting_data.setdefault(user_id, {})["experience_place"] = text
        context.user_data["waiting_for"] = None
        await finish_casting(update, context, user_id)

    else:
        await update.message.reply_text("Нажми /start, чтобы начать заново.")


async def ask_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("🎵 Вокал / Музыка", callback_data="dir_music")],
        [InlineKeyboardButton("💃 Танец", callback_data="dir_dance")],
        [InlineKeyboardButton("🎭 Театр", callback_data="dir_theatre")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

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

    await update.callback_query.edit_message_text(
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
        "📝 **Где ты занимался творчеством раньше?**\n\n"
        "Напиши в сообщении. Если ничего не было — напиши «Нигде».",
        parse_mode="Markdown"
    )


# ========================= ФИНАЛ =========================
async def finish_casting(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = casting_data.get(user_id, {})
    if not data:
        await update.message.reply_text("Что-то пошло не так. Начни заново /start")
        return

    direction = data.get("direction", "music")
    answers = user_answers.get(user_id, [])

    # Отправка админу
    admin_message = (
        f"📩 **НОВАЯ ЗАЯВКА НА КАСТИНГ!**\n\n"
        f"👤 Имя и фамилия: {data.get('name', '—')}\n"
        f"📅 Возраст: {data.get('age', '—')}\n"
        f"🎭 Направление: {get_direction_ru(direction)}\n"
        f"📊 Опыт: {data.get('experience', '—')}\n"
        f"📍 Где занимался: {data.get('experience_place', '—')}\n\n"
        f"📝 Ответы на опрос:\n" +
        "\n".join([f"• {a}" for a in answers]) +
        f"\n\n🆔 ID: {user_id}\n"
        f"👤 Username: @{update.effective_user.username or 'нет'}"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")

    # Финальное сообщение пользователю
    recommendations = {
        "music": "🎤 **Для вокалистов и музыкантов:**\n• Возьми минусовку\n• Приходи распетым\n• Если играешь — бери инструмент",
        "dance": "💃 **Для танцоров:**\n• Удобная одежда\n• Возьми музыку\n• Будь готов к импровизации",
        "theatre": "🎭 **Для театралов:**\n• Подготовь монолог (1-2 мин)\n• Можно стихотворение\n• Будь готов к этюдам",
    }

    final_text = (
        f"✅ **Заявка успешно отправлена!**\n\n"
        f"Спасибо! Мы свяжемся с тобой в ближайшее время.\n\n"
        f"---\n\n"
        f"📌 **Подписывайся на нас:**\n"
        f"Telegram: https://t.me/fusion_nstu\n"
        f"ВКонтакте: https://vk.com/fusion_nstu\n"
        f"Instagram: https://www.instagram.com/fusion_nstu\n\n"
        f"---\n\n"
        f"{recommendations.get(direction, '')}\n\n"
        f"🔥 **Ждём тебя на кастинге!**"
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=final_text,
            parse_mode="Markdown"
        )
        logging.info(f"✅ Финальное сообщение отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки финального сообщения {user_id}: {e}")
        # Запасной вариант
        try:
            await update.message.reply_text(final_text, parse_mode="Markdown")
        except:
            pass

    # Сохраняем для рассылки
    casting_users[user_id] = direction

    # Очистка
    await clear_user_data(user_id)
    context.user_data.clear()


# ========================= РАССЫЛКА =========================
async def send_casting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ Использование: `/send_casting [направление] [дата и время]`\n"
            "Пример: `/send_casting вокал 25 июля, 18:00`",
            parse_mode="Markdown"
        )
        return

    direction_input = args[0].lower()
    date_time = " ".join(args[1:])

    direction_map = {
        "вокал": "music", "музыка": "music",
        "танец": "dance", "театр": "theatre",
        "все": "all"
    }

    direction_key = direction_map.get(direction_input)
    if not direction_key:
        await update.message.reply_text("⚠️ Неизвестное направление.")
        return

    users_to_send = list(casting_users.items()) if direction_key == "all" else \
                    [(uid, d) for uid, d in casting_users.items() if d == direction_key]

    if not users_to_send:
        await update.message.reply_text(f"📭 Нет заявок по направлению «{direction_input}».")
        return

    await update.message.reply_text(f"📤 Начинаю рассылку {len(users_to_send)} пользователям...")

    success = fail = 0
    direction_name_ru = {"music": "Вокал/Музыка", "dance": "Танец", "theatre": "Театр"}

    for uid, user_dir in users_to_send:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"🎬 **Приглашение на кастинг!**\n\n"
                     f"Направление: **{direction_name_ru.get(user_dir, '')}**\n"
                     f"📅 Дата: **{date_time}**\n\n"
                     f"Ждём тебя! 🔥",
                parse_mode="Markdown"
            )
            success += 1
        except Exception as e:
            logging.error(f"Не удалось отправить {uid}: {e}")
            fail += 1

    await update.message.reply_text(f"✅ Отправлено: {success}\n❌ Не доставлено: {fail}")


# ========================= ЗАПУСК =========================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_casting", send_casting))

    app.add_handler(CallbackQueryHandler(start_quiz, pattern="^start_quiz$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^q\d+\|"))
    app.add_handler(CallbackQueryHandler(consent_handler, pattern=r"^consent_"))
    app.add_handler(CallbackQueryHandler(direction_handler, pattern=r"^dir_"))
    app.add_handler(CallbackQueryHandler(experience_handler, pattern=r"^exp_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Бот успешно запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
