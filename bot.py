import logging
import os
from mistralai import Mistral
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Инициализация Mistral AI с явным указанием API ключа
api_key = os.getenv("MISTRAL_API_KEY")  # Замените на ваш реальный API ключ
model = "mistral-large-latest"
client = Mistral(api_key=api_key)

# Токен для работы с Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Замените на токен вашего Telegram-бота

# Хранилище для диалогов и сообщений
dialogs = {}
message_ids = {}

# Функция для запроса к Mistral AI
def query_mistral_api(user_id, message):
    messages = [{"role": "user", "content": message}]
    
    try:
        response = client.chat.complete(model=model, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка при запросе к Mistral API: {str(e)}"

# Функция для удаления сообщений и очистки диалога
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id

    # Удаляем все сообщения
    if user_id in message_ids:
        for msg_id in message_ids[user_id]:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                logging.warning(f"Не удалось удалить сообщение {msg_id}: {e}")

    dialogs[user_id] = []
    message_ids[user_id] = []

    await update.message.reply_text("Диалог очищен.")

# Функция для отображения клавиатуры с кнопкой
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаем кнопку "Очистить диалог" на клавиатуре
    keyboard = [
        ["Очистить диалог"]  # Кнопка очистки диалога
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

# Основная функция для обработки сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    message = update.message.text

    if message == "Очистить диалог":
        await clear(update, context)
        return

    if user_id not in dialogs:
        dialogs[user_id] = []
    if user_id not in message_ids:
        message_ids[user_id] = []

    # Сохраняем ID сообщения пользователя
    message_ids[user_id].append(update.message.message_id)

    dialogs[user_id].append({"role": "user", "content": message})

    await context.bot.send_chat_action(chat_id=user_id, action=ChatAction.TYPING)

    response = query_mistral_api(user_id, message)

    dialogs[user_id].append({"role": "assistant", "content": response})

    msg = await update.message.reply_text(response)
    message_ids[user_id].append(msg.message_id)

# Команда для запуска бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    msg = await update.message.reply_text("Привет! Я бот, задавай вопросы. Чтобы очистить диалог, используй кнопку.")
    if user_id not in message_ids:
        message_ids[user_id] = []
    message_ids[user_id].append(msg.message_id)
    
    await show_menu(update, context)  # Показываем меню с кнопкой

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Команда /start
    app.add_handler(CommandHandler("start", start))

    # Обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Стартуем бота
    app.run_polling()
