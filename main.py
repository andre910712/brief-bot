import telebot
import os
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

user_sessions = {}

# Создаём новую ветку в GPT-ассистенте
def create_new_thread(user_id):
    thread = client.beta.threads.create()
    user_sessions[user_id] = thread.id
    return thread.id

# Отправляем сообщение ассистенту
def send_to_assistant(user_id, message_text):
    thread_id = user_sessions[user_id]
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status == 'completed':
            break

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "Что-то пошло не так..."

# Обработка команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.chat.id)
    create_new_thread(user_id)
    bot.send_message(message.chat.id, "Привет! Я помогу тебе заполнить бриф. Просто пиши ответы на вопросы. Если не знаешь — напиши 'не знаю' — я подскажу 🤖")

# Обработка всех остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.chat.id)
    if user_id not in user_sessions:
        create_new_thread(user_id)

    response = send_to_assistant(user_id, message.text)
    bot.send_message(message.chat.id, response)

# Обработка входящих запросов от Telegram
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

if __name__ == '__main__':
    app.run(debug=True)
