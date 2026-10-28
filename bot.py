import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# 1. Твій токен від BotFather
TOKEN = "9014457960:AAF8U-6Fw9u-MPHbKS6vK1LTx79AA3HruFE"

# 2. Твій реальний Telegram ID для отримання звернень
ADMIN_CHAT_ID = 8589473317

bot = telebot.TeleBot(TOKEN)
user_data = {}

# --- Клавіатури ---
def get_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_appeal = types.InlineKeyboardButton("📝 Подати звернення / Запитання", callback_data="btn_appeal")
    btn_scholarship = types.InlineKeyboardButton("🎓 Стипендії", callback_data="btn_scholarship")
    btn_leocard = types.InlineKeyboardButton("💳 Питання щодо ЛеоКарт", callback_data="btn_leocard")
    btn_complaint = types.InlineKeyboardButton("⚠️ Скарга на викладача", callback_data="btn_teacher_complaint")
    markup.add(btn_appeal, btn_scholarship, btn_leocard, btn_complaint)
    return markup

def get_back_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Головне меню", callback_data="back_to_menu"))
    return markup

# --- Обробники ---
@bot.message_handler(commands=['start'])
def start_command(message):
    text = (
        f"Привіт, {message.from_user.first_name}! 👋\n\n"
        "Це офіційний бот факультету. Тут ти можеш дізнатися корисну інформацію, "
        "поставити запитання або подати звернення до студентського самоврядування.\n\n"
        "Обери потрібний розділ нижче:"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id

    if call.data == "back_to_menu":
        bot.edit_message_text(
            "Головне меню. Обери потрібний розділ:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=get_main_keyboard()
        )
    elif call.data == "btn_scholarship":
        text = (
            "🎓 **Інформація про стипендії**\n\n"
            "• Академічна стипендія призначається на основі рейтингового балу за результатами сесії.\n"
            "• Соціальна стипендія оформлюється через деканат/профком для студентів пільгових категорій.\n\n"
            "Якщо є конкретне питання щодо нарахувань — тисни «Подати звернення»."
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    elif call.data == "btn_leocard":
        text = (
            "💳 **ЛеоКарт для студентів**\n\n"
            "Персоналізована студентська ЛеоКарт (синього кольору) дає право на пільговий проїзд у міському транспорті Львова.\n\n"
            "Якщо виникають проблеми з виготовленням чи блокуванням — надішли звернення через форму."
        )
        bot.edit_message_text(text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    elif call.data in ["btn_appeal", "btn_teacher_complaint"]:
        ticket_type = "Звернення / Запитання" if call.data == "btn_appeal" else "Скарга на викладача"
        user_data[chat_id] = {'ticket_type': ticket_type}
        msg = bot.send_message(chat_id, f"📝 Ви обрали: **{ticket_type}**.\n\nВведи своє **ПІБ** (Прізвище, Ім'я, По батькові):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text
    msg = bot.send_message(chat_id, "Введи свій **курс та групу** (наприклад: ГЛІ-11):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_group_step)

def process_group_step(message):
    chat_id = message.chat.id
    user_data[chat_id]['group'] = message.text
    msg = bot.send_message(chat_id, "Опиши детально суть свого запитання або проблеми:")
    bot.register_next_step_handler(msg, process_text_step)

def process_text_step(message):
    chat_id = message.chat.id
    user_info = user_data.get(chat_id, {})
    ticket_type = user_info.get('ticket_type', 'Звернення')
    user_name = user_info.get('name', 'Не вказано')
    user_group = user_info.get('group', 'Не вказано')
    issue_text = message.text
    username_str = f"@{message.from_user.username}" if message.from_user.username else "немає юзернейму"

    report_text = (
        f"🚨 **НОВЕ ЗВЕРНЕННЯ З БОТА**\n\n"
        f"📌 **Категорія:** {ticket_type}\n"
        f"👤 **ПІБ:** {user_name}\n"
        f"📚 **Група:** {user_group}\n"
        f"🔗 **Контакт:** {username_str} (ID: `{message.from_user.id}`)\n\n"
        f"💬 **Текст звернення:**\n{issue_text}"
    )

    try:
        bot.send_message(ADMIN_CHAT_ID, report_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Помилка відправки адміну: {e}")

    bot.send_message(chat_id, "✅ Дякуємо! Твоє звернення успішно передано. Очікуй на відповідь!", reply_markup=get_main_keyboard())
    if chat_id in user_data:
        del user_data[chat_id]

# --- Миттєвий вебсервер для Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return # вимикаємо зайвий спам у логах

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    # Запускаємо вебсервер у фоновому потоці одразу
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    
    print("Вебсервер піднято, запускаємо Telegram бота...")
    bot.infinity_polling()
