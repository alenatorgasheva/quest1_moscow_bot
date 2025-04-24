from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import random
import json
import os

# Чтение токена из переменной окружения
TOKEN = os.environ['TOKEN']

# Чтение токена из файла
# def load_token(filename='bot1/TOKEN.txt'):
#    with open(filename, 'r') as file:
#        return file.read().strip()

# TOKEN = load_token()

# Функция для записи в лог
def log_message(update: Update, bot_response: str):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_message = update.message.text or f"<{update.message.effective_attachment}>"
    log_entry = f"{current_time} | Chat ID: {update.message.chat_id} | Message: {user_message} | Bot Response: {bot_response}\n"
    with open('bot1/DATA.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)

# Функция для чтения текстов из BOT_TEXTS.json
def load_bot_texts(filename='bot1/BOT_TEXTS.json'):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

bot_texts = load_bot_texts()

# Функция для чтения вопросов и ответов
def load_quest_questions(filename='bot1/QUEST.json'):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

# Функции для работы с активными квестами
def load_active_quests(filename='bot1/ACTIVE_QUESTS.txt'):
    active_quests = {}
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if '|' in line:
                    chat_id, current_question = line.split('|')
                    active_quests[int(chat_id)] = int(current_question)
    except FileNotFoundError:
        pass
    return active_quests

def save_active_quests(active_quests, filename='bot1/ACTIVE_QUESTS.txt'):
    with open(filename, 'w', encoding='utf-8') as file:
        for chat_id, current_question in active_quests.items():
            file.write(f"{chat_id}|{current_question}\n")

quest_data = load_active_quests()

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = bot_texts["start"]
    await update.message.reply_text(response)
    log_message(update, response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = bot_texts["help"]
    await update.message.reply_text(response)
    log_message(update, response)

# Команда /quest
async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id in quest_data:
        question_index = quest_data[user_id]
        questions = load_quest_questions()
        current_question = questions[question_index]['question']
        progress_bar = questions[question_index]['progress_bar']
        response = bot_texts["quest_continue"].format(progress=progress_bar, question=current_question)
    else:
        questions = load_quest_questions()
        if not questions:
            response = bot_texts["quest_empty"]
            await update.message.reply_text(response)
            log_message(update, response)
            return
        quest_data[user_id] = 0
        current_question = questions[0]['question']
        progress_bar = questions[0]['progress_bar']
        response = bot_texts["quest_start"].format(progress=progress_bar, question=current_question)

    save_active_quests(quest_data)
    await update.message.reply_text(response)
    log_message(update, response)

# Команда /request — перезапуск квеста
async def request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    questions = load_quest_questions()
    
    if not questions:
        response = bot_texts["quest_empty"]
        await update.message.reply_text(response)
        log_message(update, response)
        return

    quest_data[user_id] = 0
    first_question = questions[0]['question']
    progress_bar = questions[0]['progress_bar']
    response = bot_texts["request_restart"].format(progress=progress_bar, question=first_question)
    save_active_quests(quest_data)
    await update.message.reply_text(response)
    log_message(update, response)

# Команда /sos — подсказка
async def sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    questions = load_quest_questions()

    if not questions:
        response = bot_texts["quest_empty"]
        await update.message.reply_text(response)
        log_message(update, response)
        return

    if user_id not in quest_data:
        # Если квест не запущен, запускаем с первого вопроса
        quest_data[user_id] = 0
        question = questions[0]['question']
        progress_bar = questions[0]['progress_bar']
        hint = questions[0]['hint']
        response = bot_texts["sos_first_time"].format(progress=progress_bar, question=question, hint=hint)
    else:
        # Если квест уже запущен — просто даем подсказку
        question_index = quest_data[user_id]
        hint = questions[question_index]['hint']
        response = bot_texts["sos_hint"].format(hint=hint)

    save_active_quests(quest_data)
    await update.message.reply_text(response)
    log_message(update, response)

# Команда /map — отправка карты
async def map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    # Проверяем, завершён ли квест
    if user_id in quest_data:
        response = "Ты ещё не завершил квест, сначала его пройди!"
    else:
        # Отправляем карту только если квест пройден
        with open('bot1/images/MAP.jpg', 'rb') as map_file:
            response = "Карта готова! Держи 🤗"
            await update.message.reply_photo(photo=InputFile(map_file, 'MAP.jpg'))

    await update.message.reply_text(response)
    log_message(update, response)

# Команда /goto — пропуск нескольких вопросов и переход к конкретному
async def goto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    questions = load_quest_questions()

    if not questions:
        response = bot_texts["quest_empty"]
        await update.message.reply_text(response)
        log_message(update, response)
        return

    try:
        # Преобразуем введённый номер в целое число
        target_question = int(context.args[0]) - 1  # Математическое вычитание для правильного индекса
        if target_question < 0 or target_question >= len(questions):
            raise ValueError("Номер вопроса вне диапазона")

        quest_data[user_id] = target_question  # Обновляем состояние квеста
        current_question = questions[target_question]['question']
        progress_bar = questions[target_question]['progress_bar']
        response = bot_texts["goto_success"].format(progress=progress_bar, question=current_question)

    except (IndexError, ValueError):
        # Ошибка ввода (неверный номер вопроса)
        response = "Ошибка! Введите номер вопроса, к которому хотите перейти (например, /goto 5)."
    
    save_active_quests(quest_data)
    await update.message.reply_text(response)
    log_message(update, response)

# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id not in quest_data:
        response = bot_texts["not_started"]
        await update.message.reply_text(response)
        log_message(update, response)
        return

    user_message = update.message.text
    quest_state = quest_data[user_id]
    questions = load_quest_questions()
    correct_answers = questions[quest_state]['answer']

    if any(answer.strip().lower() == user_message.strip().lower() for answer in correct_answers):
        quest_data[user_id] += 1
        success_phrase = random.choice(bot_texts["success_phrases"])
        if quest_data[user_id] < len(questions):
            next_q = questions[quest_data[user_id]]['question']
            progress_bar = questions[quest_data[user_id]]['progress_bar']
            response = f"{success_phrase}\n\nПрогресс: {progress_bar}\n\nСледующее задание:\n{next_q}"
        else:
            response = bot_texts["quest_complete"].format(success_phrase=success_phrase)
            del quest_data[user_id]
    else:
        response = bot_texts["wrong_answer"]

    save_active_quests(quest_data)
    await update.message.reply_text(response)
    log_message(update, response)

# Обработка остальных сообщений
async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = bot_texts["send_text_prompt"]
    await update.message.reply_text(response)
    log_message(update, response)

# Запуск бота
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('quest', quest))
    app.add_handler(CommandHandler('request', request))
    app.add_handler(CommandHandler('sos', sos))
    app.add_handler(CommandHandler('map', map))
    app.add_handler(CommandHandler('goto', goto))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_other))

    print("Бот запущен...")
    app.run_polling()