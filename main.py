import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = os.getenv("TOKEN")                    # Будет браться из Railway
ADMIN_ID = int(os.getenv("ADMIN_ID", 1431254201))
PORT = int(os.getenv("PORT", 8443))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")        # Укажешь в Railway

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========================= ДАННЫЕ =========================
QUESTIONS = [
    {"q": "Хочешь ли ты в универе заниматься активной творческой деятельностью и быть в центре коллектива?",
     "options": [("Да, очень хочу!", "active_yes"), ("Скорее да, чем нет", "active_maybe"), ("Не уверен, но хочу попробовать", "active_try")]},
    {"q": "Готов ли ты пробовать себя в творчестве, даже если у тебя пока нет опыта?",
     "options": [("Да, я открыт к новому", "exp_open"), ("Да, но немного волнуюсь", "exp_scared"), ("Я уже что-то умею", "exp_yes")]},
    {"q": "Что тебя больше зажигает в творчестве?",
     "options": [("Движение, танец, пластика", "fire_dance"), ("Вокал, музыка, ритм, мелодия", "fire_music"), ("Перевоплощение, игра на сцене, образы", "fire_theatre")]},
    {"q": "Что бы ты хотел делать в студии?",
     "options": [("Петь или играть на инструменте", "do_music"), ("Танцевать", "do_dance"), ("Играть на сцене", "do_theatre")]},
]

user_answers = {}
casting_data = {}
casting_users = {}

def get_direction_ru(direction: str) -> str:
    return {"music": "🎵 Вокал / Музыка", "dance": "💃 Танец", "theatre": "🎭 Театр"}.get(direction, "Не указано")

async def clear_user_data(user_id: int):
    user_answers.pop(user_id, None)
    casting_data.pop(user_id, None)
    casting_users.pop(user_id, None)

# ========================= ОБРАБОТЧИКИ =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await clear_user_data(user_id)
    context.user_data.clear()

    keyboard = [[InlineKeyboardButton("🎯 Пройти опрос", callback_data="start_quiz")]]
    await update.message.reply_text(
        "🎬 **ВСТУПАЙ В «ФЬЮЖН»!**\n\nПройди опрос и заполни анкету.\n\n👇 **Нажми кнопку!**",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await clear_user_data(user_id)
    user_answers[user_id] = []
    await ask_question(update, context, 0)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int):
    q = QUESTIONS[q_index]
    keyboard = [[InlineKeyboardButton(text, callback_data=f"q{q_index}|{val}")] for text, val in q["options"]]
    await update.callback_query.edit_message_text(
        f"**Вопрос {q_index + 1} из {len(QUESTIONS)}**\n\n{q['q']}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data.split("|")
    q_index, answer = int(data[0][1:]), data[1]
    user_answers.setdefault(user_id, []).append(answer)

    if q_index + 1 < len(QUESTIONS):
        await ask_question(update, context, q_index + 1)
    else:
        casting_data[user_id] = {}
        await ask_consent(update, context, user_id)

async def ask_consent(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("✅ Да, соглашаюсь", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ Нет, не соглашаюсь", callback_data="consent_no")]
    ]
    await update.callback_query.edit_message_text(
        "📋 **Согласие на обработку данных**\n\nТы соглашаешься?",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def consent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "consent_no":
        await query.edit_message_text("😔 Ок. Возвращайся, если передумаешь!")
        await clear_user_data(user_id)
        return
    casting_data[user_id]["consent"] = True
    await ask_name(update, context, user_id)

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    await update.callback_query.edit_message_text(
        "📝 **Шаг 1 из 4: Имя и фамилия**\n\nНапиши имя и фамилию.",
        parse_mode="Markdown"
    )
    context.user_data["waiting_for"] = "name"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    waiting = context.user_data.get("waiting_for")

    if waiting == "name":
        casting_data.setdefault(user_id, {})["name"] = text
        context.user_data["waiting_for"] = "age"
        await update.message.reply_text("📝 **Шаг 2 из 4: Возраст**\n\nСколько тебе лет?", parse_mode="Markdown")

    elif waiting == "age":
        if not text.isdigit():
            await update.message.reply_text("⚠️ Напиши число.")
            return
        casting_data.setdefault(user_id, {})["age"] = int(text)
        context.user_data["waiting_for"] = None
        await ask_direction(update, context, user_id)

    elif waiting == "experience_place":
        casting_data.setdefault(user_id, {})["experience_place"] = text
        context.user_data["waiting_for"] = None
        await finish_casting(update, context, user_id)

async def ask_direction(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("🎵 Вокал / Музыка", callback_data="dir_music")],
        [InlineKeyboardButton("💃 Танец", callback_data="dir_dance")],
        [InlineKeyboardButton("🎭 Театр", callback_data="dir_theatre")]
    ]
    await update.message.reply_text("📝 **Шаг 3 из 4: Направление**", parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def direction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    casting_data[query.from_user.id]["direction"] = query.data.replace("dir_", "")
    await ask_experience(update, context, query.from_user.id)

async def ask_experience(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    keyboard = [
        [InlineKeyboardButton("🌱 Нет опыта", callback_data="exp_none")],
        [InlineKeyboardButton("🌿 До 1 года", callback_data="exp_beginner")],
        [InlineKeyboardButton("🌳 1-3 года", callback_data="exp_intermediate")],
        [InlineKeyboardButton("🔥 3+ года", callback_data="exp_pro")]
    ]
    await update.callback_query.edit_message_text("📝 **Шаг 4 из 4: Опыт**", parse_mode="Markdown",
                                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def experience_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    casting_data[user_id]["experience"] = query.data.replace("exp_", "")
    context.user_data["waiting_for"] = "experience_place"
    await query.edit_message_text("📝 **Где ты занимался раньше?** (напиши «Нигде», если нет)", parse_mode="Markdown")

async def finish_casting(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    data = casting_data.get(user_id, {})
    direction = data.get("direction", "music")
    answers = user_answers.get(user_id, [])

    # Админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 **НОВАЯ ЗАЯВКА**\n\nИмя: {data.get('name')}\nВозраст: {data.get('age')}\n"
             f"Направление: {get_direction_ru(direction)}\nОпыт: {data.get('experience')}\nГде: {data.get('experience_place')}\n"
             f"ID: {user_id}",
        parse_mode="Markdown"
    )

    # Пользователю
    final_text = f"✅ **Заявка отправлена!**\nСпасибо! Мы свяжемся с тобой.\n\n🔥 Ждём на кастинге!"
    await context.bot.send_message(chat_id=user_id, text=final_text, parse_mode="Markdown")

    casting_users[user_id] = direction
    await clear_user_data(user_id)
    context.user_data.clear()

async def send_casting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    # (оставь свою функцию рассылки, если нужно)

# ========================= ЗАПУСК =========================
async def post_init(application: Application):
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", drop_pending_updates=True)
        logging.info(f"Webhook set: {WEBHOOK_URL}/webhook")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send_casting", send_casting))
    app.add_handler(CallbackQueryHandler(start_quiz, pattern="^start_quiz$"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^q\d+\|"))
    app.add_handler(CallbackQueryHandler(consent_handler, pattern=r"^consent_"))
    app.add_handler(CallbackQueryHandler(direction_handler, pattern=r"^dir_"))
    app.add_handler(CallbackQueryHandler(experience_handler, pattern=r"^exp_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    if WEBHOOK_URL:
        app.run_webhook(listen="0.0.0.0", port=PORT, url_path="webhook")
    else:
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
# ==========================================
# ЗАПУСК БОТА (Добавьте это в самый низ bot.py)
# ==========================================
if __name__ == "__main__":
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд (проверьте, что они у вас есть и импортированы)
    # Если у вас они зарегистрированы выше по коду, эту часть можно пропустить.
    application.add_handler(CommandHandler("start", start))
    # application.add_handler(MessageHandler(filters.TEXT, handle_text)) # если есть такой хендлер

    # ЗАПУСК БЕЗ ВЕБХУКОВ (используем poll)
    print("✅ Бот запускается в режиме Polling...")
    application.run_polling()
