import telebot
import openai
import os
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
bot = telebot.TeleBot(TOKEN)
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Hello from bot!', 200

@bot.message_handler(commands=['start'])
def handle_start(message):
    print("Получена команда /start")  # Для Render
    bot.send_message(message.chat.id, "Привет! Я бот, который поможет заполнить бриф по созданию сайта.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    print(f"Новое сообщение: {message.text}")  # Для Render
    bot.send_message(message.chat.id, "Сообщение получено! Скоро я научусь отвечать умнее 🙂")

if __name__ == "__main__":
    print("Запущен main.py")  # Для Render
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
