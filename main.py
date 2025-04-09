import telebot
from flask import Flask, request
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)
user_sessions = {}

def create_new_thread(user_id):
    thread = client.beta.threads.create()
    user_sessions[user_id] = thread.id
    return thread.id

def send_to_assistant(user_id, message):
    thread_id = user_sessions.get(user_id) or create_new_thread(user_id)

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run.status == "completed":
            break

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            return msg.content[0].text.value

    return "Что-то пошло не так..."

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.chat.id)
    create_new_thread(user_id)
    bot.send_message(message.chat.id,
                     "Привет! Я бот, который поможет заполнить бриф. Напиши что-нибудь или просто «не знаю» — я подскажу 🙂")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.chat.id)
    if user_id not in user_sessions:
        create_new_thread(user_id)

    response = send_to_assistant(user_id, message.text)
    bot.send_message(message.chat.id, response)

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

if __name__ == '__main__':
    app.run(debug=True)
