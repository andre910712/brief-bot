import telebot
import openai
import os
import time
import csv
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

user_states = {}
user_answers = {}
user_resume = {}

csv_path = "brief_data.csv" 

questions = [
    ["1.1", "Чем вы занимаетесь?"],
    ["1.2", "Как называется ваша компания?"],
    ["1.3", "С какого года вы на рынке?"],
    ["1.4", "В каком регионе вы работаете сейчас?"],
    ["1.5", "Планируете ли продвигаться в другие регионы?"],
    ["2.1", "Какая цель создания сайта?"],
    ["2.2", "Что должен сделать клиент на сайте?"],
    ["3.1", "Какие товары / услуги вы продаёте?"],
    ["3.2", "В чём ваше УТП / суперпреимущество?"],
    ["3.4", "Укажите ссылку на конкурентов:"],
    ["3.5", "Что вам нравится в конкурентах?"],
    ["3.6", "Ссылка на торговлю (если есть):"],
    ["3.7", "Есть ли отзывы / кейсы / сертификаты?"],
    ["3.8", "Что нужно для сайта?"],
    ["3.9", "Стили (минимализм, глянец и т.д.)."],
    ["3.10", "Есть ли примеры сайтов, которые вам нравятся?"],
    ["3.11", "Нужен ли логотип? Заголовок и вопросы."],
    ["3.12", "Ваша идея."],
    ["4.1", "Когда хотите запустить сайт?"],
    ["9.1", "Что клиент должен унести после посещения сайта?"],
    ["10.0", "Ваши контактные данные (телефон, почта или ник в Telegram)?"]
]

def save_to_csv(user_id, question, answer):
    with open(csv_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%d.%m.%Y %H:%M"), user_id, question, answer])

def gpt_help(text, current_question):
    try:
        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Помоги заполнить бриф: {current_question}\nПользователь написал: {text}"
        )
        run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[0].content[0].text.value
    except Exception as e:
        return f"GPT недоступен: {e}"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id in user_states and user_states[user_id] is not None:
        bot.send_message(user_id, "Вы уже начали заполнение. Напишите /resume чтобы продолжить.")
        return
    user_states[user_id] = 0
    user_answers[user_id] = []
    user_resume[user_id] = 0
    bot.send_message(user_id, "👋 Привет! Я умный бот со встроенным ChatGPT. Просто отвечай на вопросы. Если нужно — напиши 'не знаю', 'помощь' или 'не понимаю'.")
    bot.send_message(user_id, questions[0][1])

@bot.message_handler(commands=['resume'])
def resume(message):
    user_id = message.chat.id
    if user_id in user_resume:
        user_states[user_id] = user_resume[user_id]
        bot.send_message(user_id, f"Продолжаем с вопроса: {questions[user_states[user_id]][1]}")
    else:
        bot.send_message(user_id, "Нет данных для восстановления. Напиши /start чтобы начать заново.")

@bot.message_handler(func=lambda m: True)
def handle_answer(message):
    user_id = message.chat.id
    step = user_states.get(user_id)

    if step is None or step >= len(questions):
        bot.send_message(user_id, "Напиши /start чтобы начать заново.")
        return

    text = message.text.strip().lower()
    current_question = questions[step][1]

    if "помощь" in text or "не знаю" in text or "не понимаю" in text or "?" in text:
        hint = gpt_help(message.text, current_question)
        bot.send_message(user_id, f"🤖 Подсказка: {hint}")
        return

    user_answers.setdefault(user_id, []).append(message.text)
    user_resume[user_id] = step + 1
    save_to_csv(user_id, current_question, message.text)

    if step + 1 < len(questions):
        user_states[user_id] += 1
        bot.send_message(user_id, questions[step + 1][1])
    else:
        bot.send_message(user_id, "✅ Бриф завершён! Спасибо 🙌")
        user_states[user_id] = None
        summary = "\n".join(f"{questions[i][1]}\nОтвет: {user_answers[user_id][i]}" for i in range(len(questions)))
        bot.send_message(user_id, f"Ваши ответы:\n\n{summary}")
        del user_answers[user_id]

# Flask webhook
@app.route('/', methods=['GET'])
def index():
    return 'Бот работает'

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# Установка webhook при запуске
if __name__ == '__main__':
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # пример: https://brief-bot.onrender.com/ВАШ_ТОКЕН
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))